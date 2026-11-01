import json

import pytest
from fastapi.testclient import TestClient

from kodalo.api.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_health_and_ready(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    body = client.get("/ready").json()
    assert body["status"] == "ready"
    assert body["version"]


def test_request_id_is_reused_or_created(client: TestClient) -> None:
    assert client.get("/health", headers={"X-Request-ID": "abc"}).headers["X-Request-ID"] == "abc"
    assert client.get("/health").headers["X-Request-ID"]


def test_security_headers(client: TestClient) -> None:
    response = client.get("/api/v1/palettes")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_hsts_only_over_https() -> None:
    https = TestClient(create_app(), base_url="https://testserver")

    assert "Strict-Transport-Security" in https.get("/health").headers
    assert "Strict-Transport-Security" not in TestClient(create_app()).get("/health").headers


def test_docs_are_never_served(client: TestClient) -> None:
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_oversized_body_is_413(client: TestClient) -> None:
    response = client.post("/api/v1/brands", json={"name": "A" * 1_100_000})

    assert response.status_code == 413


def test_unexpected_errors_do_not_leak_details() -> None:
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret detail")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")

    assert response.status_code == 500
    assert "secret" not in response.text
    assert json.loads(response.text)["title"] == "Internal Server Error"
