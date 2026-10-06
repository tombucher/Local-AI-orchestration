"""
Priorité des projets, pause et sommeil.

Avec une vingtaine de projets au même niveau, le briefing parlait autant d'un
projet à dix-huit mois que d'un rendu dans quinze jours.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus, TaskType
from app.services import briefing
from app.services.project_state import resume_due_projects


async def _projets(client, auth_headers, *noms):
    ids = []
    for nom in noms:
        r = await client.post("/api/v1/projects/", json={
            "name": nom, "type": "personal", "features": {"code_gen": True}}, headers=auth_headers)
        ids.append(r.json()["id"])
    return ids


async def _activer(db, ids):
    for p in (await db.execute(select(Project).where(Project.id.in_(ids)))).scalars():
        p.status = ProjectStatus.ACTIVE
    await db.commit()


@pytest.mark.asyncio
async def test_ordre_de_priorite(client, auth_headers, db_session):
    a, b, c = await _projets(client, auth_headers, "Alpha", "Bravo", "Charlie")
    r = await client.post("/api/v1/projects/reorder", json={"project_ids": [c, a, b, 999999]},
                          headers=auth_headers)
    assert r.status_code == 200 and r.json()["ranked"] == 3      # l'id étranger est ignoré

    items = (await client.get("/api/v1/projects/", headers=auth_headers)).json()["items"]
    assert [p["name"] for p in items] == ["Charlie", "Alpha", "Bravo"]
    assert [p["priority_rank"] for p in items] == [1, 2, 3]


@pytest.mark.asyncio
async def test_pause_avec_reprise_puis_sommeil(client, auth_headers, db_session):
    (pid,) = await _projets(client, auth_headers, "Data-compost")
    reprise = (date.today() + timedelta(days=30)).isoformat()
    r = await client.put(f"/api/v1/projects/{pid}", json={"status": "PAUSED", "resume_on": reprise},
                         headers=auth_headers)
    assert r.status_code == 200 and r.json()["resume_on"] == reprise

    # En sommeil : la date de reprise n'a plus de sens
    r = await client.put(f"/api/v1/projects/{pid}", json={"status": "DORMANT"}, headers=auth_headers)
    assert r.json()["status"] == "DORMANT" and r.json()["resume_on"] is None


@pytest.mark.asyncio
async def test_pause_n_annule_rien(client, auth_headers, db_session):
    (pid,) = await _projets(client, auth_headers, "Projet")
    db_session.add(Task(project_id=pid, title="À faire", task_type=TaskType.RESEARCH, status=TaskStatus.CREATED))
    await db_session.commit()
    await client.put(f"/api/v1/projects/{pid}", json={"status": "PAUSED"}, headers=auth_headers)
    db_session.expire_all()
    tache = (await db_session.execute(select(Task).where(Task.project_id == pid))).unique().scalar_one()
    assert tache.status == TaskStatus.CREATED


@pytest.mark.asyncio
async def test_reprise_automatique_a_la_date(client, auth_headers, db_session):
    a, b = await _projets(client, auth_headers, "Échu", "Plus tard")
    projets = {p.id: p for p in (await db_session.execute(select(Project).where(Project.id.in_([a, b])))).scalars()}
    projets[a].status, projets[a].resume_on = ProjectStatus.PAUSED, briefing.today_local()
    projets[b].status, projets[b].resume_on = ProjectStatus.PAUSED, briefing.today_local() + timedelta(days=3)
    await db_session.commit()

    # Ouvrir la liste suffit : le projet échu revient dans les actifs
    items = {p["name"]: p for p in (await client.get("/api/v1/projects/", headers=auth_headers)).json()["items"]}
    assert items["Échu"]["status"] == "ACTIVE" and items["Échu"]["resume_on"] is None
    assert items["Plus tard"]["status"] == "PAUSED"
    assert await resume_due_projects(db_session) == []           # rien de plus à reprendre


@pytest.mark.asyncio
async def test_briefing_ignore_pause_et_sommeil_et_suit_l_ordre(client, auth_headers, db_session):
    from app.services.daily_review_service import DailyReviewService

    a, b, c, d = await _projets(client, auth_headers, "Deuxième", "En pause", "En sommeil", "Premier")
    await _activer(db_session, [a, d])
    projets = {p.id: p for p in (await db_session.execute(select(Project).where(Project.id.in_([a, b, c, d])))).scalars()}
    projets[b].status, projets[c].status = ProjectStatus.PAUSED, ProjectStatus.DORMANT
    projets[d].priority_rank, projets[a].priority_rank = 1, 2
    await db_session.commit()

    moi = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"]
    service = DailyReviewService(db_session)
    vus = []

    async def capture(project, *args, **kwargs):
        vus.append(project.name)
        raise RuntimeError("arrêt du test : seule la sélection des projets compte")

    service._analyze_project_status = capture
    try:
        await service.generate_daily_report(moi)
    except RuntimeError:
        pass
    assert vus[:1] == ["Premier"] and "En pause" not in vus and "En sommeil" not in vus


@pytest.mark.asyncio
async def test_automatismes_arretes_pour_un_projet_en_pause(client, auth_headers, db_session):
    from app.services.unified_orchestrator import UnifiedOrchestrator

    (pid,) = await _projets(client, auth_headers, "En pause")
    projet = (await db_session.execute(select(Project).where(Project.id == pid))).scalar_one()
    projet.status = ProjectStatus.PAUSED
    db_session.add(Task(project_id=pid, title="Veille", task_type=TaskType.VEILLE, status=TaskStatus.READY))
    await db_session.commit()

    traitees = []
    orchestrateur = UnifiedOrchestrator(db_session)

    async def ne_pas_lancer(task):
        traitees.append(task.id)
    orchestrateur.handle_task = ne_pas_lancer
    assert await orchestrateur._process_auto_tasks(batch_size=5) == 0
    assert traitees == []


@pytest.mark.asyncio
async def test_liste_resume_chaque_projet_en_une_requete(client, auth_headers, db_session):
    from datetime import datetime, timezone

    (pid,) = await _projets(client, auth_headers, "Résumé")
    proche = datetime(2026, 11, 2, 18, tzinfo=timezone.utc)
    db_session.add_all([
        Task(project_id=pid, title="A", task_type=TaskType.RESEARCH, status=TaskStatus.CREATED, due_date=proche),
        Task(project_id=pid, title="B", task_type=TaskType.RESEARCH, status=TaskStatus.CREATED,
             due_date=datetime(2026, 12, 1, tzinfo=timezone.utc)),
        Task(project_id=pid, title="C", task_type=TaskType.RESEARCH, status=TaskStatus.MANUAL_REVIEW),
        Task(project_id=pid, title="D", task_type=TaskType.RESEARCH, status=TaskStatus.COMPLETED,
             due_date=datetime(2026, 1, 1, tzinfo=timezone.utc)),   # terminée : pas une échéance
        Task(project_id=pid, title="E", task_type=TaskType.RESEARCH, status=TaskStatus.CANCELLED),
    ])
    await db_session.commit()

    p = (await client.get("/api/v1/projects/", headers=auth_headers)).json()["items"][0]
    assert (p["tasks_total"], p["tasks_completed"], p["tasks_to_activate"], p["tasks_to_review"]) == (4, 1, 2, 1)
    assert p["next_due_date"].startswith("2026-11-02")
