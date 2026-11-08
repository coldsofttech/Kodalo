from collections.abc import Iterator
from typing import Any
from unittest.mock import patch

import pytest
import schemathesis
from hypothesis import HealthCheck, settings
from schemathesis.core.failures import Failure

from kodalo.api.main import create_app
from kodalo.core.tunnel.errors import TunnelError

app = create_app()
# The app serves no docs, so the contract is published for the test on a route of its own.
app.add_api_route("/openapi.json", lambda: app.openapi(), include_in_schema=False)
schema = schemathesis.openapi.from_asgi("/openapi.json", app)

# Answers that mean a service Kodalo depends on (GitHub, Instagram, the keychain, a download)
# could not help. The routes declare them, so they are part of the contract and not a bug.
UPSTREAM_STATUSES = frozenset({502, 503})


class UnexpectedServerError(Failure):
    """A 5xx answer that is not a declared upstream failure."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(
            operation="response",
            title="Server error",
            message=f"The server answered {status_code}, which is not a declared upstream failure.",
        )


@pytest.fixture(autouse=True)
def no_downloads() -> Iterator[None]:
    """Installing cloudflared would download and install a program on the machine running the
    test, so the install always fails the way it does without a network."""
    with patch(
        "kodalo.core.tunnel.manager.ensure_cloudflared",
        side_effect=TunnelError("cloudflared is not installed."),
    ):
        yield


def only_declared_upstream_errors(ctx: Any, response: Any, case: Any) -> None:
    """Fail on 500 and any 5xx other than 502 and 503, which are the declared upstream answers."""
    if response.status_code >= 500 and response.status_code not in UPSTREAM_STATUSES:
        raise UnexpectedServerError(response.status_code)


@pytest.mark.integration
@schema.parametrize()
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_documented_requests_never_cause_server_errors(case: schemathesis.Case[Any]) -> None:
    """Schemathesis generates requests from the OpenAPI document and checks for 5xx responses."""
    case.call_and_validate(checks=[only_declared_upstream_errors])
