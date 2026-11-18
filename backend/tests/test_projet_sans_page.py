"""
Projet « Catalogue Expérimentations Visuelles » (18/11/2026) : planifié comme
un projet Node/Vite (package.json, styles.css, app.js), sans page HTML. Les
tâches « Développement de la première expérience 3D », « … deuxième… »,
« Optimisation » n'avaient pas de fichier : chacune a réécrit app.js en
entier, la dernière effaçant les autres, et rien ne pouvait s'afficher.
"""

import pytest

from app.models.task import Task, TaskStatus, TaskType
from app.services.code_cleanup import join_multi_file
from app.services.project_workspace import build_file_plan


def _t(i, titre, prompt=None):
    return Task(id=i, title=titre, task_type=TaskType.CODE_GENERATION, llm_prompt=prompt)


def test_une_tache_qui_cree_une_partie_nouvelle_a_son_propre_fichier():
    plan = build_file_plan([
        _t(1, "Conception de l'interface minimale et typographie", "Feuille `styles.css` : typographie, grille."),
        _t(2, "Développement de la première expérience visuelle 3D"),
        _t(3, "Création du système de navigation par scroll fluide"),
        _t(4, "Optimisation des performances et du rendu"),
    ])
    assert plan[1] == "styles.css"
    assert plan[2] == "developpement-de-la-premiere-experience.js"
    assert plan[3].startswith("creation-du-systeme-de-navigation") and plan[3].endswith(".js")
    assert plan[4] is None                      # transverse : retouche les fichiers des autres
    # Hors projet web, rien n'est inventé
    assert build_file_plan([_t(5, "Développement du moteur d'analyse")]) == {5: None}


@pytest.mark.asyncio
async def test_l_apercu_montre_la_version_de_la_tache_meme_reecrite_depuis(client, auth_headers, db_session):
    r = await client.post("/api/v1/projects/", json={"name": "Catalogue", "type": "professional"}, headers=auth_headers)
    pid = r.json()["id"]
    ancienne = Task(project_id=pid, title="Optimisation du rendu", task_type=TaskType.CODE_GENERATION,
                    status=TaskStatus.COMPLETED, generated_code=join_multi_file({"app.js": "const v = 1;"}))
    recente = Task(project_id=pid, title="Optimisation finale", task_type=TaskType.CODE_GENERATION,
                   status=TaskStatus.MANUAL_REVIEW,
                   generated_code=join_multi_file({"app.js": "const v = 2;", "styles.css": "body { margin: 0; }"}))
    db_session.add_all([ancienne, recente])
    await db_session.commit()

    apercu = (await client.get(f"/api/v1/tasks/{ancienne.id}/apercu", headers=auth_headers)).json()
    miens = {f["path"]: f["content"] for f in apercu["files"] if f["mine"]}
    autres = {f["path"] for f in apercu["files"] if not f["mine"]}
    assert miens == {"app.js": "const v = 1;\n"}          # sa version, pas celle qui l'a remplacée
    assert autres == {"styles.css"}                         # le reste du projet, pour l'habiller
    assert apercu["entry"] is None                          # pas de page : l'écran en fabrique une
