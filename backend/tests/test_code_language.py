"""
Tests de la reconnaissance du langage d'un fichier par son contenu.

Constat du 28/09/2026 : un module Python rangé sous index.html s'affichait comme
page web dans l'aperçu du site.
"""

import pytest

from app.services.code_language import detect_language, effective_path, file_slug

PYTHON = '#!/usr/bin/env python3\n"""Moteur ASCII."""\nimport re\n\ndef convertir(t):\n    return t\n'
HTML = '<!DOCTYPE html>\n<html lang="fr"><head></head><body><main></main></body></html>'
CSS = ':root { --encre: #111; }\n.ticket { margin: 0; }\n.ligne:hover { color: red; }'
JS = "const t = document.getElementById('x');\nfunction imprimer() { t.textContent = 'ok'; }"


@pytest.mark.parametrize("code, attendu", [
    (PYTHON, "py"), (HTML, "html"), (CSS, "css"), (JS, "js"),
    ('{"a": 1}', "json"), ("# Titre\n\nDu texte.", "md"), ("<?php echo 1;", "php"),
    ("#!/bin/bash\necho ok", "sh"), ("", None), ("juste du texte", None),
])
def test_detection(code, attendu):
    assert detect_language(code) == attendu


def test_python_qui_parle_de_html_reste_du_python():
    """Le cas réel : un module qui manipule du HTML dans ses chaînes."""
    code = PYTHON + '\ndef extraire(html):\n    return html.replace("<div>", "")\n'
    assert detect_language(code) == "py"


def test_chemin_corrige_seulement_si_le_contenu_contredit():
    assert effective_path("index.html", PYTHON, "moteur-ascii") == "moteur-ascii.py"
    assert effective_path("index.html", HTML, "x") == "index.html"
    assert effective_path("site/page.htm", HTML, "x") == "site/page.htm"
    assert effective_path("app.js", "juste du texte", "x") == "app.js"   # incertain : on garde
    assert effective_path("assets/main.css", JS, "script") == "assets/script.js"


def test_nom_coupe_entre_deux_mots():
    assert file_slug("Conception du moteur de transformation ASCII") == "conception-du-moteur-de-transformation-ascii"
    assert file_slug("Intégration du système d'alertes visuelles") == "integration-du-systeme-d-alertes-visuelles"
    long = file_slug("Un titre vraiment très long qui dépasse largement la limite fixée pour un nom")
    assert len(long) <= 48 and not long.endswith("-") and long.split("-")[-1] in "un titre vraiment tres long qui depasse largement la limite fixee pour un nom".split()


@pytest.mark.asyncio
async def test_projet_python_sans_apercu_de_site(client, auth_headers, db_session):
    from app.models.task import Task, TaskStatus, TaskType

    pid = (await client.post("/api/v1/projects/", json={
        "name": "Imprimante", "type": "personal", "features": {"code_gen": True},
    }, headers=auth_headers)).json()["id"]
    db_session.add(Task(project_id=pid, title="Conception du moteur de transformation ASCII",
                        task_type=TaskType.CODE_GENERATION, status=TaskStatus.COMPLETED,
                        generated_code=PYTHON, task_metadata={"artifact_path": "index.html"}))
    await db_session.commit()

    data = (await client.get(f"/api/v1/projects/{pid}/files", headers=auth_headers)).json()
    assert data["entry"] is None                        # plus d'aperçu de Python
    assert data["code"][0]["path"] == "conception-du-moteur-de-transformation-ascii.py"
    assert data["code"][0]["language"] == "py"
    assert any("Python" in a and "index.html" in a for a in data["coherence"])
