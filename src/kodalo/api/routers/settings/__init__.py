"""Settings routes: appearance, GitHub, AI and platforms."""

from fastapi import APIRouter

from kodalo.api.routers.settings import ai, appearance, github, platforms

router = APIRouter()
router.include_router(github.router)
router.include_router(ai.router)
router.include_router(appearance.router)
router.include_router(platforms.router)
