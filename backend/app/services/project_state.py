"""
Priorité et mise de côté des projets.

Avec une vingtaine de projets, tous au même niveau, le briefing parlait autant
d'un projet à dix-huit mois que d'un rendu dans quinze jours. L'utilisateur
range ses projets actifs par ordre de priorité, et peut en mettre en pause
(avec une date de reprise facultative) ou en sommeil (sans date).

Un projet en pause ou en sommeil sort du briefing et ses tâches automatiques
(veilles récurrentes, relances) s'arrêtent ; rien n'est annulé, contrairement
à l'archivage.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectStatus

# Projets « vivants » : ceux dont on parle et qui travaillent tout seuls
ACTIVE_STATUSES = (ProjectStatus.ACTIVE, ProjectStatus.PLANNING, ProjectStatus.IDEATION)


async def resume_due_projects(db: AsyncSession, user_id: Optional[int] = None) -> List[Project]:
    """Remet en actif les projets en pause dont la date de reprise est arrivée."""
    from app.services.briefing import today_local

    query = select(Project).where(
        Project.status == ProjectStatus.PAUSED,
        Project.resume_on.isnot(None),
        Project.resume_on <= today_local(),
    )
    if user_id is not None:
        query = query.where(Project.user_id == user_id)
    repris = (await db.execute(query)).scalars().all()
    for projet in repris:
        projet.status = ProjectStatus.ACTIVE
        projet.resume_on = None
    if repris:
        await db.flush()
    return list(repris)
