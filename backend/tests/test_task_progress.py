"""
Tests du registre d'avancement des tâches longues.

Il est volontairement en mémoire : la phase d'analyse d'une veille tourne dans un
savepoint ouvert, donc écrire la progression en base bloquerait sur le verrou de
la ligne `tasks`.
"""

import time

import pytest

from app.services import task_progress as tp


@pytest.fixture(autouse=True)
def registre_vide():
    tp._progress.clear()
    yield
    tp._progress.clear()


def test_aucune_progression_par_defaut():
    assert tp.get_progress(999) is None


def test_etape_sans_compteur():
    tp.set_progress(1, "search", "Recherche web · 4 requêtes")
    p = tp.get_progress(1)
    assert p["phase"] == "search"
    assert p["label"] == "Recherche web · 4 requêtes"
    # Étape non dénombrable : pas de pourcentage inventé
    assert p["percent"] is None


def test_etape_avec_compteur():
    tp.set_progress(1, "analysis", "Analyse de pertinence par l'IA", current=3, total=12)
    p = tp.get_progress(1)
    assert (p["current"], p["total"]) == (3, 12)
    assert p["percent"] == 25


def test_pourcentage_plafonne_a_100():
    tp.set_progress(1, "analysis", "…", current=15, total=12)
    assert tp.get_progress(1)["percent"] == 100


def test_derniere_etape_ecrase_la_precedente():
    tp.set_progress(1, "search", "Recherche…")
    tp.set_progress(1, "rss", "Flux RSS…")
    assert tp.get_progress(1)["phase"] == "rss"


def test_clear_progress():
    tp.set_progress(1, "search", "Recherche…")
    tp.clear_progress(1)
    assert tp.get_progress(1) is None


def test_progression_perimee_ignoree():
    """Après un redémarrage, la tâche est morte : ne pas afficher un avancement figé."""
    tp.set_progress(1, "analysis", "…", current=2, total=10)
    tp._progress[1].updated_at = time.time() - (tp.STALE_AFTER_SECONDS + 1)
    assert tp.get_progress(1) is None
    assert 1 not in tp._progress  # purgé au passage


def test_taches_independantes():
    tp.set_progress(1, "search", "A")
    tp.set_progress(2, "rss", "B")
    assert tp.get_progress(1)["label"] == "A"
    assert tp.get_progress(2)["label"] == "B"
    tp.clear_progress(1)
    assert tp.get_progress(2) is not None


# ------------------------------------------------ streaming non bloquant ----

def test_le_streaming_ollama_est_asynchrone():
    """Garde-fou : itérer le client Ollama SYNCHRONE dans une coroutine gelait
    toute l'API pendant la durée d'une génération (mesuré : zéro tick de la
    boucle d'événements en 7,4 s). Le streaming doit rester en AsyncClient."""
    import inspect

    from app.services.llm_client import OllamaClient

    for methode in (OllamaClient.generate_code, OllamaClient.generate_text):
        source = inspect.getsource(methode)
        assert "await self.async_client.chat(" in source, f"{methode.__name__} n'utilise pas AsyncClient"
        assert "async for chunk in" in source, f"{methode.__name__} itère le flux de façon bloquante"
        assert "for chunk in stream" not in source.replace("async for chunk in stream", "")


def test_generation_de_document_deportee_en_thread():
    """Le générateur de documents utilise le client synchrone : il doit passer
    par un thread, sinon il bloque la boucle comme le faisait le streaming."""
    import inspect

    from app.services.modules.document_generator import DocumentGeneratorModule

    for methode in (DocumentGeneratorModule.generate_document,
                    DocumentGeneratorModule.generate_section,
                    DocumentGeneratorModule.generate_budget):
        source = inspect.getsource(methode)
        assert "asyncio.to_thread" in source, f"{methode.__name__} appelle le LLM sans thread"


# -------------------------------------------------- schéma et migrations ----

def test_le_demarrage_ne_cree_plus_les_tables():
    """Garde-fou : `create_all` au démarrage créait les tables des nouveaux
    modèles avant Alembic, faisant échouer chaque migration sur « table already
    exists » et laissant le schéma diverger en silence. Le démarrage se contente
    désormais de vérifier."""
    import inspect

    from app.core import database

    assert not hasattr(database, "init_db"), "init_db (create_all) est de retour"
    assert hasattr(database, "check_db_schema")
    # On vise l'appel réel, pas le mot : la docstring explique justement pourquoi
    # `create_all` a été retiré.
    module_source = inspect.getsource(database)
    assert "metadata.create_all" not in module_source
    assert "alembic_version" in inspect.getsource(database.check_db_schema)
