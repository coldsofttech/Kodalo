"""Fonts: the catalogue a brand picks from."""

from fastapi import APIRouter

from kodalo.api.routers.brands.common import (
    Service,
)
from kodalo.api.routers.common import (
    COMMON,
)
from kodalo.api.schemas import (
    FontResponse,
)

router = APIRouter(tags=["v1"])


@router.get("/brands/fonts", summary="List fonts", responses=COMMON)
def list_fonts(service: Service) -> list[FontResponse]:
    """Return the font catalogue: bundled fonts first, then fonts installed on this computer."""
    return [FontResponse.from_core(font) for font in service.fonts.list_fonts()]
