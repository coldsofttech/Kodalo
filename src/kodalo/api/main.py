"""Application factory."""

from fastapi import FastAPI

from kodalo.api.errors import register_error_handlers
from kodalo.api.logs import RequestIdMiddleware, configure_logging
from kodalo.api.routers import health, v1
from kodalo.api.security import BodyLimitMiddleware, SecurityHeadersMiddleware
from kodalo.core import __version__


def create_app(*, embedded: bool = False) -> FastAPI:
    """Build the application. Tests call this to get a fresh app.

    The API is only used by the Kodalo window, which hosts it under Cornea. Cornea authenticates
    every request and sets strict response headers, so ``embedded=True`` leaves out this app's
    own headers. Interactive docs are never served; the contract is ``docs/openapi.json``.
    """
    configure_logging("info")

    app = FastAPI(
        title="kodalo-api",
        version=__version__,
        description="HTTP API for Kodalo brand profiles, built on **kodalo.core**.",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    # Middleware added last runs first, so the order below reads from innermost to outermost:
    # body limit, security headers, request ID.
    app.add_middleware(BodyLimitMiddleware)
    if not embedded:
        app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(v1.router, prefix="/api/v1")
    return app
