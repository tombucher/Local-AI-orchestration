"""
Tests du chien de garde des tâches GENERATING.

Constat du 26/09/2026 : il plantait à chaque passage (dates avec et sans
fuseau), si bien qu'une tâche tuée par un redémarrage restait « en cours »
indéfiniment. Et son seuil fixe de 15 min aurait tué des veilles bien vivantes.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.task import Task, TaskStatus, TaskType
from app.services import scheduler as sched
from app.services import task_progress


@pytest.fixture
def session_de_test(db_session, monkeypatch):
    """Le job ouvre sa propre session : on lui donne celle du test."""
    class Fabrique:
        def __call__(self):
            return self

        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(sched, "AsyncSessionLocal", Fabrique())
    return db_session


async def _tache(client, auth_headers, db, minutes: int) -> int:
    projet = (await client.post("/api/v1/projects/", json={
        "name": "Garde", "type": "personal", "features": {"code_gen": True},
    }, headers=auth_headers)).json()["id"]
    tache = Task(project_id=projet, title="Veille", task_type=TaskType.VEILLE,
                 status=TaskStatus.GENERATING,
                 started_at=datetime.now(timezone.utc) - timedelta(minutes=minutes))
    db.add(tache)
    await db.commit()
    return tache.id


async def _statut(db, task_id):
    db.expire_all()
    return (await db.execute(select(Task.status).where(Task.id == task_id))).scalar_one()


@pytest.mark.asyncio
async def test_tache_morte_apres_redemarrage_debloquee(client, auth_headers, session_de_test):
    tid = await _tache(client, auth_headers, session_de_test, minutes=5)
    task_progress.task_finished(tid)  # absente du processus
    await sched.watchdog_generating_tasks_job()
    assert await _statut(session_de_test, tid) == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_veille_longue_mais_vivante_laissee_tranquille(client, auth_headers, session_de_test):
    tid = await _tache(client, auth_headers, session_de_test, minutes=25)
    task_progress.task_started(tid)
    try:
        await sched.watchdog_generating_tasks_job()
        assert await _statut(session_de_test, tid) == TaskStatus.GENERATING
    finally:
        task_progress.task_finished(tid)


@pytest.mark.asyncio
async def test_tache_qui_demarre_a_peine_epargnee(client, auth_headers, session_de_test):
    tid = await _tache(client, auth_headers, session_de_test, minutes=0)
    await sched.watchdog_generating_tasks_job()
    assert await _statut(session_de_test, tid) == TaskStatus.GENERATING


@pytest.mark.asyncio
async def test_tache_vivante_mais_interminable_arretee(client, auth_headers, session_de_test):
    tid = await _tache(client, auth_headers, session_de_test, minutes=3 * 60)
    task_progress.task_started(tid)
    try:
        await sched.watchdog_generating_tasks_job()
        assert await _statut(session_de_test, tid) == TaskStatus.FAILED
    finally:
        task_progress.task_finished(tid)


@pytest.mark.asyncio
async def test_relance_des_taches_en_echec_ne_plante_plus(client, auth_headers, db_session):
    """La base renvoie des dates avec fuseau : la comparaison avec utcnow()
    faisait échouer tout le cycle de la file (constaté le 26/09/2026)."""
    from app.services.unified_orchestrator import UnifiedOrchestrator

    projet = (await client.post("/api/v1/projects/", json={
        "name": "Relance", "type": "personal", "features": {"code_gen": True},
    }, headers=auth_headers)).json()["id"]
    ancienne = Task(project_id=projet, title="Ancienne", task_type=TaskType.VEILLE,
                    status=TaskStatus.FAILED, retry_count=1,
                    last_failed_at=datetime.now(timezone.utc) - timedelta(hours=3))
    recente = Task(project_id=projet, title="Récente", task_type=TaskType.VEILLE,
                   status=TaskStatus.FAILED, retry_count=1,
                   last_failed_at=datetime.now(timezone.utc))
    db_session.add_all([ancienne, recente])
    await db_session.commit()
    ids = (ancienne.id, recente.id)

    assert await UnifiedOrchestrator(db_session)._retry_failed_tasks() == 1
    await db_session.commit()
    assert await _statut(db_session, ids[0]) == TaskStatus.READY
    assert await _statut(db_session, ids[1]) == TaskStatus.FAILED  # cooldown en cours
