"""
Service de génération de rapports quotidiens.
Analyse tous les projets actifs et génère un rapport avec suggestions d'actions.
"""

import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.project import Project
from app.services.project_analyzer import ProjectAnalyzer, Blocker
from app.services.modules.analyzer import AnalyzerModule


# ============================================================
# SCHEMAS PYDANTIC
# ============================================================

class ProjectStatus(BaseModel):
    """Statut d'un projet dans le rapport quotidien."""
    project_id: int
    project_name: str
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    ready_tasks: int
    failed_tasks: int
    completion_rate: float  # 0-100
    p1_tasks: int
    blockers: List[Blocker] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    health_status: str  # 'healthy', 'warning', 'critical'
    # Action concrète démarrable en 5 minutes, générée par l'IA
    next_obvious_action: Optional[str] = None
    # Titres de tâches prêtes / en revue (contexte pour l'IA et le frontend)
    ready_task_titles: List[str] = Field(default_factory=list)
    # Projet stagnant : suggestions de tâches générées par l'IA pour relancer
    is_stagnant: bool = False
    suggested_tasks: List[Dict] = Field(default_factory=list)


class DailyReport(BaseModel):
    """Rapport quotidien complet."""
    user_id: int
    date: datetime
    summary: str  # Résumé général par l'IA
    total_projects: int
    active_projects: int
    total_tasks: int
    completed_today: int
    projects: List[ProjectStatus] = Field(default_factory=list)
    top_priorities: List[str] = Field(default_factory=list)  # Top 3 actions du jour
    blockers_count: int
    recommendations: List[str] = Field(default_factory=list)


# ============================================================
# SERVICE PRINCIPAL
# ============================================================

class DailyReviewService:
    """Service de génération de rapports quotidiens intelligents."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.analyzer = ProjectAnalyzer(db)
        self.text_generator = AnalyzerModule()

    async def generate_daily_report(self, user_id: int) -> DailyReport:
        """
        Génère le rapport quotidien pour un utilisateur.

        Étapes:
        1. Récupérer tous les projets de l'utilisateur
        2. Analyser chaque projet (tâches, progression, blocages)
        3. Synthétiser avec l'IA
        4. Générer les top 3 actions du jour
        """
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)

        # 1. Récupérer les projets actifs de l'utilisateur (exclure les archivés)
        from app.models.project import ProjectStatus as ProjectStatusEnum
        stmt = select(Project).where(
            and_(
                Project.user_id == user_id,
                Project.status != ProjectStatusEnum.ARCHIVED
            )
        )
        result = await self.db.execute(stmt)
        projects = result.scalars().all()

        if not projects:
            return DailyReport(
                user_id=user_id,
                date=now,
                summary="Aucun projet actif.",
                total_projects=0,
                active_projects=0,
                total_tasks=0,
                completed_today=0,
                top_priorities=["Créer votre premier projet pour commencer !"],
                blockers_count=0,
            )

        # 2. Analyser chaque projet
        project_statuses = []
        total_tasks_count = 0
        completed_today_count = 0
        all_blockers = []

        for project in projects:
            project_status = await self._analyze_project_status(project, today_start)
            project_statuses.append(project_status)
            total_tasks_count += project_status.total_tasks
            all_blockers.extend(project_status.blockers)

            # Compter les tâches complétées aujourd'hui
            stmt_completed = select(func.count(Task.id)).where(
                and_(
                    Task.project_id == project.id,
                    Task.status == TaskStatus.COMPLETED,
                    Task.completed_at >= today_start
                )
            )
            result_completed = await self.db.execute(stmt_completed)
            completed_today_count += result_completed.scalar() or 0

        # 2bis. Détection de stagnation : projets ACTIVE sans activité récente
        # → suggestions de relance générées par l'IA (max 2 projets par rapport)
        await self._suggest_for_stagnant_projects(user_id, projects, project_statuses)

        # 3. Générer le résumé et les recommandations avec l'IA
        ai_summary = await self._generate_ai_summary(user_id, project_statuses, all_blockers)

        # 4. Construire le rapport final
        report = DailyReport(
            user_id=user_id,
            date=now,
            summary=ai_summary.get("summary", "Rapport quotidien généré."),
            total_projects=len(projects),
            active_projects=len([p for p in project_statuses if p.total_tasks > 0]),
            total_tasks=total_tasks_count,
            completed_today=completed_today_count,
            projects=project_statuses,
            top_priorities=ai_summary.get("top_priorities", []),
            blockers_count=len(all_blockers),
            recommendations=ai_summary.get("recommendations", []),
        )

        return report

    STAGNATION_DAYS = 7

    async def _suggest_for_stagnant_projects(
        self,
        user_id: int,
        projects: List[Project],
        project_statuses: List[ProjectStatus],
    ) -> None:
        """Repère les projets actifs sans activité depuis STAGNATION_DAYS jours
        et leur génère 2-3 suggestions de tâches pour relancer la machine."""
        from app.models.project import ProjectStatus as ProjectStatusEnum

        cutoff = datetime.utcnow() - timedelta(days=self.STAGNATION_DAYS)
        status_by_id = {ps.project_id: ps for ps in project_statuses}
        analyzed = 0

        for project in projects:
            if analyzed >= 2:  # L'analyse LLM est coûteuse : max 2 projets par rapport
                break
            if project.status != ProjectStatusEnum.ACTIVE:
                continue
            ps = status_by_id.get(project.id)
            if not ps or ps.total_tasks == 0:
                continue

            # Dernière activité = dernière création ou complétion de tâche
            stmt = select(func.max(func.coalesce(Task.completed_at, Task.created_at))).where(
                Task.project_id == project.id
            )
            result = await self.db.execute(stmt)
            last_activity = result.scalar()

            if last_activity and last_activity.replace(tzinfo=None) >= cutoff:
                continue

            ps.is_stagnant = True
            try:
                analyzer = ProjectAnalyzer(self.db, user_id=user_id)
                analysis = await analyzer.analyze_project(project.id)
                ps.suggested_tasks = [
                    {
                        "title": t.title,
                        "description": t.description,
                        "task_type": t.task_type.value,
                        "priority": t.priority.value,
                        "estimated_duration": t.estimated_duration,
                        "subtasks": t.subtasks,
                        "llm_prompt": t.llm_prompt,
                        "keywords": t.keywords,
                    }
                    for t in analysis.task_suggestions[:3]
                ]
                analyzed += 1
            except Exception as e:
                print(f"⚠️ Suggestions de relance impossibles pour projet {project.id}: {e}")

    async def _analyze_project_status(
        self,
        project: Project,
        today_start: datetime
    ) -> ProjectStatus:
        """Analyse le statut d'un projet."""

        # Compter les tâches par statut (exclure les tâches annulées)
        stmt = select(
            func.count(Task.id).label('total'),
            func.count(Task.id).filter(Task.status == TaskStatus.COMPLETED).label('completed'),
            func.count(Task.id).filter(Task.status == TaskStatus.GENERATING).label('in_progress'),
            func.count(Task.id).filter(Task.status == TaskStatus.READY).label('ready'),
            func.count(Task.id).filter(Task.status == TaskStatus.FAILED).label('failed'),
            func.count(Task.id).filter(Task.priority == TaskPriority.P1).label('p1'),
        ).where(
            and_(
                Task.project_id == project.id,
                Task.status != TaskStatus.CANCELLED
            )
        )

        result = await self.db.execute(stmt)
        counts = result.one()

        total = counts.total or 0
        completed = counts.completed or 0
        in_progress = counts.in_progress or 0
        ready = counts.ready or 0
        failed = counts.failed or 0
        p1 = counts.p1 or 0

        completion_rate = (completed / total * 100) if total > 0 else 0

        # Récupérer les tâches pour détection de blocages (exclure les annulées)
        stmt_tasks = select(Task).where(
            and_(
                Task.project_id == project.id,
                Task.status != TaskStatus.CANCELLED
            )
        )
        result_tasks = await self.db.execute(stmt_tasks)
        tasks = result_tasks.scalars().all()

        # Détecter les blocages
        blockers = await self.analyzer._detect_blockers(tasks)

        # Déterminer l'état de santé du projet
        health_status = self._determine_health_status(
            total, completed, p1, len(blockers), completion_rate
        )

        # Générer les actions recommandées
        recommended_actions = self._generate_project_recommendations(
            project, tasks, blockers, health_status
        )

        # Titres des tâches actionnables (contexte pour le briefing IA)
        ready_task_titles = [
            t.title for t in tasks
            if t.status in (TaskStatus.READY, TaskStatus.MANUAL_REVIEW, TaskStatus.CREATED)
        ][:5]

        return ProjectStatus(
            project_id=project.id,
            project_name=project.name,
            total_tasks=total,
            completed_tasks=completed,
            in_progress_tasks=in_progress,
            ready_tasks=ready,
            failed_tasks=failed,
            completion_rate=round(completion_rate, 1),
            p1_tasks=p1,
            blockers=blockers,
            recommended_actions=recommended_actions,
            health_status=health_status,
            ready_task_titles=ready_task_titles,
        )

    def _determine_health_status(
        self,
        total: int,
        completed: int,
        p1: int,
        blockers_count: int,
        completion_rate: float
    ) -> str:
        """Détermine l'état de santé d'un projet."""

        if total == 0:
            return "healthy"  # Nouveau projet

        # Critères de santé
        has_critical_blockers = blockers_count > 0
        has_many_p1 = p1 > 3
        low_completion = completion_rate < 20 and total > 5
        very_low_completion = completion_rate < 10 and total > 10

        if very_low_completion or (has_critical_blockers and has_many_p1):
            return "critical"
        elif has_critical_blockers or has_many_p1 or low_completion:
            return "warning"
        else:
            return "healthy"

    def _generate_project_recommendations(
        self,
        project: Project,
        tasks: List[Task],
        blockers: List[Blocker],
        health_status: str
    ) -> List[str]:
        """Génère les recommandations pour un projet."""
        recommendations = []

        # Si blocages, suggérer de les résoudre
        if blockers:
            high_severity = [b for b in blockers if b.severity == "high"]
            if high_severity:
                recommendations.append(f"Résoudre {len(high_severity)} blocage(s) critique(s)")
            else:
                recommendations.append(f"Résoudre {len(blockers)} blocage(s)")

        # Si beaucoup de tâches P1 prêtes
        p1_ready = [t for t in tasks if t.priority == TaskPriority.P1 and t.status == TaskStatus.READY]
        if len(p1_ready) > 0:
            recommendations.append(f"Démarrer {len(p1_ready)} tâche(s) P1 en attente")

        # Si tâches en revue manuelle
        manual_review = [t for t in tasks if t.status == TaskStatus.MANUAL_REVIEW]
        if manual_review:
            recommendations.append(f"Valider {len(manual_review)} tâche(s) en revue")

        # Si tâches échouées
        failed = [t for t in tasks if t.status == TaskStatus.FAILED]
        if failed:
            recommendations.append(f"Analyser {len(failed)} tâche(s) échouée(s)")

        # Si projet sans tâches
        if len(tasks) == 0:
            recommendations.append("Analyser le projet pour générer des tâches")

        return recommendations[:3]  # Max 3 actions par projet

    async def _generate_ai_summary(
        self,
        user_id: int,
        projects: List[ProjectStatus],
        blockers: List[Blocker]
    ) -> Dict:
        """Génère le briefing du matin : résumé éditorial, top 3 du jour,
        et une « prochaine action évidente » par projet."""

        # Échéances de financement à venir (30 jours)
        from app.models.veille_result import VeilleResult, VeilleResultStatus
        from app.models.veille_topic import VeilleTopic
        deadlines_stmt = (
            select(VeilleResult.title, VeilleResult.deadline)
            .join(VeilleTopic, VeilleResult.topic_id == VeilleTopic.id)
            .join(Project, VeilleTopic.project_id == Project.id)
            .where(
                Project.user_id == user_id,
                VeilleResult.deadline != None,  # noqa: E711
                VeilleResult.deadline >= datetime.utcnow(),
                VeilleResult.deadline <= datetime.utcnow() + timedelta(days=30),
                VeilleResult.status != VeilleResultStatus.DISMISSED,
            )
            .order_by(VeilleResult.deadline.asc())
            .limit(5)
        )
        deadlines_rows = (await self.db.execute(deadlines_stmt)).all()
        upcoming_deadlines = [
            {"title": t, "deadline": d.strftime("%Y-%m-%d")} for t, d in deadlines_rows
        ]

        context = {
            "upcoming_funding_deadlines": upcoming_deadlines,
            "projects": [
                {
                    "name": p.project_name,
                    "total_tasks": p.total_tasks,
                    "completed_tasks": p.completed_tasks,
                    "completion_rate": p.completion_rate,
                    "p1_tasks": p.p1_tasks,
                    "health": p.health_status,
                    "blockers": len(p.blockers),
                    "actionable_tasks": p.ready_task_titles,
                }
                for p in projects
            ],
            "total_blockers": len(blockers),
        }

        prompt = f"""Tu écris le briefing du matin d'un créateur indépendant (art numérique + tech) dans son journal d'atelier. Ton rôle : donner envie de s'y mettre, pas faire un rapport de gestion.

ÉTAT DES PROJETS :
{json.dumps(context, indent=2, ensure_ascii=False)}

MISSION :
1. "summary" : 2-3 phrases en FRANÇAIS, ton chaleureux et direct (tutoiement), qui racontent où en est le travail et ce qui rend la journée intéressante. Pas de jargon corporate ("complétion", "blocages critiques"), pas de pourcentages secs.
2. "top_priorities" : les 3 actions du jour, formulées comme des phrases concrètes commençant par un verbe, en citant les vrais noms de tâches/projets. Si une échéance de financement (upcoming_funding_deadlines) approche, elle passe en priorité 1 avec sa date.
3. "projects" : pour CHAQUE projet, une "next_obvious_action" — LA première petite action concrète, démarrable en 5 minutes, qui débloque la suite (ex : "Relis le code du mapping audio et valide-le", PAS "Avancer sur le projet").
4. "recommendations" : 1-2 conseils stratégiques courts.

RÉPONDS UNIQUEMENT EN JSON VALIDE (sans markdown) :
{{
  "summary": "…",
  "top_priorities": ["…", "…", "…"],
  "projects": [
    {{"name": "nom exact du projet", "next_obvious_action": "…"}}
  ],
  "recommendations": ["…"]
}}"""

        try:
            # Modèle préféré de l'utilisateur (analysis), appel async (thread)
            analyzer = ProjectAnalyzer(self.db, user_id=user_id)
            await analyzer._load_user_model_preference(usage="analysis")
            response = await self.text_generator._generate_text_async(prompt, model=analyzer.model)

            summary = ProjectAnalyzer._parse_json_lenient(response.strip())

            # Mapper les next_obvious_action sur les ProjectStatus
            # (matching tolérant : les petits modèles déforment parfois les noms)
            llm_projects = [
                proj for proj in summary.get("projects", []) if isinstance(proj, dict)
            ]
            for p in projects:
                name = p.project_name.casefold()
                for proj in llm_projects:
                    llm_name = str(proj.get("name", "")).casefold()
                    if llm_name and (llm_name in name or name in llm_name):
                        p.next_obvious_action = proj.get("next_obvious_action")
                        break
                # Repli : première tâche actionnable du projet
                if not p.next_obvious_action and p.ready_task_titles:
                    p.next_obvious_action = f"Reprendre « {p.ready_task_titles[0]} »"

            return summary

        except Exception as e:
            print(f"❌ Erreur génération résumé IA: {e}")
            # Fallback manuel
            for p in projects:
                if p.ready_task_titles and not p.next_obvious_action:
                    p.next_obvious_action = f"Reprendre « {p.ready_task_titles[0]} »"
            return {
                "summary": f"Tu as {len(projects)} projet(s) en cours. "
                           f"{'Quelques points méritent ton attention aujourd' + chr(39) + 'hui.' if blockers else 'La voie est libre — choisis un projet et avance.'}",
                "top_priorities": [
                    "Résoudre les blocages en attente" if blockers else "Choisir la tâche qui te fait le plus envie",
                    "Avancer sur les tâches P1",
                    "Valider les tâches en revue",
                ],
                "recommendations": [
                    "Concentre-toi sur un projet à la fois",
                    "Bloque 2-3 heures de travail profond aujourd'hui",
                ],
            }
