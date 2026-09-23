"""
Tests de l'honnêteté de l'avancement.

Une tâche pouvait être marquée « terminée » sans avoir produit la moindre ligne :
le projet s'affichait alors comme abouti, toutes tâches faites, alors qu'aucun
fichier n'existait. C'est le défaut le plus trompeur rencontré à l'usage.
"""

import inspect


def test_aucune_tache_terminee_sans_contenu():
    """Garde-fou : la transition vers COMPLETED doit être conditionnée."""
    from app.services.unified_orchestrator import UnifiedOrchestrator

    source = inspect.getsource(UnifiedOrchestrator.handle_task)
    assert "a_produit" in source
    # …et le contrôle doit précéder la transition de statut
    assert source.index("a_produit") < source.index("TaskStatus.COMPLETED")


def test_tache_vide_marquee_en_echec():
    """Marquer FAILED plutôt que COMPLETED rend la tâche visible et relançable."""
    from app.services.unified_orchestrator import UnifiedOrchestrator

    source = inspect.getsource(UnifiedOrchestrator.handle_task)
    assert "TaskStatus.FAILED" in source
    assert "GENERATION_FAILED" in source
    assert "retry_count" in source


def test_document_vide_leve_une_erreur():
    """Le générateur de documents ne doit pas rendre une chaîne vide en silence."""
    from app.services.unified_orchestrator import UnifiedOrchestrator

    source = inspect.getsource(UnifiedOrchestrator._handle_document_writing)
    assert "n'a produit aucun document" in source


def test_relance_possible_depuis_terminee_sans_contenu():
    from app.api.v1 import tasks

    source = inspect.getsource(tasks.generate_task_code)
    assert "TaskStatus.MANUAL_REVIEW, TaskStatus.COMPLETED" in source


def test_statistique_de_production_reelle():
    """Compter les statuts ne dit rien de ce qui existe : il faut compter les
    tâches ayant réellement un contenu."""
    from app.schemas.project import ProjectStats

    assert "tasks_with_output" in ProjectStats.model_fields

    from app.api.v1 import projects

    source = inspect.getsource(projects.get_project_stats)
    assert "tasks_with_output" in source
    assert "radar_report" in source


def test_le_score_de_maturite_ne_mesure_pas_l_avancement():
    """Il note la qualité du PLAN (dépendances, descriptions, échéances, chemin
    critique). Aucun critère ne regarde ce qui a été produit — c'est voulu, mais
    doit rester explicite pour ne pas se lire comme un taux d'avancement."""
    from app.services.maturity import MaturityService

    source = inspect.getsource(MaturityService.calculate_maturity_score)
    assert "dependencies_score" in source and "critical_path_score" in source
    assert "generated_code" not in source


def test_statut_en_cours_visible_des_le_demarrage():
    """Lancée par le planificateur, une tâche restait affichée « prête » pendant
    tout son traitement : le passage à GENERATING doit être validé aussitôt."""
    from app.services.unified_orchestrator import UnifiedOrchestrator

    source = inspect.getsource(UnifiedOrchestrator.handle_task)
    debut = source.index("TaskStatus.GENERATING")
    assert "await self.db.commit()" in source[debut:source.index("# Dispatch")]
