"""
Tests de la transmission des résultats d'une tâche à celles qui en dépendent.

Constat du 23/09/2026 : une tâche de rédaction ne recevait que le nom du projet
— ni sa propre consigne, ni la recherche ou la veille qui la précédaient. Deux
documents d'un même projet sortaient donc identiques et génériques.
"""

import inspect

import pytest
from sqlalchemy import insert

from app.models.task import Task, TaskStatus, TaskType, task_dependencies
from app.models.veille_result import VeilleResult, VeilleResultStatus, VeilleResultType
from app.models.veille_topic import VeilleScope, VeilleTopic
from app.services.task_chain import (
    brief_without_checklist, build_upstream_context, checklist_items,
)


# ------------------------------------------------------------ checklist --

def test_sous_taches_extraites_de_la_description():
    description = "Rédiger la note.\n\n- [ ] Origine du projet\n- [x] Dispositif\n* [ ] Calendrier"
    assert checklist_items(description) == ["Origine du projet", "Dispositif", "Calendrier"]
    assert brief_without_checklist(description) == "Rédiger la note."


def test_description_sans_checklist():
    assert checklist_items("Simple consigne") == []
    assert checklist_items(None) == []
    assert brief_without_checklist(None) == ""


# ------------------------------------------------------------ chaînage --

async def _projet(client, auth_headers) -> int:
    r = await client.post("/api/v1/projects/", json={
        "name": "Chaîne", "type": "personal", "features": {"code_gen": True},
    }, headers=auth_headers)
    return r.json()["id"]


@pytest.mark.asyncio
async def test_contexte_amont_reprend_texte_et_veille(client, auth_headers, db_session):
    project_id = await _projet(client, auth_headers)

    recherche = Task(project_id=project_id, title="État de l'art", task_type=TaskType.RESEARCH,
                     status=TaskStatus.COMPLETED, generated_code="Artiste repéré : Mme Tickets.")
    topic = VeilleTopic(project_id=project_id, name="Veille", scope=VeilleScope.NEWS,
                        keywords=[], scan_frequency="once")
    db_session.add_all([recherche, topic])
    await db_session.flush()

    veille = Task(project_id=project_id, title="Veille actus", task_type=TaskType.VEILLE,
                  status=TaskStatus.COMPLETED, veille_topic_id=topic.id)
    vide = Task(project_id=project_id, title="Tâche pas encore faite",
                task_type=TaskType.DOCUMENT_WRITING, status=TaskStatus.CREATED)
    note = Task(project_id=project_id, title="Note d'intention",
                task_type=TaskType.DOCUMENT_WRITING, status=TaskStatus.CREATED)
    db_session.add_all([veille, vide, note])
    await db_session.flush()

    def resultat(titre, score, statut=VeilleResultStatus.NEW):
        return VeilleResult(topic_id=topic.id, task_id=veille.id, title=titre,
                            result_type=VeilleResultType.NEWS_ARTICLE, relevance_score=score,
                            status=statut, url=f"https://exemple.org/{score}")

    db_session.add_all([
        resultat("Article moyen", 60),
        resultat("Article gardé", 40, VeilleResultStatus.SAVED),
        resultat("Article écarté", 99, VeilleResultStatus.DISMISSED),
    ])
    await db_session.execute(insert(task_dependencies), [
        {"task_id": note.id, "depends_on_id": dep.id} for dep in (recherche, veille, vide)
    ])
    await db_session.flush()

    contexte = await build_upstream_context(db_session, note)

    assert "Mme Tickets" in contexte
    assert "Article moyen" in contexte
    assert "Article écarté" not in contexte
    # Ce que l'utilisateur a mis de côté passe devant le score
    assert contexte.index("Article gardé") < contexte.index("Article moyen")
    assert "n'a encore rien produit" in contexte


@pytest.mark.asyncio
async def test_code_des_dependances_non_repete(client, auth_headers, db_session):
    """Le code amont arrive déjà par le plan de fichiers."""
    project_id = await _projet(client, auth_headers)
    html = Task(project_id=project_id, title="Structure HTML", task_type=TaskType.CODE_GENERATION,
                status=TaskStatus.COMPLETED, generated_code="<main></main>")
    css = Task(project_id=project_id, title="Styles CSS", task_type=TaskType.CODE_GENERATION,
               status=TaskStatus.CREATED)
    db_session.add_all([html, css])
    await db_session.flush()
    await db_session.execute(insert(task_dependencies), [{"task_id": css.id, "depends_on_id": html.id}])

    assert await build_upstream_context(db_session, css, skip_code=True) == ""
    assert "<main>" in await build_upstream_context(db_session, css)


@pytest.mark.asyncio
async def test_sans_dependance_rien(client, auth_headers, db_session):
    project_id = await _projet(client, auth_headers)
    seule = Task(project_id=project_id, title="Seule", task_type=TaskType.RESEARCH,
                 status=TaskStatus.CREATED)
    db_session.add(seule)
    await db_session.flush()
    assert await build_upstream_context(db_session, seule) == ""


# ----------------------------------------------------------- branchement --

def test_prompt_document_contient_consigne_et_amont():
    from app.services.modules.prompt_generator import PromptGeneratorModule

    prompt = PromptGeneratorModule().generate_document_prompt(
        document_type="Note d'intention",
        context={"project_name": "P", "project_description": "Une installation",
                 "task_title": "Note d'intention", "task_brief": "Ton personnel",
                 "upstream": "## Résultats des tâches précédentes\nMme Tickets"},
        sections=[{"name": "Origine", "max_words": 200}],
    )
    for attendu in ("Une installation", "Ton personnel", "Mme Tickets", "Origine"):
        assert attendu in prompt


def test_handlers_branches_sur_le_contexte_amont():
    from app.services.unified_orchestrator import UnifiedOrchestrator

    for handler in (UnifiedOrchestrator._handle_document_writing,
                    UnifiedOrchestrator._handle_research,
                    UnifiedOrchestrator._handle_administrative,
                    UnifiedOrchestrator._handle_code_generation):
        assert "build_upstream_context" in inspect.getsource(handler), handler.__name__
