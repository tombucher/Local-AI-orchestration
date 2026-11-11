"""
Liste des tâches : dépendances incluses, et une page assez grande pour tout
l'atelier.

Le journal lit toutes les tâches vivantes d'un coup pour dire ce qui attend.
Sans les dépendances, il proposait de lancer une tâche dont la précédente
n'était pas faite ; avec 50 tâches par page, il en oubliait en silence.
"""

import pytest


@pytest.mark.asyncio
async def test_liste_avec_dependances_et_grande_page(client, auth_headers):
    r = await client.post("/api/v1/projects/", json={
        "name": "Liste", "type": "personal", "features": {"code_gen": True}}, headers=auth_headers)
    pid = r.json()["id"]
    creer = lambda **champs: client.post("/api/v1/tasks/", json={"project_id": pid, "priority": "P2", **champs},
                                        headers=auth_headers)
    a = (await creer(title="Note d'intention", priority="P1")).json()["id"]
    b = (await creer(title="Schéma", dependency_ids=[a])).json()["id"]

    r = await client.get("/api/v1/tasks/?limit=500", headers=auth_headers)
    assert r.status_code == 200
    par_id = {t["id"]: t for t in r.json()["items"]}
    assert par_id[b]["dependencies"] == [a]
    assert par_id[a]["dependencies"] == []

    # Au-delà du plafond : refusé proprement, pas tronqué en silence
    assert (await client.get("/api/v1/tasks/?limit=501", headers=auth_headers)).status_code == 422
