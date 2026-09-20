"""
Tests de la mémoire de projet et de la notation de pertinence des références visuelles.

Calibration vérifiée sur les cas réels qui avaient produit un moodboard aberrant
(avions de ligne et peintures religieuses sur une veille « glitch » / « haïku »).
"""

import pytest

from app.services.project_memory import ProjectMemory, score_against_memory
from app.services.unified_orchestrator import _merge_queries, _query_terms


# ------------------------------------------------------- termes de requête --

def test_query_terms_groupe_par_requete():
    assert _query_terms(["Minimalist typography", "Haiku poster"]) == [
        ["minimalist", "typography"], ["haiku", "poster"]
    ]


def test_query_terms_ecarte_les_mots_generiques():
    """« art » ou « digital » reviennent partout : ils ne prouvent aucune pertinence."""
    assert _query_terms(["Glitch art"]) == [["glitch"]]
    assert _query_terms(["digital art"]) == []


def test_merge_queries_priorise_et_dedoublonne():
    merged = _merge_queries(["haiku poster"], ["Haiku Poster", "glitch"], limit=4)
    assert merged == ["haiku poster", "glitch"]


# ------------------------------------------------------------- notation ----

@pytest.fixture
def memory():
    return ProjectMemory(brief="", vocabulary=["typographie", "haiku", "affiche"])


@pytest.fixture
def queries():
    return _query_terms(["Minimalist typography", "Generative light", "Haiku poster"])


@pytest.mark.parametrize("title", [
    "Haiku Poster — 2",                 # couvre entièrement une requête
    "Haiku: Posters",
    "Minimalist typography study",
    "Typography Poster",                # croise deux requêtes différentes
])
def test_resultats_pertinents_conserves(title, memory, queries):
    assert score_against_memory({"title": title}, memory, queries) >= 60


@pytest.mark.parametrize("title", [
    "Generation Light",                                       # un seul mot commun
    "45 Commando operate NLAW (Next Generation Light Anti-Tank Weapon)",
    "Renault 5 first generation light blue",
    "The Birth of the Virgin",                                # repli des APIs musée
    "Bowl with Textured Surface Decoration",
    "KLM Cargo 747-406(ER)F PH-CKD",
])
def test_resultats_hors_sujet_ecartes(title, memory, queries):
    assert score_against_memory({"title": title}, memory, queries) < 60


def test_mot_entier_uniquement(memory, queries):
    """« light » ne doit pas matcher « delightful »."""
    assert score_against_memory({"title": "A delightful afternoon"}, memory, queries) == 0.0


def test_malus_sur_resultat_deja_ecarte(memory, queries):
    memory.disliked = ["Haiku Poster — 2"]
    assert score_against_memory({"title": "Haiku Poster — 2"}, memory, queries) < 60


def test_sans_contexte_score_neutre():
    vide = ProjectMemory(brief="", vocabulary=[])
    assert score_against_memory({"title": "n'importe quoi"}, vide, []) == 50.0


def test_memoire_pauvre_detectee():
    assert ProjectMemory(brief="", vocabulary=["a", "b"]).is_thin()
    assert not ProjectMemory(brief="", vocabulary=["a", "b", "c"]).is_thin()


def test_extend_vocabulary_fait_le_pont_fr_en():
    memory = ProjectMemory(brief="", vocabulary=["typographie"])
    memory.extend_vocabulary("haiku poster design")
    assert "haiku" in memory.vocabulary and "typographie" in memory.vocabulary


# ------------------------------------------------- sources documentaires ----

def test_flux_par_defaut_par_scope():
    """Chaque scope textuel a des flux, et ce sont bien des URLs."""
    from app.services.modules.web_research import WebResearchModule

    feeds = WebResearchModule.DEFAULT_ARTICLE_FEEDS
    assert set(feeds) >= {"tech", "cultural", "news", "academic"}
    for scope, urls in feeds.items():
        assert urls, f"aucun flux pour le scope {scope}"
        assert all(u.startswith("https://") or u.startswith("http://") for u in urls)


def test_flux_images_sans_source_morte():
    """CreativeApplications ne sert plus qu'une entrée « RSS Feed Inactive »."""
    from app.services.modules.web_research import WebResearchModule

    assert not any("creativeapplications" in u for u in WebResearchModule.DEFAULT_DESIGN_FEEDS)
    assert WebResearchModule.DEFAULT_DESIGN_FEEDS


def test_openverse_plafonne_a_20():
    """Au-delà, l'API répond 401 « page_size may not exceed 20 for anonymous requests »."""
    from app.services.modules.web_research import WebResearchModule

    assert WebResearchModule.OPENVERSE_ANON_MAX == 20


def test_select_feeds_suit_le_sujet_pas_la_categorie():
    """Un sujet typographie classé « news » doit recevoir des flux design, pas du climat."""
    from app.services.modules.web_research import WebResearchModule as W

    typo = W.select_feeds(["typographie", "graphisme", "poster"], scope="news")
    assert any("creativebloq" in u for u in typo)
    assert not any("carbonbrief" in u or "mongabay" in u for u in typo)

    climat = W.select_feeds(["climat", "biodiversité", "carbone"], scope="news")
    assert any("carbonbrief" in u for u in climat)
    assert not any("creativebloq" in u for u in climat)


def test_select_feeds_complete_quand_trop_peu_de_sources():
    """Moins de 3 flux = récolte quasi nulle : on complète avec les généralistes."""
    from app.services.modules.web_research import WebResearchModule as W

    assert len(W.select_feeds(["typographie"], scope="news")) >= 3


def test_select_feeds_repli_sans_correspondance():
    from app.services.modules.web_research import WebResearchModule as W

    assert W.select_feeds(["zzzz", "yyyy"], scope="cultural") == W.DEFAULT_ARTICLE_FEEDS["cultural"]


def test_catalogue_sans_flux_mort():
    """Prosthetic Knowledge est un blog retiré, CreativeApplications un flux inactif."""
    from app.services.modules.web_research import WebResearchModule as W

    urls = [f["url"] for f in W.FEED_CATALOGUE]
    assert not any("prostheticknowledge" in u or "creativeapplications" in u for u in urls)
    # URLs corrigées : les anciennes renvoyaient 404
    assert "https://e360.yale.edu/feed.xml" in urls
    assert "https://theecologist.org/rss" in urls


# ------------------------------------------------------ backend recherche --

def test_searxng_prioritaire_sur_brave():
    """SearXNG passe avant Brave et DuckDuckGo quand il est configuré."""
    from app.services.web_search_service import WebSearchService

    svc = WebSearchService(brave_api_key="factice")
    svc._searxng_url = "http://searxng:8080"
    assert svc._searxng_url and svc._brave_key  # les deux présents…
    # …et c'est bien SearXNG qui est interrogé en premier dans search_text
    import inspect
    source = inspect.getsource(WebSearchService.search_text)
    assert source.index("_searxng_url") < source.index("_brave_key")


def test_searxng_403_renvoie_une_liste_vide(monkeypatch, caplog):
    """Si `json` n'est pas dans search.formats, l'instance répond 403.

    On ne doit ni lever, ni retourner des résultats bidons : liste vide + message
    d'erreur explicite, pour que le repli sur Brave/DDG prenne la main.
    """
    import logging
    import httpx
    from app.services import web_search_service as wss

    class _Resp:
        status_code = 403
        def raise_for_status(self): raise AssertionError("ne doit pas être appelé")
        def json(self): raise AssertionError("ne doit pas être appelé")

    class _Client:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, *a, **k): return _Resp()

    monkeypatch.setattr(httpx, "Client", _Client)
    with caplog.at_level(logging.ERROR):
        assert wss._searxng_search_sync("test", 5, "http://searxng:8080") == []
    assert "formats" in caplog.text


def test_searxng_instance_injoignable(monkeypatch):
    """Instance éteinte : on log et on renvoie vide, sans casser la veille."""
    import httpx
    from app.services import web_search_service as wss

    class _Client:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, *a, **k): raise httpx.ConnectError("connexion refusée")

    monkeypatch.setattr(httpx, "Client", _Client)
    assert wss._searxng_search_sync("test", 5, "http://searxng:8080") == []
