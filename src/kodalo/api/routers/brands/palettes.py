"""Palettes: named sets of the eight brand colors."""

from fastapi import APIRouter, Response, status

from kodalo.api.routers.brands.common import (
    PALETTE_CHANGE_ERRORS,
    PALETTE_ERRORS,
    PalettePath,
    Service,
    palette_mapped,
)
from kodalo.api.routers.common import (
    AI_UNREACHABLE,
    COMMON,
    IMPORT_NAME,
    INVALID,
    AiSetting,
    ai_errors,
)
from kodalo.api.schemas import (
    PaletteCreate,
    PaletteDuplicate,
    PaletteExport,
    PaletteResponse,
    PaletteSuggestion,
    PaletteSuggestionPlan,
    PaletteUpdate,
)
from kodalo.core.brands.brand import (
    BrandService,
)
from kodalo.core.brands.palette import (
    Palette,
)
from kodalo.core.brands.palette.suggest import PaletteSuggester

router = APIRouter(tags=["v1"])


def _palette_response(service: BrandService, palette: Palette) -> PaletteResponse:
    return PaletteResponse.from_core(palette, service.starter(palette.id))


@router.get("/palettes", summary="List palettes", responses=COMMON)
def list_palettes(service: Service) -> list[PaletteResponse]:
    """Return the built-in palettes first, then the user's, each with brand data to start from."""
    return [_palette_response(service, p) for p in service.palettes.list_palettes()]


@router.post(
    "/palettes/suggest/plan",
    summary="Plan the AI palette suggestion",
    responses={**COMMON, **AI_UNREACHABLE},
)
def plan_palette_suggestion(service: Service, ai: AiSetting) -> PaletteSuggestionPlan:
    """Estimate what asking the default AI model for a palette would send and cost. Nothing is
    sent."""
    with ai_errors():
        return PaletteSuggestionPlan.from_core(PaletteSuggester(service.palettes, ai).plan())


@router.post(
    "/palettes/suggest",
    summary="Suggest a palette with AI",
    responses={**COMMON, **INVALID, **AI_UNREACHABLE},
)
def suggest_palette(service: Service, ai: AiSetting) -> PaletteSuggestion:
    """Ask the default AI model for a new palette that differs from the existing ones. Nothing is
    saved."""
    with ai_errors():
        name, colors = PaletteSuggester(service.palettes, ai).suggest()
    return PaletteSuggestion.model_validate({"name": name, "colors": colors.model_dump()})


@router.post(
    "/palettes",
    status_code=status.HTTP_201_CREATED,
    summary="Create a palette",
    responses=COMMON | PALETTE_CHANGE_ERRORS | PALETTE_ERRORS,
)
def create_palette(body: PaletteCreate, service: Service) -> PaletteResponse:
    """Add a palette of your own, for example from the colors of a brand."""
    with palette_mapped():
        return _palette_response(service, service.palettes.create(body.name, body.colors))


@router.post(
    "/palettes/import",
    status_code=status.HTTP_201_CREATED,
    summary="Import a palette",
    responses=COMMON | PALETTE_CHANGE_ERRORS,
)
def import_palette(
    body: PaletteExport, service: Service, name: IMPORT_NAME = None
) -> PaletteResponse:
    """Add a palette from an exported file. A name already in use gets a number added."""
    with palette_mapped():
        palette = service.palettes.import_palette(body.model_dump(mode="json"), name=name)
        return _palette_response(service, palette)


@router.get("/palettes/{palette_id}", summary="Get a palette", responses=COMMON | PALETTE_ERRORS)
def get_palette_by_id(palette_id: PalettePath, service: Service) -> PaletteResponse:
    with palette_mapped():
        return _palette_response(service, service.palettes.get(palette_id))


@router.patch(
    "/palettes/{palette_id}",
    summary="Change a palette",
    responses=COMMON | PALETTE_CHANGE_ERRORS | PALETTE_ERRORS,
)
def update_palette(
    palette_id: PalettePath, body: PaletteUpdate, service: Service
) -> PaletteResponse:
    """Rename a palette or replace its colors. Brands made from it keep their colors."""
    with palette_mapped():
        palette = service.palettes.update(palette_id, name=body.name, colors=body.colors)
        return _palette_response(service, palette)


@router.post(
    "/palettes/{palette_id}/duplicate",
    status_code=status.HTTP_201_CREATED,
    summary="Copy a palette",
    responses=COMMON | PALETTE_CHANGE_ERRORS | PALETTE_ERRORS,
)
def duplicate_palette(
    palette_id: PalettePath, body: PaletteDuplicate, service: Service
) -> PaletteResponse:
    """Copy any palette, built in or not, as a palette of your own."""
    with palette_mapped():
        palette = service.palettes.duplicate(palette_id, body.name)
        return _palette_response(service, palette)


@router.get(
    "/palettes/{palette_id}/export",
    summary="Export a palette",
    responses=COMMON | PALETTE_ERRORS,
)
def export_palette(palette_id: PalettePath, service: Service) -> PaletteExport:
    """Return the palette as a file that `import` accepts."""
    with palette_mapped():
        return PaletteExport.model_validate(service.palettes.export_palette(palette_id))


@router.delete(
    "/palettes/{palette_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a palette",
    responses=COMMON | PALETTE_CHANGE_ERRORS | PALETTE_ERRORS,
)
def delete_palette(palette_id: PalettePath, service: Service) -> Response:
    """Remove a palette of your own. Brands made from it keep their colors."""
    with palette_mapped():
        service.palettes.delete(palette_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
