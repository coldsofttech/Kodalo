from typing import Any

import pytest
import schemathesis
from hypothesis import HealthCheck, settings
from schemathesis.checks import not_a_server_error

from kodalo.api.main import create_app

app = create_app()
# The app serves no docs, so the contract is published for the test on a route of its own.
app.add_api_route("/openapi.json", lambda: app.openapi(), include_in_schema=False)
schema = schemathesis.openapi.from_asgi("/openapi.json", app)


@pytest.mark.integration
@schema.parametrize()
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_documented_requests_never_cause_server_errors(case: schemathesis.Case[Any]) -> None:
    """Schemathesis generates requests from the OpenAPI document and checks for 5xx responses."""
    case.call_and_validate(checks=[not_a_server_error])
