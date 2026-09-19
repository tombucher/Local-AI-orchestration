"""Tests des endpoints projets : CRUD, isolation par utilisateur, archivage."""
import pytest
from httpx import AsyncClient


async def _create_project(client: AsyncClient, headers: dict, name: str = "Projet test") -> dict:
    r = await client.post("/api/v1/projects/", headers=headers, json={
        "name": name,
        "description": "Description de test",
        "type": "personal",
        "features": {"code_gen": True, "veille": False, "git_auto": False},
    })
    assert r.status_code == 201, r.text
    return r.json()


async def test_create_and_get_project(client: AsyncClient, auth_headers: dict):
    project = await _create_project(client, auth_headers)
    assert project["name"] == "Projet test"
    assert project["status"] == "IDEATION"

    r = await client.get(f"/api/v1/projects/{project['id']}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == project["id"]


async def test_list_projects_includes_task_stats(client: AsyncClient, auth_headers: dict):
    await _create_project(client, auth_headers, "A")
    await _create_project(client, auth_headers, "B")
    r = await client.get("/api/v1/projects/", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert {"tasks_total", "tasks_completed"} <= set(body["items"][0].keys())


async def test_update_project(client: AsyncClient, auth_headers: dict):
    project = await _create_project(client, auth_headers)
    r = await client.put(f"/api/v1/projects/{project['id']}", headers=auth_headers,
                         json={"name": "Renommé", "status": "ACTIVE"})
    assert r.status_code == 200
    assert r.json()["name"] == "Renommé"
    assert r.json()["status"] == "ACTIVE"


async def test_archive_project_hides_it_from_list(client: AsyncClient, auth_headers: dict):
    project = await _create_project(client, auth_headers)
    r = await client.delete(f"/api/v1/projects/{project['id']}", headers=auth_headers)
    assert r.status_code == 204
    r = await client.get("/api/v1/projects/", headers=auth_headers)
    assert r.json()["total"] == 0


async def test_project_is_isolated_per_user(client: AsyncClient, auth_headers: dict):
    project = await _create_project(client, auth_headers)

    await client.post("/api/v1/auth/register", json={
        "email": "other@example.com", "password": "Test1234!", "full_name": "Other",
    })
    r = await client.post("/api/v1/auth/login", json={"email": "other@example.com", "password": "Test1234!"})
    other_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = await client.get(f"/api/v1/projects/{project['id']}", headers=other_headers)
    assert r.status_code == 404


async def test_project_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/projects/")
    assert r.status_code == 401


async def test_create_project_validation_error_format(client: AsyncClient, auth_headers: dict):
    r = await client.post("/api/v1/projects/", headers=auth_headers, json={"name": "x"})
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "validation_error"
    assert any(e["field"].endswith("type") for e in body["details"]["errors"])
