import urllib.error
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
def no_outside_world() -> Iterator[None]:
    """Keep the generated requests away from the machine and the network running the test.

    Installing cloudflared would download and install a program, and a missing or signed-out ``gh``,
    ``git`` or ``claude``, or a provider that does not answer, would make each of the hundreds of
    generated requests wait for a timeout. Every outside call fails at once, as it does with no
    program installed and no network, which the routes answer with their declared 502 or 503."""
    unreachable = urllib.error.URLError("No network in the contract test.")
    with (
        patch(
            "kodalo.core.tunnel.manager.ensure_cloudflared",
            side_effect=TunnelError("cloudflared is not installed."),
        ),
        patch("shutil.which", return_value=None),
        patch("urllib.request.urlopen", side_effect=unreachable),
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
