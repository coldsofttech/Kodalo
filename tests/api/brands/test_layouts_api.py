import pytest
from fastapi.testclient import TestClient

from kodalo.api.main import create_app

LAYOUTS = "/api/v1/brands/layouts"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def add(client: TestClient, name: str = "Mine", **settings: object) -> dict[str, object]:
    response = client.post(LAYOUTS, json={"name": name, "settings": settings})
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


def test_built_in_layouts_have_six_slides(client: TestClient) -> None:
    body = client.get(LAYOUTS).json()
    assert [(lay["name"], lay["type"], lay["slides_count"]) for lay in body] == [
        ("Compact", "system", 6),
        ("Default", "system", 6),
        ("Spacious", "system", 6),
    ]


def test_create_get_update_duplicate_delete(client: TestClient) -> None:
    layout = add(client, slides_count=8, footer_text="@k")
    url = f"{LAYOUTS}/{layout['id']}"
    assert layout["slides_count"] == 8
    assert client.get(url).json() == layout
    changed = client.patch(url, json={"name": "Renamed", "margin_top": 10, "slides_count": 3})
    assert changed.json()["name"] == "Renamed"
    assert (changed.json()["margin_top"], changed.json()["footer_text"]) == (10, "@k")
    assert client.patch(url, json={}).json() == changed.json()
    copy = client.post(f"{url}/duplicate", json={"name": "Copy"})
    assert copy.status_code == 201
    assert client.delete(f"{LAYOUTS}/{copy.json()['id']}").status_code == 204
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404


def test_error_statuses(client: TestClient) -> None:
    layout = add(client)
    assert client.post(LAYOUTS, json={"name": "mine"}).status_code == 409
    bad = client.post(LAYOUTS, json={"name": "x", "settings": {"slides_count": 0}})
    assert bad.status_code == 422
    missing_canvas = client.post(LAYOUTS, json={"name": "y", "settings": {"canvas_id": "nope"}})
    assert missing_canvas.status_code == 422
    built_in = f"{LAYOUTS}/system-default"
    assert client.patch(built_in, json={"name": "x"}).status_code == 403
    assert client.delete(built_in).status_code == 403
    assert client.patch(f"{LAYOUTS}/nope", json={"name": "x"}).status_code == 404
    assert client.patch(f"{LAYOUTS}/{layout['id']}", json={"name": "Default"}).status_code == 409


def test_brand_uses_a_layout_and_blocks_its_deletion(client: TestClient) -> None:
    layout = add(client, slides_count=4)
    brand = client.post("/api/v1/brands", json={"name": "Main"}).json()
    assert brand["layout"]["id"] == "system-default"
    data = brand["data"]
    data["layout_id"] = layout["id"]
    updated = client.patch(f"/api/v1/brands/{brand['id']}", json={"data": data}).json()
    assert updated["layout"]["slides_count"] == 4
    assert client.get(f"{LAYOUTS}/{layout['id']}").json()["used_by"] == ["Main"]
    assert client.delete(f"{LAYOUTS}/{layout['id']}").status_code == 409


def test_export_and_import_with_a_brand_file(client: TestClient) -> None:
    layout = add(client, slides_count=7)
    body = client.get(f"{LAYOUTS}/{layout['id']}/export").json()
    assert (body["format"], body["slides_count"], body["canvas"]["width"]) == (
        "kodalo-layout",
        7,
        1080,
    )
    assert client.post(f"{LAYOUTS}/import", json=body).json()["name"] == "Mine (2)"
    assert client.post(f"{LAYOUTS}/import?name=Other", json=body).json()["name"] == "Other"
    assert client.get(f"{LAYOUTS}/nope/export").status_code == 404
    assert client.post(f"{LAYOUTS}/import", json={**body, "slides_count": 0}).status_code == 422

    brand = client.post("/api/v1/brands", json={"name": "Main"}).json()
    data = brand["data"]
    data["layout_id"] = layout["id"]
    client.patch(f"/api/v1/brands/{brand['id']}", json={"data": data})
    exported = client.get(f"/api/v1/brands/{brand['id']}/export").json()
    assert exported["layout"]["slides_count"] == 7
    imported = client.post("/api/v1/brands/import?name=Copy", json=exported)
    assert imported.status_code == 201
    assert imported.json()["layout"]["id"] == layout["id"]
