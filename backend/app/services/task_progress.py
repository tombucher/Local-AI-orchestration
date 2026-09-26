"""
Suivi d'avancement des tâches longues.

Une veille enchaîne recherche web, flux RSS puis un appel au modèle local par
résultat : plusieurs minutes pendant lesquelles l'interface n'affichait rien
d'autre que « en cours ». On ne sait pas si ça travaille ou si c'est planté.

Le registre est **en mémoire** et non en base, pour deux raisons :
1. la phase d'analyse tourne dans un savepoint ouvert — écrire la progression
   depuis une autre session bloquerait sur le verrou de la ligne `tasks` ;
2. la progression n'a aucune valeur après un redémarrage, puisque le
   redémarrage tue justement la tâche de fond qu'elle décrivait.
"""

import logging
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Au-delà, une progression est considérée comme périmée (processus disparu)
STALE_AFTER_SECONDS = 15 * 60


@dataclass
class TaskProgress:
    """Où en est une tâche longue, du point de vue de l'utilisateur."""

    phase: str                      # identifiant technique : search, rss, analysis…
    label: str                      # texte affiché, en français
    current: Optional[int] = None   # pour les phases dénombrables (analyse n/N)
    total: Optional[int] = None
    updated_at: float = 0.0

    @property
    def percent(self) -> Optional[int]:
        if not self.total:
            return None
        return min(100, round(100 * (self.current or 0) / self.total))


_progress: Dict[int, TaskProgress] = {}


def set_progress(
    task_id: int,
    phase: str,
    label: str,
    current: Optional[int] = None,
    total: Optional[int] = None,
) -> None:
    """Enregistre l'étape courante d'une tâche."""
    _progress[task_id] = TaskProgress(
        phase=phase, label=label, current=current, total=total, updated_at=time.time()
    )
    logger.debug(f"⏳ [TASK-{task_id}] {label}" + (f" ({current}/{total})" if total else ""))


def get_progress(task_id: int) -> Optional[Dict[str, Any]]:
    """Progression d'une tâche, ou None si aucune (ou périmée)."""
    entry = _progress.get(task_id)
    if entry is None:
        return None
    if time.time() - entry.updated_at > STALE_AFTER_SECONDS:
        # Le processus a disparu (redémarrage, crash) : ne pas afficher un
        # avancement figé qui laisserait croire que ça travaille encore.
        _progress.pop(task_id, None)
        return None
    data = asdict(entry)
    data.pop("updated_at", None)
    data["percent"] = entry.percent
    return data


def clear_progress(task_id: int) -> None:
    """À appeler quand la tâche atteint un état terminal."""
    _progress.pop(task_id, None)


# --- Tâches réellement en cours dans CE processus ----------------------------
# Une tâche GENERATING en base mais absente d'ici est morte : le serveur a
# redémarré (rechargement, crash) pendant qu'elle tournait. Le chien de garde
# s'en sert pour la débloquer sans attendre, tout en laissant finir une veille
# longue mais vivante.
_running: Dict[int, float] = {}


def task_started(task_id: int) -> None:
    _running[task_id] = time.time()


def task_finished(task_id: int) -> None:
    _running.pop(task_id, None)


def is_running(task_id: int) -> bool:
    return task_id in _running
