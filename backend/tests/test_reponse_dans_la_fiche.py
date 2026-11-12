"""
La réponse écrite sur une tâche, et les mots-clés d'une veille mis à jour,
se retrouvent dans la fiche .md du projet — et inversement.

Cas du 12/11/2026 : l'utilisateur répond au « périmètre de la veille », clique
« Mettre à jour la veille », et constate que sa fiche n'a pas bougé. Rien ne
lui montrait que la veille avait changé : il a cliqué cinq fois, et le modèle
a fait dériver les mots-clés à chaque passage.
"""

import pytest
from sqlalchemy import select

from app.models.task import Task, TaskStatus, TaskType
from app.models.veille_topic import VeilleTopic, VeilleScope
from app.services import project_folders as pf
from app.services import veille_update
from app.services.project_markdown import (
    TacheAEcrire, ecrire_mots_cles, ecrire_projet, ecrire_reponse, lire_projet,
)

FICHE = """# Veille des appels d'offres

Repérer les marchés à la portée d'un studio.

## [x] Préciser le périmètre de la veille
type: administratif · priorité: haute
- [ ] Zone géographique
- [ ] Montants

## Veille des consultations
type: veille · mots-clés: marché public communication, identité visuelle · fréquence: hebdo
Limite : la veille passe par la recherche web.

## Dossier de références
type: document
"""


def test_reponse_lue_et_reecrite_a_l_identique():
    texte = ecrire_reponse(FICHE, "Préciser le périmètre de la veille",
                           "Zone : Bourgogne et Bretagne.\nMontants : 2 000 à 50 000 € HT.")
    assert "- [ ] Montants\n\nRéponse : Zone : Bourgogne et Bretagne.\nMontants : 2 000 à 50 000 € HT.\n\n## Veille" in texte

    fiche = lire_projet(texte)
    perimetre = fiche.taches[0]
    assert perimetre.reponse == "Zone : Bourgogne et Bretagne.\nMontants : 2 000 à 50 000 € HT."
    assert perimetre.description == "- [ ] Zone géographique\n- [ ] Montants"   # la réponse n'y est pas

    # Remplacée, pas empilée ; retirée si vide
    texte2 = ecrire_reponse(texte, "Préciser le périmètre de la veille", "Finalement toute la France.")
    assert texte2.count("Réponse :") == 1 and "toute la France" in texte2 and "Bourgogne" not in texte2
    assert "Réponse :" not in ecrire_reponse(texte2, "Préciser le périmètre de la veille", "")
    assert ecrire_reponse(texte, "Tâche inconnue", "x") is None

    # ecrire_projet ↔ lire_projet restent inverses avec une réponse
    ecrit = ecrire_projet("P", "desc", [TacheAEcrire(
        titre="T", fait=True, task_type=TaskType.ADMINISTRATIVE, metadata={},
        description="- [ ] a", reponse="ligne 1\n\nligne 2")])
    relu = lire_projet(ecrit).taches[0]
    assert relu.description == "- [ ] a" and relu.reponse == "ligne 1\nligne 2"


def test_mots_cles_remplaces_dans_la_ligne_de_meta():
    texte = ecrire_mots_cles(FICHE, "Veille des consultations", ["marché public Bretagne", "appel d'offres affiche"])
    assert "type: veille · mots-clés: marché public Bretagne, appel d'offres affiche · fréquence: hebdo" in texte
    assert "identité visuelle" not in texte
    veille = lire_projet(texte).taches[1]
    assert veille.metadata["keywords"] == ["marché public Bretagne", "appel d'offres affiche"]
    # Tâche sans ligne de méta : on en crée une
    texte2 = ecrire_mots_cles(FICHE.replace("type: document\n", ""), "Dossier de références", ["x"])
    assert "## Dossier de références\nmots-clés: x" in texte2


@pytest.fixture
def mac(tmp_path, monkeypatch):
    monkeypatch.setattr(pf.settings, "PROJECTS_MOUNT", str(tmp_path))
    monkeypatch.setattr(pf.settings, "PROJECTS_MOUNT_DISPLAY", "/Users/moi/Documents")
    return tmp_path


@pytest.mark.asyncio
async def test_la_reponse_et_les_mots_cles_vont_dans_la_fiche(client, auth_headers, db_session, mac, monkeypatch):
    dossier = mac / "Projets" / "Pro" / "Veille des appels d'offres"
    dossier.mkdir(parents=True)
    fiche = dossier / "Veille des appels d'offres.md"
    fiche.write_text(FICHE, encoding="utf-8")

    # Sync initiale : projet, tâches et sujet de veille créés depuis la fiche
    await client.put("/api/v1/settings/projects-folder", json={"path": "Projets"}, headers=auth_headers)
    r = await client.post("/api/v1/settings/projects-folder/sync", headers=auth_headers)
    assert r.status_code == 200
    projet = (await client.get("/api/v1/projects/", headers=auth_headers)).json()
    projet = projet["items"][0] if isinstance(projet, dict) else projet[0]
    taches = {t["title"]: t for t in (await client.get(
        f"/api/v1/tasks/?project_id={projet['id']}&limit=500", headers=auth_headers)).json()["items"]}
    perimetre = taches["Préciser le périmètre de la veille"]
    veille = taches["Veille des consultations"]
    assert veille["veille_topic_id"]

    # 1. Répondre dans l'outil → « Réponse : » sous la tâche dans la fiche
    r = await client.put(f"/api/v1/tasks/{perimetre['id']}", json={"user_notes": "Zone : Bourgogne."},
                         headers=auth_headers)
    assert r.status_code == 200
    assert "Réponse : Zone : Bourgogne." in fiche.read_text(encoding="utf-8")

    # 2. Mettre à jour la veille → mots-clés réécrits dans la fiche, et idempotent
    async def proposition(topic, notes, resultat):
        return {"add_keywords": ["marché public Bourgogne"], "remove_keywords": ["identité visuelle"], "add_excluded": []}
    monkeypatch.setattr(veille_update, "proposer_evolution", proposition)
    r = await client.post(f"/api/v1/tasks/{perimetre['id']}/notes-to-veille", headers=auth_headers)
    assert r.status_code == 200 and r.json()["topics"][0]["unchanged"] is False
    texte = fiche.read_text(encoding="utf-8")
    assert "mots-clés: marché public communication, marché public Bourgogne" in texte
    assert "identité visuelle" not in texte

    async def interdit(*a, **k):
        raise AssertionError("le modèle ne doit pas être rappelé pour la même réponse")
    monkeypatch.setattr(veille_update, "proposer_evolution", interdit)
    r = await client.post(f"/api/v1/tasks/{perimetre['id']}/notes-to-veille", headers=auth_headers)
    assert r.json()["topics"][0]["unchanged"] is True

    # 3. La liste des sujets du projet dit ce qui s'est passé
    sujets = (await client.get(f"/api/v1/projects/{projet['id']}/veille-topics", headers=auth_headers)).json()
    assert sujets[0]["keywords"] == ["marché public communication", "marché public Bourgogne"]
    assert sujets[0]["last_refinement"]["source_task_id"] == perimetre["id"]

    # 4. La sync suivante ne défait rien (notre écriture n'est pas une retouche de l'utilisateur)
    r = await client.post("/api/v1/settings/projects-folder/sync", headers=auth_headers)
    assert r.status_code == 200
    topic = (await db_session.execute(select(VeilleTopic).where(VeilleTopic.id == veille["veille_topic_id"]))).scalar_one()
    assert topic.keywords == ["marché public communication", "marché public Bourgogne"]

    # 5. Retouche à la main dans la fiche : réponse et mots-clés remontent dans l'outil
    texte = fiche.read_text(encoding="utf-8")
    texte = texte.replace("Réponse : Zone : Bourgogne.", "Réponse : Zone : Bourgogne et Bretagne.")
    texte = texte.replace("mots-clés: marché public communication, marché public Bourgogne",
                          "mots-clés: marché public Bretagne")
    fiche.write_text(texte, encoding="utf-8")
    await client.post("/api/v1/settings/projects-folder/sync", headers=auth_headers)
    db_session.expire_all()
    t = (await db_session.execute(select(Task).where(Task.id == perimetre["id"]))).unique().scalar_one()
    assert t.user_notes == "Zone : Bourgogne et Bretagne."
    topic = (await db_session.execute(select(VeilleTopic).where(VeilleTopic.id == veille["veille_topic_id"]))).scalar_one()
    assert topic.keywords == ["marché public Bretagne"]


# ------------------------------------------------- la description aussi --

def test_la_description_se_remplace_entre_le_titre_et_la_premiere_tache():
    from app.services.project_markdown import ecrire_description
    texte = ecrire_description(FICHE, "Zone : Bourgogne et Bretagne.\n\nMarchés de 2 000 à 50 000 € HT.")
    assert texte.startswith("# Veille des appels d'offres\n\nZone : Bourgogne et Bretagne.\n\nMarchés de 2 000 à 50 000 € HT.\n\n## [x] Préciser")
    assert "Repérer les marchés" not in texte
    fiche = lire_projet(texte)
    assert fiche.description == "Zone : Bourgogne et Bretagne.\n\nMarchés de 2 000 à 50 000 € HT."
    assert [t.titre for t in fiche.taches] == [t.titre for t in lire_projet(FICHE).taches]
    # Sans tâche : la description termine la fiche ; sans titre : rien à faire
    assert ecrire_description("# P\n\nancienne\n", "nouvelle") == "# P\n\nnouvelle\n"
    assert ecrire_description("## Tâche\n", "x") is None
    # Un « ## » dans la description deviendrait une tâche : abaissé
    assert "### Partie" in ecrire_description(FICHE, "## Partie\ntexte")


@pytest.mark.asyncio
async def test_la_reponse_reecrit_la_description_du_projet_et_de_la_fiche(
        client, auth_headers, db_session, mac, monkeypatch):
    from app.models.project import Project
    from app.services import reponse_vers_projet

    dossier = mac / "Projets" / "Pro" / "Veille des appels d'offres"
    dossier.mkdir(parents=True)
    fiche = dossier / "Veille des appels d'offres.md"
    fiche.write_text(FICHE.replace(
        "Repérer les marchés à la portée d'un studio.",
        "Repérer les marchés à la portée d'un studio.\n\nÀ préciser : zone géographique, montants visés."),
        encoding="utf-8")
    await client.put("/api/v1/settings/projects-folder", json={"path": "Projets"}, headers=auth_headers)
    await client.post("/api/v1/settings/projects-folder/sync", headers=auth_headers)
    projet = (await client.get("/api/v1/projects/", headers=auth_headers)).json()
    projet = projet["items"][0] if isinstance(projet, dict) else projet[0]
    taches = {t["title"]: t for t in (await client.get(
        f"/api/v1/tasks/?project_id={projet['id']}&limit=500", headers=auth_headers)).json()["items"]}
    perimetre = taches["Préciser le périmètre de la veille"]

    # Sans réponse : refus
    r = await client.post(f"/api/v1/tasks/{perimetre['id']}/notes-to-project", headers=auth_headers)
    assert r.status_code == 400

    await client.put(f"/api/v1/tasks/{perimetre['id']}", json={"user_notes": "Zone : Bourgogne. Marchés de 2 000 à 50 000 €."},
                     headers=auth_headers)

    async def reecriture(project, task, notes):
        assert "À préciser" in project.description and "Bourgogne" in notes
        return "Repérer les marchés à la portée d'un studio.\n\nPérimètre : Bourgogne ; marchés de 2 000 à 50 000 €."
    monkeypatch.setattr(reponse_vers_projet, "proposer_description", reecriture)
    async def pas_de_veille(topic, notes, resultat):
        return {"add_keywords": [], "remove_keywords": [], "add_excluded": []}
    monkeypatch.setattr(veille_update, "proposer_evolution", pas_de_veille)

    r = await client.post(f"/api/v1/tasks/{perimetre['id']}/notes-to-project", headers=auth_headers)
    assert r.status_code == 200
    d = r.json()["description"]
    assert d["unchanged"] is False and d["mode"] == "modele" and "Périmètre : Bourgogne" in d["description"]
    assert "À préciser" in d["previous"]

    # Dans l'outil, dans la fiche, et l'historique garde l'ancienne version
    assert "Périmètre : Bourgogne" in (await client.get(f"/api/v1/projects/{projet['id']}", headers=auth_headers)).json()["description"]
    texte = fiche.read_text(encoding="utf-8")
    assert "\n\nPérimètre : Bourgogne ; marchés de 2 000 à 50 000 €.\n\n## [x] Préciser" in texte
    assert "À préciser" not in texte
    assert "Réponse : Zone : Bourgogne." in texte  # la réponse sous la tâche n'a pas bougé
    projet_db = (await db_session.execute(select(Project).where(Project.id == projet["id"]))).scalar_one()
    assert projet_db.description_history[-1]["previous"].startswith("Repérer") \
        and "À préciser" in projet_db.description_history[-1]["previous"]

    # Même réponse : le modèle n'est pas rappelé
    async def interdit(*a, **k):
        raise AssertionError("même réponse : pas de nouvel appel au modèle")
    monkeypatch.setattr(reponse_vers_projet, "proposer_description", interdit)
    r = await client.post(f"/api/v1/tasks/{perimetre['id']}/notes-to-project", headers=auth_headers)
    assert r.json()["description"]["unchanged"] is True

    # Réponse modifiée, modèle en panne : la réponse est ajoutée datée, rien n'est perdu
    async def en_panne(*a, **k):
        raise RuntimeError("Ollama injoignable")
    monkeypatch.setattr(reponse_vers_projet, "proposer_description", en_panne)
    await client.put(f"/api/v1/tasks/{perimetre['id']}", json={"user_notes": "Finalement aussi la Bretagne."},
                     headers=auth_headers)
    r = await client.post(f"/api/v1/tasks/{perimetre['id']}/notes-to-project", headers=auth_headers)
    d = r.json()["description"]
    assert d["mode"] == "ajout" and d["description"].startswith("Repérer") \
        and "Précisé le " in d["description"] and "aussi la Bretagne" in d["description"]
    assert "aussi la Bretagne" in fiche.read_text(encoding="utf-8")

    # La sync suivante ne défait rien
    await client.post("/api/v1/settings/projects-folder/sync", headers=auth_headers)
    assert "aussi la Bretagne" in (await client.get(f"/api/v1/projects/{projet['id']}", headers=auth_headers)).json()["description"]


def test_une_proposition_demesuree_ou_sectionnee_est_refusee():
    from app.services.reponse_vers_projet import _acceptable
    assert _acceptable("Un texte court.", "Un autre texte.")
    assert not _acceptable("", "x")
    assert not _acceptable("## Plan\n- a", "x")
    assert not _acceptable("x" * 1600, "petit")
    assert _acceptable("x" * 1400, "petit")


@pytest.mark.asyncio
async def test_les_occurrences_de_veille_restent_hors_de_la_fiche(client, auth_headers, db_session, mac):
    from app.services.project_folders import write_project_markdown
    from app.models.project import Project

    dossier = mac / "Projets" / "Pro" / "Veille des appels d'offres"
    dossier.mkdir(parents=True)
    fiche = dossier / "Veille des appels d'offres.md"
    fiche.write_text(FICHE, encoding="utf-8")
    await client.put("/api/v1/settings/projects-folder", json={"path": "Projets"}, headers=auth_headers)
    await client.post("/api/v1/settings/projects-folder/sync", headers=auth_headers)
    projet = (await db_session.execute(select(Project))).scalars().first()
    topic = (await db_session.execute(select(VeilleTopic).where(VeilleTopic.project_id == projet.id))).scalar_one()
    for jour in ("05/11/2026", "12/11/2026"):
        db_session.add(Task(project_id=projet.id, title=f"Veille — {topic.name} · {jour}", task_type=TaskType.VEILLE,
                            status=TaskStatus.COMPLETED, veille_topic_id=topic.id,
                            task_metadata={"auto_generated": True, "occurrence_from_topic": topic.id}))
    await db_session.commit()
    user_id = projet.user_id
    await write_project_markdown(db_session, user_id, projet, force=True)
    texte = fiche.read_text(encoding="utf-8")
    assert texte.count("## ") == 3 and "Veille — " not in texte
    assert "## Veille des consultations\ntype: veille · mots-clés: marché public communication, identité visuelle" in texte
