import pytest
from fastapi.testclient import TestClient

from kodalo.api.main import create_app

URL = "/api/v1/settings/theme"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_theme_defaults_to_system_and_saves(client: TestClient) -> None:
    assert client.get(URL).json() == {"theme": "system"}
    assert client.put(URL, json={"theme": "dark"}).json() == {"theme": "dark"}
    assert client.get(URL).json() == {"theme": "dark"}
    assert client.put(URL, json={"theme": "blue"}).status_code == 422


@pytest.mark.parametrize("theme", ["light", "dark", "system"])
def test_every_theme_can_be_chosen(client: TestClient, theme: str) -> None:
    assert client.put(URL, json={"theme": theme}).json() == {"theme": theme}
    assert client.get(URL).json() == {"theme": theme}


def test_the_theme_survives_a_new_app() -> None:
    TestClient(create_app()).put(URL, json={"theme": "light"})
    assert TestClient(create_app()).get(URL).json() == {"theme": "light"}


def test_a_rejected_theme_keeps_the_saved_one(client: TestClient) -> None:
    client.put(URL, json={"theme": "dark"})
    assert client.put(URL, json={"theme": "sepia"}).status_code == 422
    assert client.get(URL).json() == {"theme": "dark"}


@pytest.mark.parametrize("body", [{}, {"theme": 1}, {"theme": None}, {"colour": "dark"}])
def test_a_malformed_body_is_refused(client: TestClient, body: dict[str, object]) -> None:
    assert client.put(URL, json=body).status_code == 422
