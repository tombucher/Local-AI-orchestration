"""
Tests du briefing du jour.

Constat du 27/09/2026 : aucun briefing les 25 et 26 — le Mac dormait à 8 h et
le planificateur ne tolérait qu'une seconde de retard. Et « 8 h » était 8 h UTC.
"""

from datetime import datetime

import pytest

from app.models.daily_report import DailyReport as DailyReportModel
from app.services import briefing


def test_aujourd_hui_dans_le_fuseau_de_l_utilisateur(monkeypatch):
    monkeypatch.setattr(briefing.settings, "TIMEZONE", "Pacific/Kiritimati")  # UTC+14
    assert briefing.today_local() == datetime.now(briefing.local_tz()).date()


@pytest.mark.asyncio
async def test_briefing_rattrape_au_reveil_et_a_l_heure_locale():
    from app.services import scheduler as sched

    sched.start_scheduler()
    try:
        job = sched.scheduler.get_job("daily_reports")
        assert job.misfire_grace_time >= 6 * 3600
        assert job.coalesce
        assert str(job.trigger.timezone) == briefing.settings.TIMEZONE
    finally:
        sched.scheduler.shutdown(wait=False)


@pytest.mark.asyncio
async def test_ouverture_prepare_le_briefing_manquant(client, auth_headers, monkeypatch):
    lances = []

    async def sans_modele(user_id):  # ni modèle ni vraie base
        lances.append(user_id)
        briefing._en_preparation.discard(user_id)

    monkeypatch.setattr(briefing, "_prepare", sans_modele)
    briefing._en_preparation.clear()

    r = await client.post("/api/v1/reports/daily/ensure", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["state"] == "preparing"
    assert r.json()["today"] == briefing.today_local().isoformat()


@pytest.mark.asyncio
async def test_ouverture_ne_relance_pas_si_deja_pret(client, auth_headers, db_session, monkeypatch):
    async def interdit(user_id):
        raise AssertionError("ne doit pas régénérer un briefing existant")

    monkeypatch.setattr(briefing, "_prepare", interdit)
    moi = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"]
    db_session.add(DailyReportModel(
        user_id=moi, date=briefing.today_local(), summary="Prêt", total_projects=0,
        active_projects=0, total_tasks=0, completed_today=0, blockers_count=0,
        projects_analysis=[], top_priorities=[], recommendations=[],
    ))
    await db_session.commit()

    r = await client.post("/api/v1/reports/daily/ensure", headers=auth_headers)
    assert r.json()["state"] == "ready"


@pytest.mark.asyncio
async def test_une_seule_preparation_a_la_fois(client, auth_headers, monkeypatch):
    lances = []

    async def lent(user_id):
        lances.append(user_id)  # reste « en préparation »

    monkeypatch.setattr(briefing, "_prepare", lent)
    briefing._en_preparation.clear()
    for _ in range(3):
        await client.post("/api/v1/reports/daily/ensure", headers=auth_headers)
    import asyncio
    await asyncio.sleep(0)
    assert len(lances) == 1
    briefing._en_preparation.clear()
