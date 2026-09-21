"""
Tests de l'ajout manuel d'images au moodboard.

Une veille visuelle alimente le moodboard toute seule ; rien ne permettait en
revanche d'y déposer une trouvaille faite ailleurs.
"""

import pytest
from pydantic import ValidationError

from app.schemas.project_document import VisualReferenceCreate


# ------------------------------------------------------- validation d'URL --

@pytest.mark.parametrize("url", [
    "https://exemple.org/image.jpg",
    "http://exemple.org/image.png",
    "  https://exemple.org/avec-espaces.jpg  ",
])
def test_urls_acceptees(url):
    assert VisualReferenceCreate(url=url).url.startswith(("http://", "https://"))


@pytest.mark.parametrize("url", [
    "javascript:alert(1)",
    "data:image/png;base64,AAAA",
    "file:///etc/passwd",
    "exemple.org/image.jpg",
])
def test_urls_refusees(url):
    """Seul le http(s) est accepté : pas de javascript:, data: ni file:."""
    with pytest.raises(ValidationError):
        VisualReferenceCreate(url=url)


def test_champs_facultatifs():
    ref = VisualReferenceCreate(url="https://exemple.org/i.jpg")
    assert ref.title is None and ref.note is None and ref.source_url is None


def test_page_source_distincte_de_l_image():
    ref = VisualReferenceCreate(
        url="https://cdn.exemple.org/i.jpg",
        source_url="https://exemple.org/article",
    )
    assert ref.source_url == "https://exemple.org/article"


def test_source_url_aussi_validee():
    with pytest.raises(ValidationError):
        VisualReferenceCreate(url="https://ok.org/i.jpg", source_url="javascript:void(0)")


# ------------------------------------------------------------- cloisonnement --

def test_sujet_dedie_aux_ajouts_manuels():
    """Les ajouts manuels vont dans leur propre sujet, pour ne pas se mêler aux
    résultats d'une veille ni être écrasés par un nouveau scan."""
    from app.api.v1.projects import MANUAL_TOPIC_NAME

    assert MANUAL_TOPIC_NAME == "Ajouts manuels"
