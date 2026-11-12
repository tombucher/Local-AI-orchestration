"""
Répondre à une tâche : la réponse voyage vers les tâches suivantes, le carnet
du projet, et peut faire évoluer la veille.

Cas du 12/11/2026 : « Préciser le périmètre de la veille » posait des questions
(zone, prestations, seuils). L'utilisateur avait les réponses et nulle part où
les écrire ; la veille hebdomadaire continuait avec ses mots-clés d'origine.
"""

import pytest
from sqlalchemy import select

from app.models.project import Project
from app.models.task import Task, TaskStatus, TaskType, task_dependencies
from app.models.veille_topic import VeilleTopic, VeilleScope
from app.services import veille_update
from app.services.project_memory import build_project_memory
from app.services.task_chain import build_upstream_context


async def _projet(client, auth_headers):
    r = await client.post("/api/v1/projects/", json={
        "name": "Veille des appels d'offres", "type": "professional",
        "description": "Repérer les consultations graphisme des collectivités.",
        "features": {"veille": True}}, headers=auth_headers)
    return r.json()["id"]


@pytest.mark.asyncio
async def test_la_reponse_se_sauvegarde_et_suit_la_tache_en_aval(client, auth_headers, db_session):
    pid = await _projet(client, auth_headers)
    amont = Task(project_id=pid, title="Préciser le périmètre", task_type=TaskType.ADMINISTRATIVE,
                 status=TaskStatus.COMPLETED, generated_code="Quelle zone ? Quels montants ?")
    aval = Task(project_id=pid, title="Dossier de références", task_type=TaskType.DOCUMENT_WRITING,
                status=TaskStatus.CREATED)
    db_session.add_all([amont, aval])
    await db_session.flush()
    await db_session.execute(task_dependencies.insert().values(task_id=aval.id, depends_on_id=amont.id))
    await db_session.commit()

    r = await client.put(f"/api/v1/tasks/{amont.id}", json={
        "user_notes": "Zone : Auvergne-Rhône-Alpes et Bourgogne. Montants : 3 000 à 40 000 € HT."},
        headers=auth_headers)
    assert r.status_code == 200 and "Bourgogne" in r.json()["user_notes"]
    assert "Bourgogne" in (await client.get(f"/api/v1/tasks/{amont.id}", headers=auth_headers)).json()["user_notes"]

    aval_id = aval.id
    db_session.expire_all()
    aval = (await db_session.execute(select(Task).where(Task.id == aval_id))).unique().scalar_one()
    contexte = await build_upstream_context(db_session, aval)
    assert "Quelle zone" in contexte
    assert "font autorité" in contexte and "Bourgogne" in contexte

    projet = (await db_session.execute(select(Project).where(Project.id == pid))).scalar_one()
    memoire = await build_project_memory(db_session, projet)
    assert "Précisions de l'utilisateur (Préciser le périmètre)" in memoire.brief
    assert "bourgogne" in memoire.vocabulary


@pytest.mark.asyncio
async def test_la_reponse_fait_evoluer_la_veille(client, auth_headers, db_session, monkeypatch):
    pid = await _projet(client, auth_headers)
    topic = VeilleTopic(project_id=pid, name="Consultations", scope=VeilleScope.NEWS,
                        keywords=["marché public communication", "identité visuelle"],
                        excluded_keywords=[], scan_frequency="weekly")
    tache = Task(project_id=pid, title="Préciser le périmètre", task_type=TaskType.ADMINISTRATIVE,
                 status=TaskStatus.COMPLETED, generated_code="Quelle zone ?")
    db_session.add_all([topic, tache])
    await db_session.commit()

    # Sans réponse écrite : refus explicite
    r = await client.post(f"/api/v1/tasks/{tache.id}/notes-to-veille", headers=auth_headers)
    assert r.status_code == 400

    async def proposition_simulee(topic, notes, resultat):
        assert "Bourgogne" in notes and "Quelle zone" in resultat
        return {"add_keywords": ["marché public graphisme Bourgogne"],
                "remove_keywords": ["identité visuelle"], "add_excluded": ["signalétique routière"]}
    monkeypatch.setattr(veille_update, "proposer_evolution", proposition_simulee)

    await client.put(f"/api/v1/tasks/{tache.id}", json={"user_notes": "Zone : Bourgogne. Pas de signalétique routière."},
                     headers=auth_headers)
    r = await client.post(f"/api/v1/tasks/{tache.id}/notes-to-veille", headers=auth_headers)
    assert r.status_code == 200
    [sujet] = r.json()["topics"]
    assert sujet["keywords"] == ["marché public communication", "marché public graphisme Bourgogne"]
    assert sujet["excluded_keywords"] == ["signalétique routière"]
    assert sujet["removed"] == ["identité visuelle"]

    topic_id, tache_id = topic.id, tache.id
    db_session.expire_all()
    topic = (await db_session.execute(select(VeilleTopic).where(VeilleTopic.id == topic_id))).scalar_one()
    assert topic.refinement_history[-1]["user_notes"].startswith("Zone : Bourgogne")
    assert topic.refinement_history[-1]["source_task_id"] == tache_id
    assert topic.next_scan is not None  # prochaine occurrence avancée à tout de suite


def test_sans_modele_la_note_entre_quand_meme_dans_l_historique():
    topic = VeilleTopic(name="V", scope=VeilleScope.NEWS, keywords=["a", "b"], excluded_keywords=[])
    resultat = veille_update.appliquer(topic, {}, "ma réponse", source_task_id=1)
    assert resultat["keywords"] == ["a", "b"] and resultat["added"] == []
    assert topic.refinement_history[-1]["user_notes"] == "ma réponse"


def test_pas_plus_de_huit_mots_cles():
    topic = VeilleTopic(name="V", scope=VeilleScope.NEWS, keywords=[f"k{i}" for i in range(7)], excluded_keywords=[])
    resultat = veille_update.appliquer(topic, {"add_keywords": ["n1", "n2", "n3"]}, "r", source_task_id=1)
    assert len(resultat["keywords"]) == 8 and resultat["added"] == ["n1"]
