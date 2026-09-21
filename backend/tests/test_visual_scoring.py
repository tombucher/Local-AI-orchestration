"""
Tests de la notation des références visuelles par le modèle vision.

Contexte : la notation lexicale ne pouvait pas fonctionner — les sources nomment
leurs images « IMG_8531.JPG », et une image intitulée « Brutalist Design » s'est
révélée être un tracteur rouillé.
"""

import pytest

from app.services.visual_scoring import _parse, titre_illisible


# ------------------------------------------------- lecture de la réponse ----

def test_parse_format_attendu():
    r = _parse("Art ASCII en noir et blanc | 95")
    assert r == {"score": 95.0, "description": "Art ASCII en noir et blanc"}


def test_parse_note_seule():
    """Le modèle oublie parfois la description : la note reste exploitable."""
    r = _parse("85")
    assert r["score"] == 85.0
    assert r["description"] == ""


def test_parse_note_plafonnee():
    assert _parse("bidule | 250")["score"] == 100.0
    assert _parse("bidule | 0")["score"] == 0.0


def test_parse_prend_la_derniere_note():
    """« 0-20 = aucun rapport … | 15 » ne doit pas être lu comme 0."""
    assert _parse("Schéma noir et blanc | 15")["score"] == 15.0


@pytest.mark.parametrize("reponse", ["", "   ", "aucune idée", None])
def test_parse_reponses_inexploitables(reponse):
    assert _parse(reponse) is None


def test_parse_tronque_les_descriptions_bavardes():
    r = _parse("x" * 300 + " | 50")
    assert len(r["description"]) <= 120


# ------------------------------------------------------ titres illisibles ---

@pytest.mark.parametrize("titre", [
    "IMG_8531.JPG", "movieposter.jpg", "978ab07c673d90c07f9baacc17dd57da.jpg",
    "image.png", "friends.gif", "https://flic.kr/p/92f7Ds", "", "   ",
])
def test_titres_a_remplacer(titre):
    assert titre_illisible(titre)


@pytest.mark.parametrize("titre", [
    "Kanji Ascii Art", "Vintage Olivetti Underwood Model 340",
    "Brutalist Design", "handmade paper texture",
])
def test_titres_lisibles_conserves(titre):
    assert not titre_illisible(titre)


# ---------------------------------------------------------- garde-fous ------

def test_consigne_calibree():
    """Sans échelle explicite ni consigne de sévérité, le modèle note tout
    entre 85 et 95 et ne discrimine plus rien (mesuré le 21/09/2026)."""
    from app.services.visual_scoring import GABARIT_PROMPT

    assert "Sois sévère" in GABARIT_PROMPT
    for palier in ("0-20", "30-50", "60-80", "90-100"):
        assert palier in GABARIT_PROMPT


@pytest.mark.asyncio
async def test_sans_vision_les_scores_lexicaux_sont_conserves(monkeypatch):
    from app.services import visual_scoring as vs

    monkeypatch.setattr(vs, "resolve_model", lambda m, p="": "modele-sans-vision")
    monkeypatch.setattr(vs, "supports_vision", lambda m: False)

    images = [{"title": "a", "relevance_score": 42.0, "thumbnail_url": "http://x/y.png"}]
    resultat = await vs.score_images_with_vision(images, "quelque chose")
    assert resultat[0]["relevance_score"] == 42.0


@pytest.mark.asyncio
async def test_liste_vide():
    from app.services.visual_scoring import score_images_with_vision

    assert await score_images_with_vision([], "peu importe") == []
