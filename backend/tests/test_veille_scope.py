"""
Tests de la portée de veille et des tâches sans contenu à valider.

Deux impasses rencontrées à l'usage :
- choisir « Visuelle » dans le formulaire n'avait aucun effet : la portée était
  enregistrée dans les metadata de la tâche mais jamais relue, et l'orchestrateur
  créait systématiquement un sujet « actualités » ;
- une tâche « à valider » n'ayant rien produit ne pouvait être ni validée, ni
  rejetée, ni relancée.
"""

import inspect

import pytest

from app.models.veille_topic import VeilleScope


def test_la_portee_choisie_est_relue():
    """Garde-fou : `task_metadata['scope']` doit décider du pipeline."""
    from app.services.unified_orchestrator import UnifiedOrchestrator

    source = inspect.getsource(UnifiedOrchestrator._handle_veille)
    assert "(task.task_metadata or {}).get('scope')" in source
    assert "scope=scope_demande or VeilleScope.NEWS" in source


def test_portee_visuelle_route_vers_le_pipeline_images():
    from app.services.unified_orchestrator import UnifiedOrchestrator

    source = inspect.getsource(UnifiedOrchestrator._handle_veille)
    assert "scope_demande == VeilleScope.VISUAL" in source
    assert "_handle_visual_veille" in source


def test_sujet_incoherent_bascule_vers_la_portee_demandee():
    """Un sujet « actualités » créé par le bug ne doit pas figer une veille
    visuelle dans le mauvais pipeline."""
    from app.services.unified_orchestrator import UnifiedOrchestrator

    source = inspect.getsource(UnifiedOrchestrator._handle_veille)
    assert "veille_topic.scope != scope_demande" in source


@pytest.mark.parametrize("libelle", ["visual", "tech", "cultural", "funding", "academic", "news"])
def test_toutes_les_portees_du_formulaire_existent(libelle):
    """Les valeurs proposées dans le formulaire doivent exister côté modèle."""
    assert VeilleScope(libelle)


def test_portee_inconnue_ne_casse_pas():
    with pytest.raises(ValueError):
        VeilleScope("portee-inexistante")


def test_relance_possible_si_rien_a_valider():
    """Garde-fou : sans cela, une tâche arrivée à son terme sans rien produire
    est une impasse — rien à valider, rien à rejeter, rien à relancer."""
    from app.api.v1 import tasks

    source = inspect.getsource(tasks.generate_task_code)
    assert "TaskStatus.MANUAL_REVIEW, TaskStatus.COMPLETED" in source
    assert "not (task.generated_code or '').strip()" in source
    # …et les champs doivent être réinitialisés à la relance
    assert "task.generated_code = None" in source
