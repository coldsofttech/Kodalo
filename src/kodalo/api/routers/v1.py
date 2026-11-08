"""Version 1 of the API, served under ``/api/v1``."""

from fastapi import APIRouter

from kodalo.api.routers import about, brands, repositories, settings, studio

# Cornea has already authenticated the caller by the time a request reaches these routes.
router = APIRouter(tags=["v1"])
router.include_router(repositories.router)
router.include_router(studio.router)
router.include_router(about.router)
router.include_router(brands.router)
router.include_router(settings.router)
