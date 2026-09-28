"""
Discuter avec l'IA d'un projet déjà en cours pour trouver les tâches qui manquent.

Avant le 28/09/2026, l'idéation n'était possible qu'à la création d'un projet
(statut IDEATION) ; les projets venus des fiches .md, souvent sans tâches, n'y
avaient pas accès. Et les tâches issues de l'analyse partaient en READY : le
planificateur lançait aussitôt veilles et recherches.
"""

import pytest
from sqlalchemy import select

from app.models.ideation_message import IdeationMessage
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus, TaskType
from app.services.ideation_service import IdeationService
from app.services.project_analyzer import ProjectAnalyzer


async def _projet_actif(client, auth_headers, db, taches=()):
    pid = (await client.post("/api/v1/projects/", json={
        "name": "Data-compost", "type": "personal", "features": {"code_gen": True},
        "description": "Installation de compostage numérique.",
    }, headers=auth_headers)).json()["id"]
    projet = (await db.execute(select(Project).where(Project.id == pid))).scalar_one()
    projet.status = ProjectStatus.ACTIVE
    for titre, statut in taches:
        db.add(Task(project_id=pid, title=titre, task_type=TaskType.RESEARCH, status=statut))
    await db.commit()
    return pid


@pytest.mark.asyncio
async def test_discussion_possible_sur_un_projet_en_cours(client, auth_headers, db_session, monkeypatch):
    async def reponse_sans_modele(self, project_id):
        message = IdeationMessage(project_id=project_id, role="ASSISTANT", content="Qu'est-ce qui bloque ?")
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message
    monkeypatch.setattr(IdeationService, "generate_assistant_response", reponse_sans_modele)

    pid = await _projet_actif(client, auth_headers, db_session,
                              [("Diagnostic", TaskStatus.COMPLETED), ("Note d'intention", TaskStatus.CREATED)])
    r = await client.post("/api/v1/ideation/start", json={"project_id": pid}, headers=auth_headers)
    assert r.status_code == 201, r.text

    contexte = (await db_session.execute(select(IdeationMessage).where(
        IdeationMessage.project_id == pid, IdeationMessage.role == "USER"))).scalars().first()
    assert "est en cours" in contexte.content
    assert "- [fait] Diagnostic" in contexte.content and "- Note d'intention" in contexte.content
    # Le projet reste actif : discuter ne le renvoie pas en idéation
    projet = (await db_session.execute(select(Project).where(Project.id == pid))).scalar_one()
    assert projet.status == ProjectStatus.ACTIVE


@pytest.mark.asyncio
async def test_projet_archive_refuse(client, auth_headers, db_session):
    pid = await _projet_actif(client, auth_headers, db_session)
    projet = (await db_session.execute(select(Project).where(Project.id == pid))).scalar_one()
    projet.status = ProjectStatus.ARCHIVED
    await db_session.commit()
    r = await client.post("/api/v1/ideation/start", json={"project_id": pid}, headers=auth_headers)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_proposer_des_taches_garde_la_discussion_sans_changer_le_statut(client, auth_headers, db_session):
    pid = await _projet_actif(client, auth_headers, db_session)
    db_session.add_all([
        IdeationMessage(project_id=pid, role="USER", content="Il faut d'abord réparer l'écran e-paper."),
        IdeationMessage(project_id=pid, role="ASSISTANT", content="Alors une tâche de diagnostic matériel."),
    ])
    await db_session.commit()

    r = await client.post(f"/api/v1/ideation/transcript/{pid}", headers=auth_headers)
    assert r.status_code == 200 and r.json()["messages"] == 2
    db_session.expire_all()
    projet = (await db_session.execute(select(Project).where(Project.id == pid))).scalar_one()
    assert projet.status == ProjectStatus.ACTIVE
    assert "e-paper" in projet.ideation_transcript[0]["content"]


def test_resume_garde_la_fin_de_la_discussion_sans_l_introduction():
    transcript = [{"role": "USER", "content": "Description très longue " * 50,
                   "meta": {"auto_generated": True}}]
    transcript += [{"role": "USER" if i % 2 else "ASSISTANT", "content": f"message {i} " + "x" * 700}
                   for i in range(20)]
    transcript.append({"role": "USER", "content": "Conclusion : commencer par le diagnostic."})
    resume = ProjectAnalyzer.__new__(ProjectAnalyzer)._summarize_ideation_transcript(transcript)
    assert "Conclusion : commencer par le diagnostic." in resume     # la fin est gardée
    assert "Description très longue" not in resume                   # l'introduction auto écartée
    assert "début de la conversation omis" in resume
    assert len(resume) < 7000


def test_taches_creees_depuis_l_analyse_restent_en_attente():
    import inspect
    from app.services import project_analyzer
    source = inspect.getsource(project_analyzer)
    assert "status=TaskStatus.READY" not in source


@pytest.mark.asyncio
async def test_veilles_suggerees_en_attente_sans_passage_programme(client, auth_headers, db_session):
    from app.models.veille_topic import VeilleTopic

    pid = await _projet_actif(client, auth_headers, db_session)
    r = await client.post(f"/api/v1/projects/{pid}/create-suggested-tasks", json={
        "tasks": [{"title": "Note d'intention", "description": "Rédiger la note", "task_type": "document_writing",
                   "priority": "P1", "estimated_duration": 3600, "subtasks": [], "dependencies": [],
                   "rationale": "", "llm_prompt": None}],
        "veille": [{"scope": "cultural", "keywords": ["festival", "art numérique"],
                    "reason": "Trouver des lieux", "scan_frequency": "weekly"}],
    }, headers=auth_headers)
    assert r.status_code in (200, 201), r.text

    db_session.expire_all()
    taches = (await db_session.execute(select(Task).where(Task.project_id == pid))).unique().scalars().all()
    assert {t.status for t in taches} == {TaskStatus.CREATED}      # rien ne part tout seul
    assert any(t.task_type == TaskType.VEILLE for t in taches)
    topic = (await db_session.execute(select(VeilleTopic).where(VeilleTopic.project_id == pid))).scalars().one()
    assert topic.next_scan is None


@pytest.mark.asyncio
async def test_recurrence_demarre_apres_la_premiere_veille(client, auth_headers, db_session):
    from app.models.veille_topic import VeilleScope, VeilleTopic
    from app.services.unified_orchestrator import UnifiedOrchestrator

    pid = await _projet_actif(client, auth_headers, db_session)
    topic = VeilleTopic(project_id=pid, name="V", scope=VeilleScope.NEWS, keywords=[], scan_frequency="weekly")
    db_session.add(topic)
    await db_session.flush()
    tache = Task(project_id=pid, title="Veille", task_type=TaskType.VEILLE,
                 status=TaskStatus.GENERATING, veille_topic_id=topic.id)
    db_session.add(tache)
    await db_session.commit()

    await UnifiedOrchestrator(db_session)._start_veille_recurrence(tache)
    assert topic.last_scan is not None and topic.next_scan is not None
