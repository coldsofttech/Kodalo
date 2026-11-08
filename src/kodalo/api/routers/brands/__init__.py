"""Brand-related routes: profiles, logos, fonts, layouts, palettes and canvases."""

from fastapi import APIRouter

from kodalo.api.routers.brands import canvases, fonts, layouts, logos, palettes, profiles

# Fonts come before profiles so ``/brands/fonts`` is not read as a profile id.
router = APIRouter(tags=["v1"])
router.include_router(fonts.router)
router.include_router(layouts.router)
router.include_router(palettes.router)
router.include_router(canvases.router)
router.include_router(profiles.router)
router.include_router(logos.router)
