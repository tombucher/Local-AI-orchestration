"""
Une page (visuel génératif, maquette, prototype) s'écrit en trois fichiers.

Cas du 18/11/2026 : « Moteur génératif » rendait une seule page de 32 000
caractères, styles et script compris : illisible à la revue, au bord de la
limite de sortie du modèle, et sans aperçu à l'écran de validation. Désormais
HTML, CSS et JS sont écrits un par un, l'aperçu les assemble, et « Ajuster »
peut ne réécrire qu'un des trois.
"""

import pytest
from sqlalchemy import select

from app.models.task import Task, TaskStatus, TaskType
from app.services.code_cleanup import extraire_en_ligne, join_multi_file, split_multi_file, strip_code_fences
from app.services.project_workspace import bundle_paths, bundle_step_context
from app.services.unified_orchestrator import UnifiedOrchestrator

HTML = """<!DOCTYPE html>
<html><head><title>Moteur</title>
<link rel="stylesheet" href="moteur.css">
<script src="https://cdn.jsdelivr.net/npm/p5@1.9.0/lib/p5.min.js"></script>
</head><body><canvas id="toile"></canvas><button id="exporter">Exporter</button>
<script src="moteur.js" defer></script></body></html>"""
CSS = ":root { --encre: #1d1a17; }\n#toile { display: block; }\n#exporter { color: var(--encre); }"
JS = "document.getElementById('exporter').addEventListener('click', () => saveCanvas('affiche', 'png'));"


def test_trois_fichiers_seulement_pour_une_page_que_personne_d_autre_ne_stylise():
    assert bundle_paths("moteur.html", {1: "moteur.html", 2: "mockups.html"}, 1) == \
        ["moteur.html", "moteur.css", "moteur.js"]
    # Projet déjà découpé en tâches HTML / CSS / JS : chacune garde son fichier
    assert bundle_paths("index.html", {1: "index.html", 2: "styles.css", 3: "app.js"}, 1) == []
    assert bundle_paths("app.js", {1: "app.js"}, 1) == []
    assert bundle_paths(None, {}, 1) == []


def test_les_balises_sont_retirees_fichier_par_fichier():
    sortie = "Voici les fichiers :\n=== moteur.html ===\n```html\n" + HTML + "\n```\n" \
             "=== moteur.css ===\n```css\n" + CSS + "\n```\n=== moteur.js ===\n```javascript\n" + JS + "\n```"
    fichiers = split_multi_file(strip_code_fences(sortie))
    assert list(fichiers) == ["moteur.html", "moteur.css", "moteur.js"]
    assert fichiers["moteur.css"].strip() == CSS and "```" not in "".join(fichiers.values())
    assert split_multi_file(join_multi_file(fichiers)) == fichiers


def test_styles_et_script_ecrits_dans_la_page_sont_sortis_vers_leurs_fichiers():
    page = """<html><head><style>body { margin: 0; }</style>
<script src="https://cdn.jsdelivr.net/npm/p5@1.9.0/lib/p5.min.js"></script></head>
<body><script type="application/json" id="donnees">{"a": 1}</script>
<script>function setup() { createCanvas(400, 400); }</script></body></html>"""
    html, css, js = extraire_en_ligne(page, "m.css", "m.js")
    assert css == "body { margin: 0; }" and "createCanvas" in js
    assert "<style" not in html and "createCanvas" not in html
    assert "p5.min.js" in html and 'id="donnees"' in html     # CDN et données restent
    assert '<link rel="stylesheet" href="m.css">' in html and '<script src="m.js" defer></script>' in html
    # Rien à sortir : la page ne bouge pas
    assert extraire_en_ligne(HTML, "moteur.css", "moteur.js") == (HTML, "", "")


def test_chaque_etape_voit_les_fichiers_deja_ecrits():
    bundle = ["moteur.html", "moteur.css", "moteur.js"]
    ctx = bundle_step_context("PLAN", bundle, "moteur.css", {"moteur.html": HTML})
    assert "écris `moteur.css`, et lui seul" in ctx and 'id="exporter"' in ctx
    ctx = bundle_step_context("PLAN", bundle, "moteur.css", {"moteur.html": HTML, "moteur.css": CSS},
                              ajustement=True)
    assert "version actuelle, à corriger" in ctx and "--encre" in ctx


class FauxModele:
    def __init__(self, reponses):
        self.reponses, self.contextes = list(reponses), []

    async def generate_code(self, task, model_override=None, workspace_context=None,
                            document_context=None, images=None, **_):
        self.contextes.append(workspace_context)
        return self.reponses.pop(0)


async def _tache(db_session, client, auth_headers):
    r = await client.post("/api/v1/projects/", json={"name": "Festival", "type": "professional"},
                          headers=auth_headers)
    tache = Task(project_id=r.json()["id"], title="Moteur génératif", task_type=TaskType.CODE_GENERATION,
                 status=TaskStatus.GENERATING, task_metadata={"artifact_path": "moteur.html"})
    db_session.add(tache)
    await db_session.commit()
    return tache


@pytest.mark.asyncio
async def test_page_generee_en_trois_appels_puis_un_seul_fichier_corrige(client, auth_headers, db_session):
    tache = await _tache(db_session, client, auth_headers)
    bundle = ["moteur.html", "moteur.css", "moteur.js"]
    orch = UnifiedOrchestrator(db_session)
    orch.llm_client = FauxModele([HTML, CSS, JS])
    await orch._generer_page(tache, "modele", "PLAN", bundle, "", None)

    assert len(orch.llm_client.contextes) == 3
    assert 'id="exporter"' in orch.llm_client.contextes[2]          # le JS a vu le HTML
    assert "--encre" in orch.llm_client.contextes[2]                # et les noms du CSS…
    assert "display: block" not in orch.llm_client.contextes[2]     # …pas la feuille entière
    assert split_multi_file(tache.generated_code) == {p: c + "\n" for p, c in zip(bundle, (HTML, CSS, JS))}
    assert tache.task_metadata["artifact_files"] == bundle
    await db_session.commit()

    # L'aperçu : la page de la tâche, ses trois fichiers en premier
    r = await client.get(f"/api/v1/tasks/{tache.id}/apercu", headers=auth_headers)
    assert r.status_code == 200
    apercu = r.json()
    assert apercu["entry"] == "moteur.html"
    assert [f["path"] for f in apercu["files"] if f["mine"]] == bundle

    # « Ajuster » le CSS seulement : le code reste, la cible est notée
    tache.status = TaskStatus.MANUAL_REVIEW
    await db_session.commit()
    r = await client.post(f"/api/v1/tasks/{tache.id}/reject",
                          json={"approved": False, "notes": "Couleurs plus vives", "fichier": "moteur.css"},
                          headers=auth_headers)
    assert r.status_code == 200
    tache_id = tache.id
    db_session.expire_all()
    tache = (await db_session.execute(select(Task).where(Task.id == tache_id))).unique().scalar_one()
    assert tache.generated_code and tache.task_metadata["fichier_a_ajuster"] == "moteur.css"

    # La génération suivante ne réécrit que le CSS
    orch = UnifiedOrchestrator(db_session)
    orch.llm_client = FauxModele([":root { --encre: #ff2a00; }"])
    await orch._ajuster_un_fichier(tache, "modele", "PLAN", bundle, split_multi_file(tache.generated_code),
                                   "moteur.css", "", None)
    fichiers = split_multi_file(tache.generated_code)
    assert fichiers["moteur.css"].strip() == ":root { --encre: #ff2a00; }"
    assert fichiers["moteur.html"].strip() == HTML and fichiers["moteur.js"].strip() == JS
    assert "version actuelle, à corriger" in orch.llm_client.contextes[0]


@pytest.mark.asyncio
async def test_html_ecrit_avec_tout_dedans_les_autres_appels_sont_evites(client, auth_headers, db_session):
    tache = await _tache(db_session, client, auth_headers)
    gros_css, gros_js = "body { margin: 0; }\n" * 20, "function setup() { createCanvas(400, 400); }\n" * 10
    page = f"<html><head><style>{gros_css}</style></head><body><script>{gros_js}</script></body></html>"
    orch = UnifiedOrchestrator(db_session)
    orch.llm_client = FauxModele([page])
    await orch._generer_page(tache, "modele", "PLAN", ["m.html", "m.css", "m.js"], "", None)
    assert len(orch.llm_client.contextes) == 1   # CSS et JS sortis de la page : pas d'appel de plus
    fichiers = split_multi_file(tache.generated_code)
    assert "margin" in fichiers["m.css"] and "createCanvas" in fichiers["m.js"]
    assert '<link rel="stylesheet" href="m.css">' in fichiers["m.html"]


@pytest.mark.asyncio
async def test_rejet_sans_fichier_efface_tout_comme_avant(client, auth_headers, db_session):
    tache = await _tache(db_session, client, auth_headers)
    tache.status, tache.generated_code = TaskStatus.MANUAL_REVIEW, join_multi_file({"m.html": HTML})
    tache.task_metadata = {"artifact_path": "m.html", "artifact_files": ["m.html", "m.css", "m.js"]}
    await db_session.commit()
    r = await client.post(f"/api/v1/tasks/{tache.id}/reject", json={"approved": False, "notes": "Non",
                                                                    "fichier": "inconnu.css"}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["generated_code"] is None


@pytest.mark.parametrize("titre, description, attendu", [
    ("Moteur génératif de l'affiche", "Cercles en mouvement, curseur qui accélère l'animation.",
     "moteur-generatif-de-l-affiche.html"),
    ("Mockups de l'affiche", "Déclinaisons sur trois formats.", "mockups-de-l-affiche.html"),
    ("Visuel p5.js", "", "visuel-p5-js.html"),
    ("Feuille de style de l'affiche", "", "styles.css"),
    ("Script JavaScript du site", "", "app.js"),
    ("Animation du menu", "", "app.js"),
    ("Structure HTML de la page", "", "index.html"),
])
def test_ce_qui_se_regarde_devient_une_page(titre, description, attendu):
    from app.services.project_workspace import infer_artifact_path
    assert infer_artifact_path(Task(title=titre, description=description)) == attendu


def test_le_raisonnement_ecrit_avant_le_code_est_retire():
    from app.services.code_cleanup import retirer_preambule
    sortie = """The user wants me to rewrite the `moteur.js` file, fixing the issue where `TWO_PI` is not defined.

Let me analyze the existing code and fix all issues:

1. **Main bug**: `TWO_PI` is used in the initialization loop outside of any sketch function.
- Move circle initialization into `sketch.setup` so `sketch.TWO_PI` is available

Let me write the complete corrected file.


// ===== Moteur génératif =====
(function () {
  "use strict";
})();"""
    assert retirer_preambule(sortie, "moteur.js").startswith("// ===== Moteur génératif")
    css = "Voici la feuille de styles complète pour la page.\n\n:root { --a: red; }\n.titre {\n  color: var(--a);\n}"
    assert retirer_preambule(css, "moteur.css").startswith(":root")
    assert retirer_preambule("Voici la page demandée :\n<!DOCTYPE html>\n<html></html>", "p.html").startswith("<!DOCTYPE")
    # Du vrai code, un Markdown, une ligne de code avant la prose : rien ne bouge
    assert retirer_preambule(JS, "moteur.js") == JS
    assert retirer_preambule("Un README.\n\n# Titre", "README.md") == "Un README.\n\n# Titre"
    code = "const a = 1;\nLe reste est une phrase sans code ici.\n// fin"
    assert retirer_preambule(code, "a.js") == code


@pytest.mark.asyncio
async def test_un_fichier_coupe_par_la_limite_est_signale(client, auth_headers, db_session):
    tache = await _tache(db_session, client, auth_headers)

    class Coupe(FauxModele):
        async def generate_code(self, task, **k):
            code = await super().generate_code(task, **k)
            self.derniere_sortie_tronquee = code.startswith("document")  # le JS est coupé
            return code

    orch = UnifiedOrchestrator(db_session)
    orch.llm_client = Coupe([HTML, CSS, JS])
    await orch._generer_page(tache, "modele", "PLAN", ["moteur.html", "moteur.css", "moteur.js"], "", None)
    assert tache.task_metadata["fichiers_tronques"] == ["moteur.js"]

    # La correction du JS, complète cette fois, retire l'alerte
    orch.llm_client = Coupe(["(function () { /* complet */ })();"])
    await orch._ajuster_un_fichier(tache, "modele", "PLAN", ["moteur.html", "moteur.css", "moteur.js"],
                                   split_multi_file(tache.generated_code), "moteur.js", "", None)
    assert "fichiers_tronques" not in tache.task_metadata


@pytest.mark.asyncio
async def test_si_le_modele_echoue_la_relance_corrige_toujours_le_seul_fichier(client, auth_headers, db_session):
    tache = await _tache(db_session, client, auth_headers)
    tache.generated_code = join_multi_file({"m.html": HTML, "m.css": CSS, "m.js": JS})
    tache.task_metadata = {"artifact_path": "m.html", "artifact_files": ["m.html", "m.css", "m.js"],
                           "fichier_a_ajuster": "m.js"}

    class EnPanne(FauxModele):
        async def generate_code(self, task, **k):
            raise TimeoutError("Ollama muet")

    orch = UnifiedOrchestrator(db_session)
    orch.llm_client = EnPanne([])
    with pytest.raises(TimeoutError):
        await orch._ajuster_un_fichier(tache, "modele", "PLAN", ["m.html", "m.css", "m.js"],
                                       split_multi_file(tache.generated_code), "m.js", "", None)
    assert tache.task_metadata["fichier_a_ajuster"] == "m.js"


@pytest.mark.asyncio
async def test_une_reponse_a_cote_est_redemandee_une_fois(client, auth_headers, db_session):
    from app.services.code_cleanup import fichier_plausible
    assert not fichier_plausible("moteur-generatif-de-l-affiche.html", "moteur.html")
    assert fichier_plausible(HTML, "moteur.html") and fichier_plausible(CSS, "m.css") and fichier_plausible(JS, "m.js")

    tache = await _tache(db_session, client, auth_headers)
    orch = UnifiedOrchestrator(db_session)
    orch.llm_client = FauxModele(["moteur.html", HTML, CSS, JS])
    await orch._generer_page(tache, "modele", "PLAN", ["moteur.html", "moteur.css", "moteur.js"], "", None)
    assert len(orch.llm_client.contextes) == 4
    assert "n'était pas le contenu de `moteur.html`" in orch.llm_client.contextes[1]
    assert split_multi_file(tache.generated_code)["moteur.html"].strip() == HTML

    # Deux fois à côté : échec clair, plutôt qu'une page vide enregistrée
    orch.llm_client = FauxModele(["moteur.html", "moteur.html"])
    with pytest.raises(ValueError, match="n'a pas écrit moteur.html"):
        await orch._generer_page(tache, "modele", "PLAN", ["moteur.html", "moteur.css", "moteur.js"], "", None)
