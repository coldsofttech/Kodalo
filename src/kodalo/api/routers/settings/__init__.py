"""Settings routes: appearance, GitHub and AI."""

from fastapi import APIRouter

from kodalo.api.routers.settings import ai, appearance, github

router = APIRouter()
router.include_router(github.router)
router.include_router(ai.router)
router.include_router(appearance.router)
