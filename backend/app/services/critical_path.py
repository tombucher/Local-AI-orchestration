"""
Service de calcul du chemin critique (Critical Path Method)

Ce service implémente l'algorithme CPM pour analyser les dépendances entre tâches
et identifier le chemin critique d'un projet.
"""
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from app.models.task import Task
from app.models.task_log import TaskLog, TaskEventType
from app.schemas.task import TaskResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class CriticalPathService:
    """
    Service pour calculer le chemin critique d'un projet

    L'algorithme CPM (Critical Path Method) permet de :
    1. Trouver l'ordre topologique des tâches
    2. Calculer les dates au plus tôt / au plus tard
    3. Identifier les tâches critiques (marge nulle)
    """

    # Durée par défaut quand une tâche n'a pas d'estimation (4 h en secondes) —
    # sans elle, les tâches non estimées ont une barre de largeur nulle au Gantt
    DEFAULT_TASK_DURATION = 4 * 3600
    # Heures travaillées par jour pour projeter les unités CPM en dates calendaires
    WORK_SECONDS_PER_DAY = 6 * 3600

    def __init__(self):
        pass

    async def calculate_critical_path(
        self,
        tasks: List[Task],
        db: AsyncSession
    ) -> Dict:
        """
        Calcule le chemin critique pour une liste de tâches

        Args:
            tasks: Liste des tâches du projet
            db: Session de base de données (pour récupérer les dépendances)

        Returns:
            Dict avec :
            - ordered_tasks: Liste des tâches ordonnées
            - critical_tasks: Liste des IDs des tâches critiques
            - total_duration: Durée totale du projet
            - has_cycle: Booléen indiquant si un cycle a été détecté

        Raises:
            ValueError: Si un cycle est détecté dans les dépendances
        """
        # 1. Construire le graphe des dépendances
        graph, in_degree, task_map = await self._build_dependency_graph(tasks, db)

        # 2. Vérifier les cycles avec l'algorithme de Kahn
        if await self._has_cycle(graph, in_degree):
            raise ValueError("Cycle detected in task dependencies")

        # 3. Calculer l'ordre topologique
        topological_order = await self._topological_sort(graph, in_degree)

        # 4. Calculer les dates au plus tôt / au plus tard
        early_start, early_finish, late_start, late_finish = self._calculate_dates(topological_order, task_map, graph)

        # 5. Identifier les tâches critiques (marge nulle)
        critical_tasks = self._identify_critical_tasks(topological_order, early_start, late_start)

        # 6. Préparer la réponse, avec projection en dates calendaires
        # (ancre = aujourd'hui, WORK_SECONDS_PER_DAY de travail par jour)
        anchor = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)

        def project_date(units: int) -> str:
            days = units / self.WORK_SECONDS_PER_DAY
            return (anchor + timedelta(days=days)).isoformat()

        # Graphe des dépendances inversé pour le frontend (flèches du Gantt)
        dependencies_map = defaultdict(list)
        for prev_id, next_ids in graph.items():
            for next_id in next_ids:
                dependencies_map[next_id].append(prev_id)

        response = {
            'ordered_tasks': [
                {
                    'task_id': task_id,
                    'title': task_map[task_id].title,
                    'status': task_map[task_id].status.value,
                    'early_start': early_start[task_id],
                    'early_finish': early_finish[task_id],
                    'late_start': late_start[task_id],
                    'late_finish': late_finish[task_id],
                    'is_critical': task_id in critical_tasks,
                    'slack': late_start[task_id] - early_start[task_id],
                    'projected_start': project_date(early_start[task_id]),
                    'projected_end': project_date(early_finish[task_id]),
                    'due_date': task_map[task_id].due_date.isoformat() if task_map[task_id].due_date else None,
                    'depends_on': dependencies_map.get(task_id, []),
                }
                for task_id in topological_order
            ],
            'critical_tasks': critical_tasks,
            'total_duration': max(early_finish.values()) if early_finish else 0,
            'projected_end_date': project_date(max(early_finish.values())) if early_finish else None,
            'has_cycle': False
        }

        return response

    async def _build_dependency_graph(
        self,
        tasks: List[Task],
        db: AsyncSession
    ) -> Tuple[Dict[int, List[int]], Dict[int, int], Dict[int, Task]]:
        """
        Construit le graphe des dépendances à partir des tâches

        Returns:
            graph: Dictionnaire {task_id: [depends_on_ids]}
            in_degree: Dictionnaire {task_id: nombre_de_dependances_entrantes}
            task_map: Dictionnaire {task_id: Task}
        """
        from app.models.task import task_dependencies

        graph = defaultdict(list)
        in_degree = defaultdict(int)
        task_map = {}

        # Initialiser avec toutes les tâches
        for task in tasks:
            task_map[task.id] = task
            in_degree[task.id] = 0  # Initialiser à 0

        # Récupérer les dépendances depuis la base de données
        if tasks:
            task_ids = [task.id for task in tasks]
            deps_query = select(task_dependencies).where(
                task_dependencies.c.task_id.in_(task_ids)
            )
            result = await db.execute(deps_query)
            dependencies = result.all()

            # Construire le graphe
            for dep in dependencies:
                task_id = dep.task_id
                depends_on_id = dep.depends_on_id

                # Vérifier que la dépendance fait partie des tâches du projet
                if depends_on_id in task_map:
                    graph[depends_on_id].append(task_id)
                    in_degree[task_id] += 1

        return graph, in_degree, task_map

    async def _has_cycle(
        self,
        graph: Dict[int, List[int]],
        in_degree: Dict[int, int]
    ) -> bool:
        """
        Détecte les cycles dans le graphe des dépendances

        Utilise l'algorithme de Kahn pour la détection de cycles
        """
        # Créer une copie du degré entrant
        in_degree_copy = in_degree.copy()
        queue = deque()

        # Initialiser la queue avec les nœuds sans dépendances
        for node in in_degree_copy:
            if in_degree_copy[node] == 0:
                queue.append(node)

        # Compter le nombre de nœuds traités
        processed = 0
        total_nodes = len(in_degree_copy)

        while queue:
            node = queue.popleft()
            processed += 1

            # Mettre à jour les dépendances
            for neighbor in graph.get(node, []):
                in_degree_copy[neighbor] -= 1
                if in_degree_copy[neighbor] == 0:
                    queue.append(neighbor)

        # Si tous les nœuds n'ont pas été traités, il y a un cycle
        return processed != total_nodes

    async def _topological_sort(
        self,
        graph: Dict[int, List[int]],
        in_degree: Dict[int, int]
    ) -> List[int]:
        """
        Effectue un tri topologique des tâches

        Utilise l'algorithme de Kahn
        """
        in_degree_copy = in_degree.copy()
        queue = deque()

        # Initialiser la queue avec les nœuds sans dépendances
        for node in in_degree_copy:
            if in_degree_copy[node] == 0:
                queue.append(node)

        topological_order = []

        while queue:
            node = queue.popleft()
            topological_order.append(node)

            # Mettre à jour les dépendances
            for neighbor in graph.get(node, []):
                in_degree_copy[neighbor] -= 1
                if in_degree_copy[neighbor] == 0:
                    queue.append(neighbor)

        return topological_order

    def _calculate_dates(
        self,
        topological_order: List[int],
        task_map: Dict[int, Task],
        graph: Dict[int, List[int]]
    ) -> Tuple[Dict[int, int], Dict[int, int], Dict[int, int], Dict[int, int]]:
        """
        Calcule les dates au plus tôt et au plus tard

        Returns:
            early_start, early_finish, late_start, late_finish
        """
        # Initialiser les dictionnaires
        early_start = {task_id: 0 for task_id in topological_order}
        early_finish = {}
        late_start = {}
        late_finish = {}

        # Calcul des dates au plus tôt (forward pass)
        for task_id in topological_order:
            task = task_map[task_id]
            duration = task.estimated_duration or self.DEFAULT_TASK_DURATION

            # La date de début au plus tôt est le max des dates de fin des dépendances
            max_prev_finish = 0
            for prev_task_id in self._get_predecessors(task_id, task_map, graph):
                if prev_task_id in early_finish:
                    max_prev_finish = max(max_prev_finish, early_finish[prev_task_id])

            early_start[task_id] = max_prev_finish
            early_finish[task_id] = early_start[task_id] + duration

        # Calcul des dates au plus tard (backward pass)
        # Initialiser la date de fin au plus tard pour la dernière tâche
        if topological_order:
            last_task_id = topological_order[-1]
            late_finish[last_task_id] = early_finish[last_task_id]
            late_start[last_task_id] = early_start[last_task_id]

            # Parcourir en sens inverse
            for i in range(len(topological_order) - 2, -1, -1):
                task_id = topological_order[i]
                task = task_map[task_id]
                duration = task.estimated_duration or self.DEFAULT_TASK_DURATION

                # La date de fin au plus tard est le min des dates de début des successeurs
                min_next_start = float('inf')
                for next_task_id in self._get_successors(task_id, task_map, graph):
                    if next_task_id in late_start:
                        min_next_start = min(min_next_start, late_start[next_task_id])

                # Si pas de successeur, utiliser la date de fin au plus tôt
                if min_next_start == float('inf'):
                    late_finish[task_id] = early_finish[task_id]
                else:
                    late_finish[task_id] = min_next_start
                late_start[task_id] = late_finish[task_id] - duration

        return early_start, early_finish, late_start, late_finish

    def _get_predecessors(self, task_id: int, task_map: Dict[int, Task], graph: Dict[int, List[int]]) -> List[int]:
        """Retourne les IDs des tâches dont dépend la tâche donnée"""
        # Retourner les prédécesseurs à partir du graphe
        predecessors = []
        for node, neighbors in graph.items():
            if task_id in neighbors:
                predecessors.append(node)
        return predecessors

    def _get_successors(self, task_id: int, task_map: Dict[int, Task], graph: Dict[int, List[int]]) -> List[int]:
        """Retourne les IDs des tâches qui dépendent de la tâche donnée"""
        # Retourner les successeurs à partir du graphe
        return graph.get(task_id, [])

    def _identify_critical_tasks(
        self,
        topological_order: List[int],
        early_start: Dict[int, int],
        late_start: Dict[int, int]
    ) -> List[int]:
        """
        Identifie les tâches critiques (marge nulle)

        Une tâche est critique si early_start == late_start
        """
        critical_tasks = []

        for task_id in topological_order:
            if early_start[task_id] == late_start[task_id]:
                critical_tasks.append(task_id)

        return critical_tasks

    async def create_critical_path_log(
        self,
        db: AsyncSession,
        project_id: int,
        user_id: int,
        critical_path_data: Dict
    ) -> None:
        """
        Crée un log pour le calcul du chemin critique
        """
        # TODO: Ajouter TaskEventType.CRITICAL_PATH_CALCULATED à l'enum si nécessaire
        # Pour l'instant, on skip le logging pour éviter l'erreur
        pass