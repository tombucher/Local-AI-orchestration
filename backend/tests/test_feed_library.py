"""
Tests de la bibliothèque de flux : déduction des thèmes, vérification d'un flux,
et priorité de la bibliothèque personnelle sur le catalogue intégré.
"""

import feedparser
import pytest

from app.services.feed_library import derive_tags, inspect_feed
from app.services.modules.web_research import WebResearchModule


def _feed(title: str, subtitle: str, entries: list, categories=None) -> object:
    """Construit un flux RSS minimal et le parse, pour tester sans réseau."""
    items = "".join(
        f"<item><title>{t}</title><description>{d}</description>"
        + "".join(f"<category>{c}</category>" for c in (categories or []))
        + "</item>"
        for t, d in entries
    )
    xml = (
        '<?xml version="1.0"?><rss version="2.0"><channel>'
        f"<title>{title}</title><description>{subtitle}</description>{items}"
        "</channel></rss>"
    )
    return feedparser.parse(xml)


# ------------------------------------------------------------- thèmes ----

def test_derive_tags_utilise_le_titre_du_flux():
    parsed = _feed("Reporterre, le média de l'écologie", "", [("Un article", "Du texte")])
    tags = derive_tags(parsed)
    # L'apostrophe ne doit pas coller l'article au mot : « écologie », pas « l'écologie »
    assert "écologie" in tags
    assert "reporterre" in tags


def test_derive_tags_ignore_les_mots_vus_une_seule_fois():
    """Un nom propre croisé dans un seul article n'est pas un thème du flux."""
    parsed = _feed(
        "Journal", "",
        [("Jules Ferry inaugure", "texte"), ("Pesticides interdits", "pesticides partout"),
         ("Les pesticides encore", "pesticides et agriculture")],
    )
    tags = derive_tags(parsed)
    assert "pesticides" in tags      # présent dans deux entrées
    assert "ferry" not in tags       # une seule entrée


def test_derive_tags_exploite_les_categories_declarees():
    parsed = _feed("Mag", "", [("A", "x"), ("B", "y")], categories=["graphic design"])
    assert "graphic design" in derive_tags(parsed)


def test_derive_tags_ecarte_les_mois_et_mots_passe_partout():
    parsed = _feed(
        "Actus", "",
        [("Septembre : people like this", "become member"),
         ("Septembre encore : people like that", "become member")],
    )
    tags = derive_tags(parsed)
    for noise in ("septembre", "like", "people", "become", "member"):
        assert noise not in tags


# -------------------------------------------------------- vérification ----

@pytest.mark.asyncio
async def test_inspect_feed_refuse_les_urls_internes():
    """Anti-SSRF : le backend ne doit jamais requêter Postgres ou Ollama."""
    result = await inspect_feed("http://postgres:5432/feed")
    assert result["ok"] is False
    assert "refus" in result["status"].casefold()


@pytest.mark.asyncio
async def test_inspect_feed_refuse_les_schemas_non_http():
    result = await inspect_feed("file:///etc/passwd")
    assert result["ok"] is False


# ------------------------------------------- priorité de la bibliothèque ----

def test_flux_personnels_prioritaires_a_correspondance_egale():
    perso = [{"url": "https://perso.example/rss", "tags": ["typographie", "affiche"]}]
    urls = WebResearchModule.select_feeds(["typographie"], scope="news", user_feeds=perso)
    assert urls[0] == "https://perso.example/rss"


def test_flux_personnels_hors_sujet_non_imposes():
    """Un flux climat ne doit pas polluer une veille typographie."""
    perso = [{"url": "https://climat.example/rss", "tags": ["climat", "carbone"]}]
    urls = WebResearchModule.select_feeds(["typographie", "graphisme"], scope="news", user_feeds=perso)
    assert "https://climat.example/rss" not in urls


def test_sans_correspondance_la_bibliotheque_prime_sur_le_catalogue():
    perso = [{"url": "https://perso.example/rss", "tags": ["photographie"]}]
    urls = WebResearchModule.select_feeds(["sujetinconnuxyz"], scope="news", user_feeds=perso)
    assert urls == ["https://perso.example/rss"]


def test_pas_de_doublon_entre_bibliotheque_et_catalogue():
    perso = [{"url": "https://www.dezeen.com/feed/", "tags": ["design"]}]
    urls = WebResearchModule.select_feeds(["design"], scope="cultural", user_feeds=perso)
    assert len(urls) == len(set(urls))
