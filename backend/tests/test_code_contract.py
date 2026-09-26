"""
Tests du contrat d'interface entre fichiers, du contrôle de cohérence et de
l'export du projet.

Constat du 26/09/2026 : le HTML était transmis tronqué au CSS et au JS, qui ont
inventé leurs propres noms ; et le résultat ne se récupérait que par copier-coller.
"""

import io
import zipfile
from datetime import datetime, timedelta, timezone

import pytest

from app.services.code_contract import check_coherence, extract_contract, format_contract
from app.services.project_export import safe_path, split_multi_file

HTML = """<!DOCTYPE html><html><head><link rel="stylesheet" href="styles.css"></head>
<body><main class="page">
<div id="ticket" class="ticket"></div>
<button id="imprimer" class="bouton">Imprimer</button>
</main><script src="app.js" defer></script></body></html>"""
CSS = """/* .commentaire-ignore */
:root { --encre: #111; }
.page { color: var(--encre); background: url(fond.png); }
.ticket, .bouton:hover { margin: 0.5rem; }
.ligne { opacity: 1; }"""
JS = """const t = document.getElementById('ticket');
document.querySelector('#imprimer').addEventListener('click', () => {
  const l = document.createElement('p'); l.classList.add('ligne'); t.append(l);
});"""


# -------------------------------------------------------------- contrat --

def test_contrat_html():
    c = extract_contract("index.html", HTML)
    assert c.ids == {"ticket", "imprimer"}
    assert c.classes == {"page", "ticket", "bouton"}
    assert c.button_ids == {"imprimer"}
    assert c.local_refs == {"styles.css", "app.js"}


def test_contrat_css_ignore_valeurs_et_commentaires():
    c = extract_contract("styles.css", CSS)
    assert c.styled_classes == {"page", "ticket", "bouton", "ligne"}
    assert c.css_vars == {"--encre"}
    # ni la couleur #111, ni fond.png, ni 0.5rem, ni le commentaire
    assert not c.styled_ids


def test_contrat_js():
    c = extract_contract("app.js", JS)
    assert c.targeted_ids == {"ticket", "imprimer"}
    assert "ligne" in c.classes


def test_contrat_formate_lisible():
    texte = format_contract("index.html", extract_contract("index.html", HTML))
    assert "`#imprimer`" in texte and "`.bouton`" in texte


# ------------------------------------------------------------ cohérence --

def test_projet_coherent_sans_alerte():
    assert check_coherence({"index.html": HTML, "styles.css": CSS, "app.js": JS}) == []


def test_script_qui_vise_un_element_absent():
    js = "document.getElementById('bouton-imprimer').onclick = null;"
    alertes = check_coherence({"index.html": HTML, "app.js": js})
    assert any("#bouton-imprimer" in a and "absent du HTML" in a for a in alertes)
    # …et les boutons du HTML restent sans effet
    assert any("#imprimer" in a and "sans effet" in a for a in alertes)


def test_element_cree_par_le_script_n_est_pas_absent():
    js = ("const b = document.createElement('button'); b.id = 'nouveau';"
          "document.querySelector('#nouveau'); document.getElementById('imprimer');"
          "document.getElementById('ticket');")
    assert check_coherence({"index.html": HTML, "styles.css": CSS, "app.js": js}) == []


def test_fichier_lie_manquant():
    alertes = check_coherence({"index.html": HTML, "styles.css": CSS})
    assert any("app.js" in a and "n'existe pas" in a for a in alertes)


def test_classes_du_script_non_stylees():
    js = JS + "\nx.classList.add('ligne-a'); x.classList.add('ligne-b'); x.classList.add('ligne-c');"
    alertes = check_coherence({"index.html": HTML, "styles.css": CSS, "app.js": js})
    assert any("ligne-a" in a and "sans style" in a for a in alertes)


def test_sans_html_rien_a_verifier():
    assert check_coherence({"main.py": "print('ok')"}) == []


# ------------------------------------------------------------ contexte --

def test_contrat_transmis_meme_si_le_code_est_tronque():
    """Le cœur du bug : les éléments au-delà de la coupure disparaissaient."""
    import inspect
    from app.services import project_workspace

    source = inspect.getsource(project_workspace.build_workspace_context)
    assert "format_contract" in source
    assert source.index("Contrat d'interface") < source.index("Code déjà produit")
    assert project_workspace.MAX_CHARS_PER_FILE >= 10000


# --------------------------------------------------------------- export --

@pytest.mark.parametrize("brut, attendu", [
    ("index.html", "index.html"),
    ("./css/styles.css", "css/styles.css"),
    ("/abs/app.js", "abs/app.js"),
    ("../../etc/passwd", None),
    ("a/../../b", None),
    ("", None),
])
def test_chemins_assainis(brut, attendu):
    assert safe_path(brut) == attendu


def test_sortie_multi_fichiers():
    sortie = "=== index.html ===\n<p>ok</p>\n=== ../hors.txt ===\nnon\n=== app.js ===\nconsole.log(1)\n"
    assert split_multi_file(sortie) == {"index.html": "<p>ok</p>\n", "app.js": "console.log(1)\n"}
    assert split_multi_file("<p>simple</p>") == {}


@pytest.mark.asyncio
async def test_export_zip_et_fichiers(client, auth_headers, db_session):
    from app.models.task import Task, TaskStatus, TaskType

    projet = (await client.post("/api/v1/projects/", json={
        "name": "Site test", "type": "personal", "features": {"code_gen": True},
    }, headers=auth_headers)).json()["id"]
    db_session.add_all([
        Task(project_id=projet, title="Structure HTML", task_type=TaskType.CODE_GENERATION,
             status=TaskStatus.COMPLETED, generated_code=HTML, task_metadata={"artifact_path": "index.html"}),
        Task(project_id=projet, title="Styles CSS", task_type=TaskType.CODE_GENERATION,
             status=TaskStatus.COMPLETED, generated_code=CSS, task_metadata={"artifact_path": "styles.css"}),
        Task(project_id=projet, title="Note d'intention", task_type=TaskType.DOCUMENT_WRITING,
             status=TaskStatus.COMPLETED, generated_code="Je travaille le papier thermique."),
    ])
    await db_session.flush()

    r = await client.get(f"/api/v1/projects/{projet}/files", headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["entry"] == "index.html"
    assert [f["path"] for f in data["code"]] == ["index.html", "styles.css"]
    assert any("app.js" in a for a in data["coherence"])  # lié mais jamais produit

    r = await client.get(f"/api/v1/projects/{projet}/export", headers=auth_headers)
    assert r.status_code == 200
    noms = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert "site-test/index.html" in noms
    assert "site-test/README.md" in noms
    assert any(n.startswith("site-test/documents/") and "note" in n for n in noms)


@pytest.mark.asyncio
async def test_export_refuse_le_projet_d_un_autre(client, auth_headers):
    r = await client.get("/api/v1/projects/999999/export", headers=auth_headers)
    assert r.status_code == 404


# ------------------------------------------------ financements en amont --

@pytest.mark.asyncio
async def test_appels_a_projets_transmis_et_clos_signales(client, auth_headers, db_session):
    """Le dossier ne recevait que « 7 opportunités trouvées », sans les appels."""
    from sqlalchemy import insert
    from app.models.task import Task, TaskStatus, TaskType, task_dependencies
    from app.models.veille_result import VeilleResult, VeilleResultStatus, VeilleResultType
    from app.models.veille_topic import VeilleScope, VeilleTopic
    from app.services.task_chain import build_upstream_context

    projet = (await client.post("/api/v1/projects/", json={
        "name": "Fin", "type": "personal", "features": {"code_gen": True},
    }, headers=auth_headers)).json()["id"]
    topic = VeilleTopic(project_id=projet, name="Fin", scope=VeilleScope.FUNDING, keywords=[],
                        scan_frequency="once")
    financement = Task(project_id=projet, title="Appels", task_type=TaskType.FUNDING_SEARCH,
                       status=TaskStatus.COMPLETED, generated_code="2 opportunités trouvées.")
    dossier = Task(project_id=projet, title="Dossier", task_type=TaskType.DOCUMENT_WRITING,
                   status=TaskStatus.CREATED)
    db_session.add_all([topic, financement, dossier])
    await db_session.flush()

    maintenant = datetime.now(timezone.utc)
    db_session.add_all([
        VeilleResult(topic_id=topic.id, task_id=financement.id, title="Appel clos",
                     result_type=VeilleResultType.CALL_FOR_PROPOSALS, relevance_score=95,
                     status=VeilleResultStatus.ACTIONABLE, deadline=maintenant - timedelta(days=30)),
        VeilleResult(topic_id=topic.id, task_id=financement.id, title="Appel ouvert",
                     result_type=VeilleResultType.CALL_FOR_PROPOSALS, relevance_score=70,
                     status=VeilleResultStatus.ACTIONABLE, deadline=maintenant + timedelta(days=30)),
    ])
    await db_session.execute(insert(task_dependencies).values(task_id=dossier.id, depends_on_id=financement.id))
    await db_session.flush()

    contexte = await build_upstream_context(db_session, dossier)
    assert "2 opportunités trouvées" in contexte
    assert "Appel ouvert" in contexte and "CLOS le" in contexte
    # l'appel encore ouvert passe devant, malgré un score plus bas
    assert contexte.index("Appel ouvert") < contexte.index("Appel clos")


@pytest.mark.asyncio
async def test_documents_toujours_accessibles(client, auth_headers):
    """Un utilitaire homonyme ajouté en fin de module avait écrasé celui des documents."""
    projet = (await client.post("/api/v1/projects/", json={
        "name": "Docs", "type": "personal", "features": {"code_gen": True},
    }, headers=auth_headers)).json()["id"]
    r = await client.get(f"/api/v1/projects/{projet}/documents", headers=auth_headers)
    assert r.status_code == 200, r.text


def test_aucune_fonction_definie_deux_fois_dans_l_api():
    import ast
    import pathlib

    for module in pathlib.Path("app/api/v1").glob("*.py"):
        noms = [n.name for n in ast.parse(module.read_text()).body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        doublons = {n for n in noms if noms.count(n) > 1}
        assert not doublons, f"{module.name} : {doublons}"
