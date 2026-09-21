"""
Tests de la récupération des illustrations d'articles.

Les moteurs et les flux fournissent déjà une vignette pour la plupart des
résultats (mesuré : 23/45 sur SearXNG, ~100 % sur les flux configurés). On les
jetait, ce qui rendait le radar entièrement textuel et interdisait d'envoyer une
trouvaille au moodboard. Aucun téléchargement de page n'est nécessaire.
"""

import feedparser
import pytest

from app.services.modules.web_research import _image_d_entree


def _entree(xml_item: str):
    xml = ('<?xml version="1.0"?><rss version="2.0" '
           'xmlns:media="http://search.yahoo.com/mrss/"><channel><title>T</title>'
           f"{xml_item}</channel></rss>")
    return feedparser.parse(xml).entries[0]


def test_image_depuis_media_content():
    e = _entree('<item><title>A</title>'
                '<media:content url="https://ex.org/photo.jpg" type="image/jpeg"/></item>')
    assert _image_d_entree(e) == "https://ex.org/photo.jpg"


def test_image_depuis_media_thumbnail():
    e = _entree('<item><title>A</title>'
                '<media:thumbnail url="https://ex.org/vignette.png"/></item>')
    assert _image_d_entree(e) == "https://ex.org/vignette.png"


def test_image_depuis_le_resume_html():
    e = _entree('<item><title>A</title><description>'
                '&lt;p&gt;Texte&lt;/p&gt;&lt;img src="https://ex.org/inline.jpg"/&gt;'
                '</description></item>')
    assert _image_d_entree(e) == "https://ex.org/inline.jpg"


def test_pas_d_image():
    assert _image_d_entree(_entree('<item><title>A</title><description>Du texte</description></item>')) is None


def test_image_relative_ignoree():
    """Une source relative serait inaffichable hors du site d'origine."""
    e = _entree('<item><title>A</title><description>'
                '&lt;img src="/local/image.jpg"/&gt;</description></item>')
    assert _image_d_entree(e) is None


def test_media_content_non_image_ignore():
    """Certains flux déclarent des vidéos ou des podcasts en media:content."""
    e = _entree('<item><title>A</title>'
                '<media:content url="https://ex.org/episode.mp3" type="audio/mpeg"/></item>')
    assert _image_d_entree(e) is None


def test_searxng_conserve_la_vignette():
    """Garde-fou : le mapping SearXNG doit propager `img_src`."""
    import inspect

    from app.services import web_search_service as wss

    source = inspect.getsource(wss._searxng_search_sync)
    assert '"image"' in source
    assert "img_src" in source


def test_la_veille_enregistre_l_illustration():
    """Garde-fou : le résultat de veille doit porter l'image jusqu'en base."""
    import inspect

    from app.services.unified_orchestrator import UnifiedOrchestrator

    source = inspect.getsource(UnifiedOrchestrator._handle_veille)
    assert "image_url=result.get('image')" in source
