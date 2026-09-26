"""
L'orchestrateur est strictement local : aucun projet ne doit partir vers un
modèle cloud, même si Ollama en propose et même si on en choisit un.

Constat du 27/09/2026 : `gpt-oss:120b-cloud` (suffixe en tiret) échappait au
filtre `":cloud"` du repli, et les modèles cloud figuraient dans la liste des
Paramètres.
"""

import pytest

from app.services import model_registry as registry

OLLAMA_LIST = {"models": [
    {"model": "qwen3.8:27b-mlx", "size": 18_000_000_000},
    {"model": "gemma4:12b-mlx", "size": 7_700_000_000},
    {"model": "deepseek-v4-flash:cloud", "size": 348, "remote_host": "https://ollama.com:443"},
    {"model": "gpt-oss:120b-cloud", "size": 384, "remote_host": "https://ollama.com:443"},
    {"model": "modele-distant:latest", "size": 300, "remote_host": "https://ollama.com:443"},
    {"model": "nomic-embed-text:latest", "size": 274_000_000},
]}


class FauxClient:
    def list(self):
        return OLLAMA_LIST


@pytest.fixture(autouse=True)
def ollama_simule(monkeypatch):
    monkeypatch.setattr(registry, "_client", lambda: FauxClient())
    registry._list_cache.update(ts=0.0, models=[])
    registry._cloud_names.clear()
    registry._warned_missing.clear()
    monkeypatch.setattr(registry.settings, "OLLAMA_MODEL_CODE", "qwen3.8:27b-mlx")


def test_modeles_cloud_absents_de_la_liste():
    noms = registry.list_local_models(force=True)
    assert noms == ["qwen3.8:27b-mlx", "gemma4:12b-mlx", "nomic-embed-text:latest"]


@pytest.mark.parametrize("nom", [
    "deepseek-v4-flash:cloud",
    "gpt-oss:120b-cloud",       # suffixe en tiret : échappait au filtre
    "modele-distant:latest",    # rien dans le nom, seul remote_host le trahit
])
def test_modele_cloud_refuse_meme_choisi(nom):
    registry.list_local_models(force=True)
    choisi = registry.resolve_model(nom, "test")
    assert choisi == "qwen3.8:27b-mlx"
    assert not registry.is_cloud_model(choisi)


def test_nom_de_base_ne_rattrape_pas_un_modele_cloud():
    """'gpt-oss' ne doit pas correspondre à 'gpt-oss:120b-cloud'."""
    assert registry.resolve_model("gpt-oss", "test") == "qwen3.8:27b-mlx"


def test_modele_local_inchange():
    assert registry.resolve_model("gemma4:12b-mlx") == "gemma4:12b-mlx"


def test_detection_par_le_tag():
    assert registry.looks_like_cloud("x:cloud")
    assert registry.looks_like_cloud("x:120b-cloud")
    assert not registry.looks_like_cloud("cloudy-model:7b")  # le nom, pas le tag
    assert not registry.looks_like_cloud(None)
