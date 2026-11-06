from typing import Any

import pytest
from fastapi.testclient import TestClient

from kodalo.api.main import create_app

PALETTES = "/api/v1/palettes"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def colors(client: TestClient) -> dict[str, Any]:
    body: dict[str, Any] = client.get(f"{PALETTES}/system-midnight").json()["colors"]
    return body


def add(client: TestClient, name: str = "Ocean") -> dict[str, Any]:
    response = client.post(PALETTES, json={"name": name, "colors": colors(client)})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def test_built_in_palettes_come_with_brand_data(client: TestClient) -> None:
    body = client.get(PALETTES).json()
    assert [(p["name"], p["type"]) for p in body] == [
        ("Graphite", "system"),
        ("Midnight", "system"),
        ("Paper", "system"),
    ]
    assert body[1]["data"]["colors"] == body[1]["colors"]
    assert body[1]["data"]["fonts"]["body"]["family"] == "Inter"


def test_create_get_update_duplicate_delete(client: TestClient) -> None:
    palette = add(client)
    url = f"{PALETTES}/{palette['id']}"
    assert client.get(url).json() == palette
    changed = colors(client)
    changed["primary"]["light"] = "#123456"
    updated = client.patch(url, json={"name": "Sea", "colors": changed}).json()
    assert (updated["name"], updated["colors"]["primary"]["light"]) == ("Sea", "#123456")
    assert client.patch(url, json={}).json() == updated
    copy = client.post(f"{url}/duplicate", json={"name": "Copy"})
    assert copy.status_code == 201
    assert client.delete(f"{PALETTES}/{copy.json()['id']}").status_code == 204
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404


def test_error_statuses(client: TestClient) -> None:
    add(client)
    assert (
        client.post(PALETTES, json={"name": "ocean", "colors": colors(client)}).status_code == 409
    )
    assert client.post(PALETTES, json={"name": "x", "colors": {}}).status_code == 422
    built_in = f"{PALETTES}/system-paper"
    assert client.patch(built_in, json={"name": "x"}).status_code == 403
    assert client.delete(built_in).status_code == 403
    assert client.patch(f"{PALETTES}/nope", json={"name": "x"}).status_code == 404


def test_export_and_import(client: TestClient) -> None:
    body = client.get(f"{PALETTES}/system-paper/export").json()
    assert (body["format"], body["name"]) == ("kodalo-palette", "Paper")
    assert client.post(f"{PALETTES}/import", json=body).json()["name"] == "Paper (2)"
    assert client.post(f"{PALETTES}/import?name=Other", json=body).json()["name"] == "Other"
    assert client.get(f"{PALETTES}/nope/export").status_code == 404
    assert client.post(f"{PALETTES}/import", json={**body, "colors": {}}).status_code == 422


def test_a_brand_starts_from_a_palette_by_name(client: TestClient) -> None:
    add(client)
    sea = client.post("/api/v1/brands", json={"name": "A", "palette": "ocean"})
    assert sea.status_code == 201
    assert client.post("/api/v1/brands", json={"name": "B", "palette": "neon"}).status_code == 422
