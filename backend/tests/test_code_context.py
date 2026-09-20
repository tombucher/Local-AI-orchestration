"""
Tests du contexte d'atelier partagé entre les tâches de code d'un projet,
et du nettoyage des fences Markdown dans le code généré.
"""

from types import SimpleNamespace

import pytest

from app.services.code_cleanup import strip_code_fences
from app.services.project_workspace import build_file_plan, infer_artifact_path


def _task(task_id: int, title: str, description: str = "", metadata=None):
    return SimpleNamespace(
        id=task_id,
        title=title,
        description=description,
        llm_prompt=None,
        task_metadata=metadata,
        generated_code=None,
    )


# ---------------------------------------------------------------- fences ----

@pytest.mark.parametrize("raw, expected", [
    ("```html\n<p>ok</p>\n```", "<p>ok</p>"),
    ("```\nbody { color: red; }\n```", "body { color: red; }"),
    ("~~~python\nprint('x')\n~~~", "print('x')"),
    ("```js\nconst a = 1;", "const a = 1;"),                 # fence orpheline
    ("const a = 1;\nconst b = 2;", "const a = 1;\nconst b = 2;"),  # rien à retirer
])
def test_strip_code_fences(raw, expected):
    assert strip_code_fences(raw) == expected


def test_strip_code_fences_garde_le_bloc_dominant():
    raw = "Voici le code :\n\n```css\nbody {\n  margin: 0;\n  padding: 0 1rem;\n}\n```\n"
    assert strip_code_fences(raw) == "body {\n  margin: 0;\n  padding: 0 1rem;\n}"


def test_strip_code_fences_vide():
    assert strip_code_fences(None) == ""
    assert strip_code_fences("") == ""


# ------------------------------------------------------------ plan fichiers --

@pytest.mark.parametrize("title, expected", [
    ("Créer la structure HTML de la page d'accueil", "index.html"),
    ("Styliser l'interface avec CSS", "styles.css"),
    ("Ajouter l'interactivité JavaScript", "app.js"),
    ("Mettre en place un serveur Node.js", "server.js"),
    ("Écrire le README du projet", "README.md"),
])
def test_infer_artifact_path_par_mot_cle(title, expected):
    assert infer_artifact_path(_task(1, title)) == expected


def test_infer_artifact_path_nom_explicite_prioritaire():
    assert infer_artifact_path(_task(1, "Créer le fichier `config.json`")) == "config.json"


def test_infer_artifact_path_metadata_prioritaire():
    task = _task(1, "Styliser avec CSS", metadata={"artifact_path": "assets/main.css"})
    assert infer_artifact_path(task) == "assets/main.css"


def test_infer_artifact_path_tache_transverse():
    """Une tâche d'intégration ne produit pas de fichier propre."""
    assert infer_artifact_path(_task(1, "Intégrer et relier les trois fichiers")) is None


def test_build_file_plan_sans_collision():
    plan = build_file_plan([
        _task(1, "Créer la structure HTML"),
        _task(2, "Styliser avec CSS"),
        _task(3, "Seconde page HTML : contact"),
    ])
    assert plan == {1: "index.html", 2: "styles.css", 3: "index-2.html"}


def test_build_file_plan_est_deterministe():
    tasks = [_task(3, "Ajouter du JavaScript"), _task(1, "Structure HTML"), _task(2, "Styles CSS")]
    assert build_file_plan(tasks) == build_file_plan(list(reversed(tasks)))
