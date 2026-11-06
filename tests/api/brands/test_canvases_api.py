import pytest
from fastapi.testclient import TestClient

from kodalo.api.main import create_app

CANVASES = "/api/v1/canvases"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def add(client: TestClient, name: str = "Feed") -> dict[str, object]:
    response = client.post(CANVASES, json={"name": name, "width": 1080, "height": 1350})
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


def test_list_starts_with_built_in_canvases(client: TestClient) -> None:
    body = client.get(CANVASES).json()
    assert [c["type"] for c in body] == ["system"] * 5
    assert body[0]["used_by"] == ["Compact", "Default", "Spacious"]
    assert body[-1]["used_by"] == []


def test_create_get_update_duplicate_delete(client: TestClient) -> None:
    canvas = add(client)
    url = f"{CANVASES}/{canvas['id']}"
    assert client.get(url).json() == canvas
    assert client.patch(url, json={"width": 900}).json()["width"] == 900
    copy = client.post(f"{url}/duplicate", json={"name": "Copy"})
    assert copy.status_code == 201
    assert client.delete(f"{CANVASES}/{copy.json()['id']}").status_code == 204
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404


def test_error_statuses(client: TestClient) -> None:
    canvas = add(client)
    taken = {"name": "feed", "width": 500, "height": 500}
    assert client.post(CANVASES, json=taken).status_code == 409
    tiny = {"name": "Tiny", "width": 10, "height": 500}
    assert client.post(CANVASES, json=tiny).status_code == 422
    built_in = f"{CANVASES}/system-instagram_story"
    assert client.patch(built_in, json={"name": "x"}).status_code == 403
    assert client.delete(built_in).status_code == 403
    assert client.patch(f"{CANVASES}/nope", json={"name": "x"}).status_code == 404
    clash = {"name": "Instagram story"}
    assert client.patch(f"{CANVASES}/{canvas['id']}", json=clash).status_code == 409


def test_layout_uses_a_canvas_and_blocks_its_deletion(client: TestClient) -> None:
    canvas = add(client)
    layout = client.post(
        "/api/v1/layouts",
        json={"name": "Feed layout", "settings": {"canvas_id": canvas["id"]}},
    ).json()
    brand = client.post("/api/v1/brands", json={"name": "Main"}).json()
    data = brand["data"]
    data["layout_id"] = layout["id"]
    url = f"/api/v1/brands/{brand['id']}"
    updated = client.patch(url, json={"data": data}).json()
    assert updated["canvas"]["name"] == "Feed"
    assert updated["layout"]["name"] == "Feed layout"
    assert client.get(f"{CANVASES}/{canvas['id']}").json()["used_by"] == ["Feed layout"]
    assert client.delete(f"{CANVASES}/{canvas['id']}").status_code == 409
    data["layout_id"] = "missing"
    assert client.patch(url, json={"data": data}).status_code == 422


def test_export_and_import(client: TestClient) -> None:
    canvas = add(client)
    exported = client.get(f"{CANVASES}/{canvas['id']}/export")
    assert exported.status_code == 200
    body = exported.json()
    assert (body["format"], body["name"], body["width"]) == ("kodalo-canvas", "Feed", 1080)
    copy = client.post(f"{CANVASES}/import", json=body)
    assert copy.status_code == 201
    assert copy.json()["name"] == "Feed (2)"
    named = client.post(f"{CANVASES}/import?name=Other", json=body)
    assert named.json()["name"] == "Other"
    assert client.get(f"{CANVASES}/nope/export").status_code == 404
    assert client.post(f"{CANVASES}/import", json={**body, "width": 5}).status_code == 422
