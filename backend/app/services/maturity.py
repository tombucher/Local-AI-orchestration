"""
Service de calcul du score de maturité des projets

Ce service calcule un score de maturité (0-100) pour les projets basé sur :
- Présence de dépendances entre tâches (30%)
- Descriptions remplies (20%)
- Dates d'échéance fixées (20%)
- Présence d'un chemin critique calculable (30%)
"""

from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.task import Task, TaskStatus
from app.models.project import Project
from app.services.critical_path import CriticalPathService

class MaturityService:
    """
    Service pour calculer le score de maturité des projets
    """

    def __init__(self):
        self.critical_path_service = CriticalPathService()

    async def calculate_maturity_score(
        self,
        project: Project,
        db: AsyncSession
    ) -> int:
        """
        Calcule le score de maturité pour un projet

        Args:
            project: Le projet à analyser
            db: Session de base de données

        Returns:
            Score de maturité (0-100)
        """
        # Récupérer toutes les tâches du projet (non annulées)
        tasks_query = select(Task).where(
            Task.project_id == project.id,
            Task.status != TaskStatus.CANCELLED
        )
        result = await db.execute(tasks_query)
        tasks = result.scalars().all()

        if not tasks:
            return 0  # Pas de tâches = maturité 0

        # Calculer les différents critères
        dependencies_score = await self._calculate_dependencies_score(tasks, db)
        descriptions_score = self._calculate_descriptions_score(tasks)
        deadlines_score = self._calculate_deadlines_score(tasks)
        critical_path_score = await self._calculate_critical_path_score(tasks, db)

        # Calculer le score total (pondéré)
        total_score = (
            dependencies_score * 0.30 +
            descriptions_score * 0.20 +
            deadlines_score * 0.20 +
            critical_path_score * 0.30
        )

        return int(round(total_score))

    async def _calculate_dependencies_score(
        self,
        tasks: List[Task],
        db: AsyncSession
    ) -> float:
        """
        Calcule le score pour la présence de dépendances (30%)

        Critères:
        - 0% si aucune tâche n'a de dépendances
        - 100% si au moins 50% des tâches ont des dépendances
        - Score linéaire entre 0 et 100% selon le pourcentage de tâches avec dépendances
        """
        if not tasks:
            return 0.0

        from app.models.task import task_dependencies

        # Compter les tâches ayant au moins une dépendance via requête directe
        # (évite db.refresh qui casse le lazy="selectin" en contexte async)
        task_ids = [t.id for t in tasks]
        deps_query = select(task_dependencies.c.task_id).where(
            task_dependencies.c.task_id.in_(task_ids)
        ).distinct()
        result = await db.execute(deps_query)
        tasks_with_deps_ids = {row[0] for row in result.all()}

        tasks_with_dependencies = len(tasks_with_deps_ids)

        # Calculer le pourcentage de tâches avec dépendances
        percentage_with_dependencies = (tasks_with_dependencies / len(tasks)) * 100

        # Score linéaire (0-100)
        return min(percentage_with_dependencies, 100.0)

    def _calculate_descriptions_score(
        self,
        tasks: List[Task]
    ) -> float:
        """
        Calcule le score pour les descriptions remplies (20%)

        Critères:
        - 0% si aucune tâche n'a de description
        - 100% si toutes les tâches ont des descriptions non vides
        - Score linéaire selon le pourcentage de tâches avec descriptions
        """
        if not tasks:
            return 0.0

        # Compter le nombre de tâches avec descriptions non vides
        tasks_with_descriptions = 0

        for task in tasks:
            if task.description and len(task.description.strip()) > 0:
                tasks_with_descriptions += 1

        # Calculer le pourcentage de tâches avec descriptions
        percentage_with_descriptions = (tasks_with_descriptions / len(tasks)) * 100

        return min(percentage_with_descriptions, 100.0)

    def _calculate_deadlines_score(
        self,
        tasks: List[Task]
    ) -> float:
        """
        Calcule le score pour les dates d'échéance fixées (20%)

        Critères:
        - 0% si aucune tâche n'a de durée estimée
        - 100% si toutes les tâches ont des durées estimées
        - Score linéaire selon le pourcentage de tâches avec durées estimées
        """
        if not tasks:
            return 0.0

        # Compter le nombre de tâches avec durées estimées
        tasks_with_deadlines = 0

        for task in tasks:
            if task.estimated_duration and task.estimated_duration > 0:
                tasks_with_deadlines += 1

        # Calculer le pourcentage de tâches avec durées estimées
        percentage_with_deadlines = (tasks_with_deadlines / len(tasks)) * 100

        return min(percentage_with_deadlines, 100.0)

    async def _calculate_critical_path_score(
        self,
        tasks: List[Task],
        db: AsyncSession
    ) -> float:
        """
        Calcule le score pour la présence d'un chemin critique calculable (30%)

        Critères:
        - 0% si le chemin critique ne peut pas être calculé (cycle ou pas assez de données)
        - 100% si le chemin critique peut être calculé avec succès
        - 50% si le chemin critique peut être calculé mais il n'y a pas de tâches critiques
        """
        if not tasks:
            return 0.0

        try:
            # Essayer de calculer le chemin critique
            critical_path_data = await self.critical_path_service.calculate_critical_path(tasks, db)

            # Vérifier si des tâches critiques ont été identifiées
            if critical_path_data['critical_tasks']:
                return 100.0  # Chemin critique calculé avec des tâches critiques
            else:
                return 50.0  # Chemin critique calculé mais pas de tâches critiques

        except ValueError as e:
            # Erreur lors du calcul (cycle détecté ou autre problème)
            if "Cycle detected" in str(e):
                return 0.0  # Cycle détecté = chemin critique impossible
            else:
                return 0.0  # Autres erreurs = chemin critique impossible
        except Exception:
            # Autres exceptions
            return 0.0

    async def update_project_maturity_score(
        self,
        project_id: int,
        db: AsyncSession
    ) -> int:
        """
        Met à jour le score de maturité d'un projet et retourne le nouveau score

        Args:
            project_id: ID du projet
            db: Session de base de données

        Returns:
            Nouveau score de maturité
        """
        # Récupérer le projet
        query = select(Project).where(Project.id == project_id)
        result = await db.execute(query)
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Calculer le nouveau score
        new_score = await self.calculate_maturity_score(project, db)

        # Mettre à jour le score
        project.maturity_score = new_score
        await db.commit()
        await db.refresh(project)

        return new_score

    async def analyze_maturity_criteria(
        self,
        project: Project,
        db: AsyncSession
    ) -> dict:
        """
        Analyse détaillée des critères de maturité

        Args:
            project: Le projet à analyser
            db: Session de base de données

        Returns:
            Analyse détaillée par critère
        """
        # Récupérer toutes les tâches du projet (non annulées)
        tasks_query = select(Task).where(
            Task.project_id == project.id,
            Task.status != TaskStatus.CANCELLED
        )
        result = await db.execute(tasks_query)
        tasks = result.scalars().all()

        if not tasks:
            return {
                'dependencies': {'score': 0, 'details': 'Aucune tâche disponible'},
                'descriptions': {'score': 0, 'details': 'Aucune tâche disponible'},
                'deadlines': {'score': 0, 'details': 'Aucune tâche disponible'},
                'critical_path': {'score': 0, 'details': 'Aucune tâche disponible'}
            }

        # Analyser les dépendances via requête directe (évite db.refresh async)
        from app.models.task import task_dependencies as deps_table
        task_ids = [t.id for t in tasks]
        deps_query = select(deps_table.c.task_id).where(
            deps_table.c.task_id.in_(task_ids)
        ).distinct()
        deps_result = await db.execute(deps_query)
        tasks_with_deps_ids = {row[0] for row in deps_result.all()}
        tasks_with_dependencies = len(tasks_with_deps_ids)

        dependencies_score = min((tasks_with_dependencies / len(tasks)) * 100, 100.0)

        # Analyser les descriptions
        tasks_with_descriptions = 0
        for task in tasks:
            if task.description and len(task.description.strip()) > 0:
                tasks_with_descriptions += 1

        descriptions_score = min((tasks_with_descriptions / len(tasks)) * 100, 100.0)

        # Analyser les deadlines
        tasks_with_deadlines = 0
        for task in tasks:
            if task.estimated_duration and task.estimated_duration > 0:
                tasks_with_deadlines += 1

        deadlines_score = min((tasks_with_deadlines / len(tasks)) * 100, 100.0)

        # Analyser le chemin critique
        critical_path_score = 0.0
        critical_path_details = 'Chemin critique non calculable'

        try:
            critical_path_service = CriticalPathService()
            critical_path_data = await critical_path_service.calculate_critical_path(tasks, db)

            if critical_path_data['critical_tasks']:
                critical_path_score = 100.0
                critical_path_details = f"Chemin critique calculé avec {len(critical_path_data['critical_tasks'])} tâches critiques"
            else:
                critical_path_score = 50.0
                critical_path_details = "Chemin critique calculé mais aucune tâche critique identifiée"
        except ValueError as e:
            if "Cycle detected" in str(e):
                critical_path_details = "Cycle détecté dans les dépendances - chemin critique impossible"
            else:
                critical_path_details = f"Erreur lors du calcul du chemin critique: {str(e)}"
        except Exception as e:
            critical_path_details = f"Erreur inattendue: {str(e)}"

        return {
            'dependencies': {
                'score': round(dependencies_score, 1),
                'details': f"{tasks_with_dependencies}/{len(tasks)} tâches avec dépendances",
                'percentage': round(dependencies_score, 1)
            },
            'descriptions': {
                'score': round(descriptions_score, 1),
                'details': f"{tasks_with_descriptions}/{len(tasks)} tâches avec descriptions",
                'percentage': round(descriptions_score, 1)
            },
            'deadlines': {
                'score': round(deadlines_score, 1),
                'details': f"{tasks_with_deadlines}/{len(tasks)} tâches avec durées estimées",
                'percentage': round(deadlines_score, 1)
            },
            'critical_path': {
                'score': round(critical_path_score, 1),
                'details': critical_path_details,
                'percentage': round(critical_path_score, 1)
            }
        }

    async def generate_improvement_suggestions(
        self,
        project: Project,
        db: AsyncSession
    ) -> list:
        """
        Génère des conseils personnalisés pour améliorer le score de maturité

        Args:
            project: Le projet à analyser
            db: Session de base de données

        Returns:
            Liste de conseils d'amélioration
        """
        # Analyser les critères
        criteria = await self.analyze_maturity_criteria(project, db)

        suggestions = []

        # Conseils pour les dépendances
        if criteria['dependencies']['score'] < 50:
            suggestions.append(
                "Ajoutez des dépendances entre les tâches pour mieux structurer votre projet. "
                "Les dépendances aident à identifier l'ordre d'exécution et les tâches critiques."
            )

        # Conseils pour les descriptions
        if criteria['descriptions']['score'] < 50:
            suggestions.append(
                "Ajoutez des descriptions détaillées à vos tâches. "
                "Des descriptions claires améliorent la compréhension et la planification."
            )

        # Conseils pour les deadlines
        if criteria['deadlines']['score'] < 50:
            suggestions.append(
                "Estimez la durée de chaque tâche. "
                "Les estimations de durée sont essentielles pour la planification et le calcul du chemin critique."
            )

        # Conseils pour le chemin critique
        if criteria['critical_path']['score'] < 50:
            suggestions.append(
                "Résolvez les problèmes de dépendances (cycles détectés) et assurez-vous que "
                "toutes les tâches ont des durées estimées pour permettre le calcul du chemin critique."
            )

        # Conseils généraux
        if len(suggestions) == 0:
            suggestions.append(
                "Votre projet a déjà un bon niveau de maturité. "
                "Continuez à maintenir les descriptions, dépendances et estimations à jour."
            )

        return suggestions
