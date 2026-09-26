"""
Tests des projets tenus dans des dossiers du Mac (une fiche .md par dossier).

Tout se passe dans un dossier temporaire qui joue le rôle du dossier partagé :
jamais dans les vrais fichiers.
"""

from datetime import date

import pytest
from sqlalchemy import select

from app.models.project import Project
from app.models.task import Task, TaskStatus, TaskType, task_dependencies
from app.models.user_settings import UserSettings
from app.models.veille_topic import VeilleTopic
from app.services import project_folders as pf
from app.services.project_markdown import cocher_tache, lire_echeance, lire_projet

FICHE = """# Tickets de veille

Une imprimante thermique qui imprime l'actu écologique en ASCII.

## Veille visuelle
mots-clés: ticket de caisse, ASCII art

## Note d'intention
type: document · échéance: 15/10/2026 · après: Veille visuelle · priorité: haute
Ton personnel.
- [ ] Origine du projet
- [ ] Dispositif technique

## Page web
type: code · après: Note d'intention · fichier: index.html
"""


# ------------------------------------------------------------- lecture --

def test_lecture_complete():
    p = lire_projet(FICHE, date(2026, 9, 27))
    assert p.titre == "Tickets de veille"
    assert "imprimante thermique" in p.description
    assert [t.titre for t in p.taches] == ["Veille visuelle", "Note d'intention", "Page web"]
    veille, note, page = p.taches
    assert veille.task_type == TaskType.VEILLE and veille.metadata["scope"] == "visual"
    assert veille.metadata["keywords"] == ["ticket de caisse", "ASCII art"]
    assert note.task_type == TaskType.DOCUMENT_WRITING and note.priorite.value == "P1"
    assert note.echeance.date() == date(2026, 10, 15)
    assert note.apres == ["Veille visuelle"]
    assert "- [ ] Origine du projet" in note.description
    assert page.metadata["artifact_path"] == "index.html"
    assert p.erreurs == []


def test_texte_libre_seulement():
    p = lire_projet("Juste une idée de projet, sans titre ni tâche.")
    assert p.titre is None and p.taches == [] and "idée" in p.description


def test_type_devine_sans_type_explicite():
    p = lire_projet("## Moodboard des tickets\n\n## Styles CSS\n\n## Appels à projets 2027\n")
    assert [(t.task_type, t.metadata.get("scope")) for t in p.taches] == [
        (TaskType.VEILLE, "visual"), (TaskType.CODE_GENERATION, None), (TaskType.FUNDING_SEARCH, None)]


def test_titre_dans_un_bloc_de_code_ignore():
    p = lire_projet("## Vraie tâche\n```\n## pas une tâche\n```\n")
    assert [t.titre for t in p.taches] == ["Vraie tâche"]


def test_erreurs_signalees_sans_bloquer():
    p = lire_projet("## A\ntype: sculpture · après: Z · échéance: 45/13\n\n## A\n")
    assert len(p.taches) == 1
    texte = " ".join(p.erreurs)
    assert "sculpture" in texte and "Z" in texte and "45/13" in texte and "double" in texte


@pytest.mark.parametrize("valeur, attendu", [
    ("15/10", date(2026, 10, 15)),
    ("01/03", date(2027, 3, 1)),        # déjà passée cette année → l'an prochain
    ("15/10/27", date(2027, 10, 15)),
    ("2026-12-01", date(2026, 12, 1)),
    ("31/02", None),
])
def test_echeances(valeur, attendu):
    lu = lire_echeance(valeur, date(2026, 9, 27))
    assert (lu.date() if lu else None) == attendu


def test_cocher_une_tache():
    coche = cocher_tache(FICHE, "note d'intention")
    assert "## [x] Note d'intention" in coche
    assert cocher_tache(coche, "Note d'intention") is None  # déjà cochée
    assert cocher_tache(FICHE, "Inexistante") is None


# --------------------------------------------------------- dossiers --

@pytest.fixture
def mac(tmp_path, monkeypatch):
    monkeypatch.setattr(pf.settings, "PROJECTS_MOUNT", str(tmp_path))
    monkeypatch.setattr(pf.settings, "PROJECTS_MOUNT_DISPLAY", "/Users/moi/Documents")
    (tmp_path / "Projets").mkdir()
    return tmp_path


@pytest.fixture
async def moi(client, auth_headers, db_session, mac):
    uid = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"]
    db_session.add(UserSettings(user_id=uid, projects_folder="Projets"))
    await db_session.commit()
    return uid


def _ecrire(mac, dossier, nom, texte):
    (mac / "Projets" / dossier).mkdir(parents=True, exist_ok=True)
    (mac / "Projets" / dossier / nom).write_text(texte, encoding="utf-8")
    return mac / "Projets" / dossier / nom


async def _taches(db, projet_id):
    db.expire_all()
    return {t.title: t for t in (await db.execute(
        select(Task).where(Task.project_id == projet_id))).unique().scalars().all()}


def test_chemins_hors_du_partage_refuses(mac):
    for mauvais in ("../", "Projets/../../etc", "/../.."):
        with pytest.raises(ValueError):
            pf.inside_mount(mauvais)
    assert pf.browse("")["display"] == "/Users/moi/Documents"
    assert [d["name"] for d in pf.browse("")["dirs"]] == ["Projets"]


def test_parcours_montre_aussi_les_fichiers(mac):
    """Un dossier sans sous-dossier semblait vide : ses fichiers doivent apparaître."""
    d = mac / "Projets" / "Expo" / "Textes"
    d.mkdir(parents=True)
    (d / "fiche.md").write_text("x")
    (d / "photo.jpg").write_bytes(b"x")
    (d / ".DS_Store").write_bytes(b"x")
    vu = pf.browse("Projets/Expo/Textes")
    assert vu["dirs"] == []
    assert vu["files"] == [{"name": "fiche.md", "is_md": True}, {"name": "photo.jpg", "is_md": False}]
    assert [e["name"] for e in vu["breadcrumb"]] == ["Documents", "Projets", "Expo", "Textes"]
    assert vu["breadcrumb"][2]["path"] == "Projets/Expo"


def test_fiche_du_dossier_choisie(mac):
    d = mac / "Projets" / "Expo"
    d.mkdir()
    (d / "notes.md").write_text("x")
    (d / "Expo.md").write_text("y")
    assert pf.pick_project_file(d).name == "Expo.md"


@pytest.mark.asyncio
async def test_dossier_devient_projet(db_session, moi, mac):
    _ecrire(mac, "Tickets de veille", "tickets.md", FICHE)
    rapport = await pf.sync_user(db_session, moi)
    assert rapport.created == ["Tickets de veille"]

    projet = (await db_session.execute(select(Project).where(Project.user_id == moi))).scalars().one()
    assert projet.source_path == "Projets/Tickets de veille/tickets.md"
    taches = await _taches(db_session, projet.id)
    assert set(taches) == {"Veille visuelle", "Note d'intention", "Page web"}
    assert all(t.status == TaskStatus.CREATED for t in taches.values())  # Tom active lui-même

    deps = (await db_session.execute(select(task_dependencies))).all()
    assert (taches["Note d'intention"].id, taches["Veille visuelle"].id) in deps
    assert (taches["Page web"].id, taches["Note d'intention"].id) in deps
    assert (await db_session.execute(select(VeilleTopic))).scalars().first().scope.value == "visual"

    # Sans changement : rien n'est réimporté
    assert (await pf.sync_user(db_session, moi)).updated == []


@pytest.mark.asyncio
async def test_modifications_de_la_fiche_suivies(db_session, moi, mac):
    fiche = _ecrire(mac, "Tickets", "tickets.md", FICHE)
    await pf.sync_user(db_session, moi)

    fiche.write_text(FICHE.replace("## Page web\ntype: code · après: Note d'intention · fichier: index.html\n",
                                   "## Dossier de candidature\n")
                     .replace("## Veille visuelle", "## [x] Veille visuelle"), encoding="utf-8")
    rapport = await pf.sync_user(db_session, moi)
    assert rapport.updated == ["Tickets de veille"]

    projet_id = (await db_session.execute(select(Project.id))).scalar_one()
    taches = await _taches(db_session, projet_id)
    assert taches["Veille visuelle"].status == TaskStatus.COMPLETED   # cochée à la main
    assert taches["Page web"].status == TaskStatus.CANCELLED           # retirée, jamais lancée
    assert taches["Dossier de candidature"].status == TaskStatus.CREATED


@pytest.mark.asyncio
async def test_tache_terminee_cochee_dans_la_fiche_une_seule_fois(db_session, moi, mac):
    fiche = _ecrire(mac, "Tickets", "tickets.md", FICHE)
    await pf.sync_user(db_session, moi)
    projet_id = (await db_session.execute(select(Project.id))).scalar_one()
    note = (await _taches(db_session, projet_id))["Note d'intention"]
    note.status = TaskStatus.COMPLETED
    note.generated_code = "Texte de la note."
    await db_session.commit()

    rapport = await pf.sync_user(db_session, moi)
    assert rapport.checked == ["Tickets de veille — Note d'intention"]
    texte = fiche.read_text(encoding="utf-8")
    assert "## [x] Note d'intention" in texte
    assert "## Veille visuelle" in texte  # le reste intact

    # Tom la décoche : l'outil ne la recoche pas
    fiche.write_text(texte.replace("## [x] Note d'intention", "## Note d'intention"), encoding="utf-8")
    await pf.sync_user(db_session, moi)
    assert "## Note d'intention" in fiche.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_production_ecrite_sans_ecraser_une_retouche(db_session, moi, mac):
    _ecrire(mac, "Tickets", "tickets.md", FICHE)
    await pf.sync_user(db_session, moi)
    projet_id = (await db_session.execute(select(Project.id))).scalar_one()
    page = (await _taches(db_session, projet_id))["Page web"]
    page.status, page.generated_code = TaskStatus.COMPLETED, "<p>v1</p>"
    await db_session.commit()

    await pf.sync_user(db_session, moi)
    sortie = mac / "Projets" / "Tickets" / "Production" / "index.html"
    assert sortie.read_text() == "<p>v1</p>\n"

    sortie.write_text("<p>retouché à la main</p>")
    page = (await _taches(db_session, projet_id))["Page web"]
    page.generated_code = "<p>v2</p>"
    await db_session.commit()
    rapport = await pf.sync_user(db_session, moi)
    assert sortie.read_text() == "<p>retouché à la main</p>"
    assert rapport.kept == ["Tickets de veille — index.html"]
    # signalé une fois, pas à chaque passage
    assert (await pf.sync_user(db_session, moi)).kept == []


@pytest.mark.asyncio
async def test_fiche_deposee_devient_un_dossier(db_session, moi, mac):
    (mac / "Projets" / "Tickets de veille").mkdir()  # déjà pris : ne pas écrire dedans
    projet = await pf.import_markdown_file(db_session, moi, "tickets.md", FICHE)
    assert projet.source_path == "Projets/Tickets de veille 2/tickets.md"
    assert (mac / "Projets" / "Tickets de veille 2" / "tickets.md").read_text(encoding="utf-8") == FICHE
    assert list((mac / "Projets" / "Tickets de veille").iterdir()) == []


@pytest.mark.asyncio
async def test_fiche_deposee_sans_dossier_configure(client, auth_headers, db_session, mac):
    uid = (await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"]
    projet = await pf.import_markdown_file(db_session, uid, "idee.md", "Une idée libre.")
    assert projet.name == "idee" and projet.source_path is None
    assert projet.description == "Une idée libre."


# ---------------------------------------------------------------- API --

@pytest.mark.asyncio
async def test_api_choisir_le_dossier_et_synchroniser(client, auth_headers, mac):
    _ecrire(mac, "Tickets", "tickets.md", FICHE)

    r = await client.get("/api/v1/settings/projects-folder/browse", headers=auth_headers)
    assert r.status_code == 200 and r.json()["dirs"][0]["name"] == "Projets"

    r = await client.put("/api/v1/settings/projects-folder", json={"path": "Projets"}, headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["display"] == "/Users/moi/Documents/Projets"
    assert data["projects"][0]["folder"] == "Tickets"
    assert data["report"]["created"] == ["Tickets de veille"]

    projets = (await client.get("/api/v1/projects/", headers=auth_headers)).json()["items"]
    assert projets[0]["source_path"] == "Projets/Tickets/tickets.md"


@pytest.mark.asyncio
async def test_api_refuse_de_sortir_du_partage(client, auth_headers, mac):
    for chemin in ("../..", "Projets/../../etc"):
        r = await client.put("/api/v1/settings/projects-folder", json={"path": chemin}, headers=auth_headers)
        assert r.status_code == 400
        r = await client.get("/api/v1/settings/projects-folder/browse", params={"path": chemin},
                             headers=auth_headers)
        assert r.status_code == 400


@pytest.mark.asyncio
async def test_api_deposer_une_fiche(client, auth_headers, mac):
    r = await client.post("/api/v1/projects/import-md", headers=auth_headers,
                          files={"file": ("expo.md", FICHE.encode(), "text/markdown")})
    assert r.status_code == 201, r.text
    assert r.json()["name"] == "Tickets de veille"

    r = await client.post("/api/v1/projects/import-md", headers=auth_headers,
                          files={"file": ("image.png", b"x", "image/png")})
    assert r.status_code == 400


# ------------------------------------------------ outil → fiche (bouton) --

async def _projet_outil(client, auth_headers, db):
    """Projet créé dans l'outil, avec tâches, dépendance, veille et tâche finie."""
    from app.models.task import TaskPriority
    from datetime import datetime, timezone

    pid = (await client.post("/api/v1/projects/", json={
        "name": "Expo Lyon 2027", "type": "personal", "features": {"code_gen": True},
        "description": "Installation sonore.\n## Pas une tâche",
    }, headers=auth_headers)).json()["id"]
    veille = Task(project_id=pid, title="Veille festivals", task_type=TaskType.VEILLE,
                  status=TaskStatus.COMPLETED, task_metadata={"scope": "cultural", "keywords": ["son", "Lyon"]})
    note = Task(project_id=pid, title="Note d'intention", task_type=TaskType.DOCUMENT_WRITING,
                status=TaskStatus.CREATED, priority=TaskPriority.P1,
                description="Ton personnel.\n## Contexte\n- [ ] Origine",
                due_date=datetime(2026, 11, 2, 18, tzinfo=timezone.utc))
    doublon = Task(project_id=pid, title="note d'intention", task_type=TaskType.DOCUMENT_WRITING,
                   status=TaskStatus.CREATED)
    db.add_all([veille, note, doublon])
    await db.flush()
    await db.execute(task_dependencies.insert().values(task_id=note.id, depends_on_id=veille.id))
    await db.commit()
    return pid


@pytest.mark.asyncio
async def test_bouton_ecrit_dossier_et_fiche_relue_a_l_identique(client, auth_headers, db_session, moi, mac):
    pid = await _projet_outil(client, auth_headers, db_session)
    r = await client.post(f"/api/v1/projects/{pid}/write-md", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["created"] and r.json()["path"] == "Projets/Expo Lyon 2027/Expo Lyon 2027.md"

    texte = (mac / "Projets" / "Expo Lyon 2027" / "Expo Lyon 2027.md").read_text(encoding="utf-8")
    assert "## [x] Veille festivals\ntype: veille culturelle · mots-clés: son, Lyon" in texte
    assert "type: document · échéance: 02/11/2026 · après: Veille festivals · priorité: haute" in texte
    assert "### Contexte" in texte and "### Pas une tâche" in texte   # titres abaissés
    assert "## note d'intention (2)" in texte                        # doublon rendu distinct

    avant = {t.title: (t.status, t.task_type) for t in (await _taches(db_session, pid)).values()}
    rapport = await pf.sync_user(db_session, moi)
    assert rapport.created == [] and rapport.warnings == []
    apres = {t.title: (t.status, t.task_type) for t in (await _taches(db_session, pid)).values()}
    assert apres == avant  # la synchronisation suivante ne change rien


@pytest.mark.asyncio
async def test_bouton_ne_perd_pas_une_modification_de_la_fiche(client, auth_headers, db_session, moi, mac):
    pid = await _projet_outil(client, auth_headers, db_session)
    await client.post(f"/api/v1/projects/{pid}/write-md", headers=auth_headers)
    fiche = mac / "Projets" / "Expo Lyon 2027" / "Expo Lyon 2027.md"
    fiche.write_text(fiche.read_text(encoding="utf-8") + "\n## Ajout à la main\n", encoding="utf-8")

    r = await client.post(f"/api/v1/projects/{pid}/write-md", headers=auth_headers)
    assert r.status_code == 412
    assert "Ajout à la main" in fiche.read_text(encoding="utf-8")

    r = await client.post(f"/api/v1/projects/{pid}/write-md", params={"force": True}, headers=auth_headers)
    assert r.status_code == 200 and not r.json()["created"]
    assert "Ajout à la main" not in fiche.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_bouton_sans_dossier_configure(client, auth_headers, db_session, mac):
    pid = await _projet_outil(client, auth_headers, db_session)
    r = await client.post(f"/api/v1/projects/{pid}/write-md", headers=auth_headers)
    assert r.status_code == 409 and "Paramètres" in r.json().get("message", r.text)


@pytest.mark.asyncio
async def test_ecrire_toutes_les_fiches(client, auth_headers, db_session, moi, mac):
    await _projet_outil(client, auth_headers, db_session)
    archive = (await client.post("/api/v1/projects/", json={
        "name": "Vieux projet", "type": "personal", "features": {"code_gen": True},
    }, headers=auth_headers)).json()["id"]
    projet = (await db_session.execute(select(Project).where(Project.id == archive))).scalar_one()
    from app.models.project import ProjectStatus
    projet.status = ProjectStatus.ARCHIVED
    await db_session.commit()

    r = await client.post("/api/v1/projects/write-md-all", headers=auth_headers)
    assert [p["name"] for p in r.json()["written"]] == ["Expo Lyon 2027"]
    # Une seconde fois : plus rien à écrire
    r = await client.post("/api/v1/projects/write-md-all", headers=auth_headers)
    assert r.json()["written"] == []
