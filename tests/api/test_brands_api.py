import sqlite3
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from kodalo.api import deps
from kodalo.api.main import create_app

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>'
BRANDS = "/api/v1/brands"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def create(client: TestClient, name: str = "Main", **extra: Any) -> dict[str, Any]:
    response = client.post(BRANDS, json={"name": name, **extra})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def test_create_get_list(client: TestClient) -> None:
    brand = create(client)
    assert brand["is_default"] is True
    assert brand["data"]["colors"]["text"]["light"] == "#111827"
    assert client.get(f"{BRANDS}/{brand['id']}").json() == brand
    assert client.get(BRANDS).json() == [brand]


def test_create_from_palette_or_data(client: TestClient) -> None:
    paper = create(client, "Paper", palette="paper")
    assert paper["data"]["colors"]["background"]["light"] == "#faf7f2"
    copy = create(client, "Copy", data=paper["data"])
    assert copy["data"] == paper["data"]
    assert copy["is_default"] is False


def test_create_errors(client: TestClient) -> None:
    create(client)
    assert client.post(BRANDS, json={"name": "main"}).status_code == 409
    assert client.post(BRANDS, json={"name": "x", "palette": "neon"}).status_code == 422
    assert client.post(BRANDS, json={"name": "   "}).status_code == 422
    both = {"name": "y", "palette": "paper", "data": create(client, "Z")["data"]}
    assert client.post(BRANDS, json=both).status_code == 422
    assert client.post(BRANDS, json={"name": "y", "extra": 1}).status_code in (200, 201, 422)


def test_errors_are_problem_json(client: TestClient) -> None:
    response = client.get(f"{BRANDS}/nope")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "That brand does not exist."


def test_update_name_and_data(client: TestClient) -> None:
    brand = create(client)
    data = brand["data"]
    data["layout"]["footer_text"] = "@kodalo"
    updated = client.patch(f"{BRANDS}/{brand['id']}", json={"name": "Renamed", "data": data})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed"
    assert updated.json()["data"]["layout"]["footer_text"] == "@kodalo"
    unchanged = client.patch(f"{BRANDS}/{brand['id']}", json={})
    assert unchanged.json()["name"] == "Renamed"


def test_update_rejects_bad_data(client: TestClient) -> None:
    brand = create(client)
    brand["data"]["colors"]["text"]["light"] = "red"
    response = client.patch(f"{BRANDS}/{brand['id']}", json={"data": brand["data"]})
    assert response.status_code == 422
    assert response.json()["errors"]
    create(client, "Other")
    assert client.patch(f"{BRANDS}/{brand['id']}", json={"name": "other"}).status_code == 409


def test_unknown_ids_are_404(client: TestClient) -> None:
    for response in (
        client.get(f"{BRANDS}/x"),
        client.patch(f"{BRANDS}/x", json={"name": "a"}),
        client.delete(f"{BRANDS}/x"),
        client.post(f"{BRANDS}/x/default"),
        client.post(f"{BRANDS}/x/duplicate", json={"name": "a"}),
        client.get(f"{BRANDS}/x/export"),
        client.put(f"{BRANDS}/x/logo", content=PNG, headers={"Content-Type": "image/png"}),
        client.get(f"{BRANDS}/x/logo"),
        client.delete(f"{BRANDS}/x/logo"),
    ):
        assert response.status_code == 404


def test_default_duplicate_delete(client: TestClient) -> None:
    first = create(client, "A")
    second = create(client, "B")
    assert client.post(f"{BRANDS}/{second['id']}/default").json()["is_default"] is True
    assert client.get(f"{BRANDS}/{first['id']}").json()["is_default"] is False
    copy = client.post(f"{BRANDS}/{first['id']}/duplicate", json={"name": "A copy"})
    assert copy.status_code == 201
    assert client.post(f"{BRANDS}/{first['id']}/duplicate", json={"name": "a"}).status_code == 409
    assert client.delete(f"{BRANDS}/{second['id']}").status_code == 204
    names = {b["name"]: b["is_default"] for b in client.get(BRANDS).json()}
    assert sorted(names) == ["A", "A copy"]
    assert list(names.values()).count(True) == 1


def test_logo_lifecycle(client: TestClient) -> None:
    brand = create(client)
    url = f"{BRANDS}/{brand['id']}/logo"
    assert client.get(url).status_code == 404

    stored = client.put(url, content=SVG, headers={"Content-Type": "image/svg+xml"})
    assert stored.status_code == 200
    assert stored.json()["data"]["logo"]["file"].endswith(".svg")
    shown = client.get(url)
    assert shown.headers["content-type"] == "image/svg+xml"
    assert shown.content == SVG
    assert shown.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in shown.headers["content-security-policy"]

    dark = client.put(
        url, params={"variant": "dark"}, content=PNG, headers={"Content-Type": "image/png"}
    )
    assert dark.json()["data"]["logo"]["dark_file"].endswith(".png")
    assert client.get(url, params={"variant": "dark"}).content == PNG

    assert (
        client.delete(url, params={"variant": "dark"}).json()["data"]["logo"]["dark_file"] is None
    )
    assert client.get(url, params={"variant": "dark"}).status_code == 404


def test_logo_upload_checks(client: TestClient) -> None:
    url = f"{BRANDS}/{create(client)['id']}/logo"
    assert client.put(url, content=PNG).status_code == 415
    assert client.put(url, content=PNG, headers={"Content-Type": "text/plain"}).status_code == 415
    scripted = b"<svg><script>alert(1)</script></svg>"
    rejected = client.put(url, content=scripted, headers={"Content-Type": "image/svg+xml"})
    assert rejected.status_code == 422
    assert "not allowed" in rejected.json()["detail"]
    assert client.get(url).status_code == 404
    assert client.put(url, params={"variant": "blue"}, content=PNG).status_code == 422


def test_logo_size_limit(client: TestClient) -> None:
    url = f"{BRANDS}/{create(client)['id']}/logo"
    headers = {"Content-Type": "image/png"}
    too_big = PNG + b"\x00" * (2 * 1024 * 1024)
    assert client.put(url, content=too_big, headers=headers).status_code == 413
    # Without a declared length the handler still stops reading at the limit.
    chunks = (b"\x00" * 65536 for _ in range(40))
    assert client.put(url, content=chunks, headers=headers).status_code == 413


def test_logos_may_exceed_the_general_body_limit(client: TestClient) -> None:
    brand = create(client)
    url = f"{BRANDS}/{brand['id']}/logo"
    large_png = PNG + bytes(1_500_000)  # above the 1 MiB general limit, below the 2 MB logo limit
    stored = client.put(url, content=large_png, headers={"Content-Type": "image/png"})
    assert stored.status_code == 200
    assert client.post(BRANDS, json={"name": "x" * 1_100_000}).status_code == 413


def test_export_import_round_trip(client: TestClient) -> None:
    brand = create(client)
    url = f"{BRANDS}/{brand['id']}"
    client.put(f"{url}/logo", content=PNG, headers={"Content-Type": "image/png"})
    exported = client.get(f"{url}/export")
    assert exported.status_code == 200
    document = exported.json()
    assert document["format"] == "kodalo-brand"
    assert len(document["logos"]) == 1

    imported = client.post(f"{BRANDS}/import", json=document)
    assert imported.status_code == 201
    assert imported.json()["name"] == "Main (2)"
    new_logo = f"{BRANDS}/{imported.json()['id']}/logo"
    assert client.get(new_logo).content == PNG
    renamed = client.post(f"{BRANDS}/import", params={"name": "Fresh"}, json=document)
    assert renamed.json()["name"] == "Fresh"


def test_import_rejects_bad_files(client: TestClient) -> None:
    document = client.get(f"{BRANDS}/{create(client)['id']}/export").json()
    assert client.post(f"{BRANDS}/import", json={**document, "format": "x"}).status_code == 422
    broken = {**document, "data": {**document["data"], "schema_version": 2}}
    assert client.post(f"{BRANDS}/import", json=broken).status_code == 422
    scripted = {
        **document,
        "data": {**document["data"], "logo": {**document["data"]["logo"], "file": "a.svg"}},
        "logos": {"a.svg": {"content_base64": "PHN2Zz48c2NyaXB0Lz48L3N2Zz4="}},
    }
    assert client.post(f"{BRANDS}/import", json=scripted).status_code == 422
    assert len(client.get(BRANDS).json()) == 1


def test_contrast(client: TestClient) -> None:
    colors = create(client)["data"]["colors"]
    ok = client.post(f"{BRANDS}/contrast", json={"colors": colors})
    assert ok.status_code == 200
    assert len(ok.json()) == 12
    assert all(item["passes"] for item in ok.json())
    colors["text"]["light"] = "#eeeeee"
    failing = client.post(f"{BRANDS}/contrast", json={"colors": colors}).json()
    assert [(i["color"], i["mode"]) for i in failing if not i["passes"]] == [("text", "light")]
    assert client.post(f"{BRANDS}/contrast", json={"colors": {}}).status_code == 422


def test_reference_data(client: TestClient) -> None:
    palettes = client.get("/api/v1/palettes").json()
    assert [p["key"] for p in palettes] == ["midnight", "paper", "graphite"]
    assert palettes[0]["data"]["fonts"]["body"]["family"] == "Inter"
    fonts = client.get("/api/v1/fonts").json()
    assert fonts[0] == {"family": "Inter", "category": "sans", "source": "bundled"}
    presets = {
        p["key"]: (p["width"], p["height"]) for p in client.get("/api/v1/canvas-presets").json()
    }
    assert presets["instagram_portrait"] == (1080, 1350)


def test_doctor(client: TestClient) -> None:
    create(client)
    body = client.get("/api/v1/doctor").json()
    assert body["healthy"] is True
    details = {c["name"]: c["detail"] for c in body["checks"]}
    assert details["Brand profiles"] == "1 (default: Main)"
    assert {"name", "ok", "detail", "required"} == set(body["checks"][0])


def test_data_survives_a_restart(client: TestClient) -> None:
    created = create(client)
    deps.reset_services()
    assert TestClient(create_app()).get(f"{BRANDS}/{created['id']}").json() == created


def test_storage_failure_is_503_with_a_safe_message(tmp_path: Path) -> None:
    data_dir = tmp_path / "newer"
    deps.configure(data_dir)
    create(TestClient(create_app()))
    with sqlite3.connect(data_dir / "kodalo.db") as connection:
        connection.execute("UPDATE schema_migrations SET version_num = '9999'")
    deps.reset_services()

    response = TestClient(create_app()).get(BRANDS)

    assert response.status_code == 503
    assert "newer version" in response.json()["detail"]
    assert "9999" not in response.text
