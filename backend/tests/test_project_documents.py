"""
Tests de l'espace documents : sélection sous budget, formatage du code,
et traitement des images selon la capacité vision du modèle.
"""

import base64

import pytest

from app.models.project_document import DocumentKind
from app.services.project_documents import (
    MAX_CHARS_PER_DOCUMENT, DocumentContext, _language_for, _relevance,
    summarise_for_memory,
)


class FauxDocument:
    """Document minimal, sans base de données."""

    def __init__(self, name, kind=DocumentKind.TEXT, content=None, binary=None, note=None):
        self.name = name
        self.kind = kind
        self.content = content
        self.binary = binary
        self.note = note

    @property
    def is_image(self):
        return self.kind == DocumentKind.IMAGE


# ------------------------------------------------------------ pertinence --

def test_relevance_recoupe_nom_et_note():
    from app.services.project_documents import _significant

    besoin = _significant("Créer la page d'accueil selon la charte graphique")
    charte = FauxDocument("charte-graphique.md", note="Règles de la charte")
    autre = FauxDocument("budget-2027.csv", note="Prévisionnel comptable")
    assert _relevance(charte, besoin) > _relevance(autre, besoin)


def test_relevance_nulle_sans_objectif():
    assert _relevance(FauxDocument("a.md"), set()) == 0.0


# ------------------------------------------------------------- langages --

@pytest.mark.parametrize("nom, attendu", [
    ("app.py", "python"), ("main.ts", "typescript"), ("index.html", "html"),
    ("styles.css", "css"), ("notes.md", "markdown"), ("sans-extension", ""),
])
def test_langage_deduit_de_l_extension(nom, attendu):
    assert _language_for(nom) == attendu


# ---------------------------------------------------------------- résumé --

def test_resume_pour_le_carnet():
    docs = [FauxDocument("charte.md", note="Règles visuelles"), FauxDocument("api.py")]
    resume = summarise_for_memory(docs)
    assert "charte.md (Règles visuelles)" in resume
    assert "api.py" in resume


def test_resume_vide_sans_documents():
    assert summarise_for_memory([]) == ""


# -------------------------------------------------------------- contexte --

def test_contexte_vide_est_falsy():
    assert not DocumentContext()
    assert DocumentContext(text="quelque chose")


@pytest.mark.asyncio
async def test_budget_respecte_et_documents_excedentaires_cites(monkeypatch):
    """Au-delà du budget, un document doit être cité, pas injecté en entier."""
    from app.services import project_documents as pd

    gros = [FauxDocument(f"doc-{i}.md", content="x" * 5000) for i in range(6)]
    monkeypatch.setattr(pd, "load_documents", lambda db, pid: _async(gros))

    ctx = await pd.build_document_context(None, 1, objective="", max_chars=9000)
    assert ctx.used, "aucun document injecté"
    assert ctx.mentioned, "les documents hors budget doivent être cités"
    assert len(ctx.text) < 9000 + 2000  # budget + en-têtes


@pytest.mark.asyncio
async def test_document_trop_long_est_tronque(monkeypatch):
    from app.services import project_documents as pd

    enorme = [FauxDocument("enorme.md", content="y" * (MAX_CHARS_PER_DOCUMENT * 3))]
    monkeypatch.setattr(pd, "load_documents", lambda db, pid: _async(enorme))

    ctx = await pd.build_document_context(None, 1)
    assert "(document tronqué)" in ctx.text


@pytest.mark.asyncio
async def test_le_code_est_encadre_avec_son_langage(monkeypatch):
    from app.services import project_documents as pd

    docs = [FauxDocument("app.py", kind=DocumentKind.CODE, content="print('bonjour')")]
    monkeypatch.setattr(pd, "load_documents", lambda db, pid: _async(docs))

    ctx = await pd.build_document_context(None, 1)
    assert "```python" in ctx.text


@pytest.mark.asyncio
async def test_images_transmises_seulement_avec_vision(monkeypatch):
    from app.services import project_documents as pd

    docs = [FauxDocument("ref.png", kind=DocumentKind.IMAGE, binary=b"\x89PNG-faux")]
    monkeypatch.setattr(pd, "load_documents", lambda db, pid: _async(docs))

    avec = await pd.build_document_context(None, 1, include_images=True)
    assert len(avec.images) == 1
    assert base64.b64decode(avec.images[0]) == b"\x89PNG-faux"

    sans = await pd.build_document_context(None, 1, include_images=False)
    assert sans.images == []
    # Le modèle doit au moins savoir que l'image existe
    assert "ref.png" in sans.mentioned


@pytest.mark.asyncio
async def test_nombre_d_images_plafonne(monkeypatch):
    """Chaque image coûte beaucoup de tokens à un modèle local."""
    from app.services import project_documents as pd

    docs = [FauxDocument(f"i{i}.png", kind=DocumentKind.IMAGE, binary=b"x") for i in range(10)]
    monkeypatch.setattr(pd, "load_documents", lambda db, pid: _async(docs))

    ctx = await pd.build_document_context(None, 1, include_images=True)
    assert len(ctx.images) == pd.MAX_IMAGES


async def _async(valeur):
    return valeur
