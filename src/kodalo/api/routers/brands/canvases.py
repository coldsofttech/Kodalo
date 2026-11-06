"""Canvases: named slide sizes, and the social platforms they are made for."""

from fastapi import APIRouter, Response, status

from kodalo.api.routers.brands.common import (
    CANVAS_CHANGE_ERRORS,
    CANVAS_ERRORS,
    CanvasPath,
    Service,
    canvas_mapped,
)
from kodalo.api.routers.common import (
    COMMON,
    IMPORT_NAME,
)
from kodalo.api.schemas import (
    CanvasCreate,
    CanvasDuplicate,
    CanvasExport,
    CanvasResponse,
    CanvasUpdate,
    ContrastItem,
    ContrastRequest,
    SocialPlatformResponse,
)
from kodalo.core.brands.brand import (
    check_colors,
)

router = APIRouter(tags=["v1"])


@router.get("/canvases", summary="List canvases", responses=COMMON)
def list_canvases(service: Service) -> list[CanvasResponse]:
    """Return the built-in canvases first, then the user's, each sorted by name."""
    return [CanvasResponse.from_core(c) for c in service.canvases.list_canvases()]


@router.get("/social-platforms", summary="List social platforms", responses=COMMON)
def list_social_platforms(service: Service) -> list[SocialPlatformResponse]:
    """Return the social platforms a canvas can be made for, with the sizes each recommends."""
    return [SocialPlatformResponse.from_core(p) for p in service.canvases.list_platforms()]


@router.post(
    "/canvases",
    status_code=status.HTTP_201_CREATED,
    summary="Create a canvas",
    responses=COMMON | CANVAS_CHANGE_ERRORS | CANVAS_ERRORS,
)
def create_canvas(body: CanvasCreate, service: Service) -> CanvasResponse:
    """Add a slide size that brand layouts can use."""
    with canvas_mapped():
        return CanvasResponse.from_core(
            service.canvases.create(body.name, body.width, body.height, body.platform_id)
        )


@router.post(
    "/canvases/import",
    status_code=status.HTTP_201_CREATED,
    summary="Import a canvas",
    responses=COMMON | CANVAS_CHANGE_ERRORS,
)
def import_canvas(body: CanvasExport, service: Service, name: IMPORT_NAME = None) -> CanvasResponse:
    """Add a canvas from an exported file. A name already in use gets a number added."""
    with canvas_mapped():
        canvas = service.canvases.import_canvas(body.model_dump(mode="json"), name=name)
        return CanvasResponse.from_core(canvas)


@router.get(
    "/canvases/{canvas_id}/export",
    summary="Export a canvas",
    responses=COMMON | CANVAS_ERRORS,
)
def export_canvas(canvas_id: CanvasPath, service: Service) -> CanvasExport:
    """Return the canvas as a file that `import` accepts."""
    with canvas_mapped():
        return CanvasExport.model_validate(service.canvases.export_canvas(canvas_id))


@router.get("/canvases/{canvas_id}", summary="Get a canvas", responses=COMMON | CANVAS_ERRORS)
def get_canvas(canvas_id: CanvasPath, service: Service) -> CanvasResponse:
    with canvas_mapped():
        return CanvasResponse.from_core(service.canvases.get(canvas_id))


@router.patch(
    "/canvases/{canvas_id}",
    summary="Change a canvas",
    responses=COMMON | CANVAS_CHANGE_ERRORS | CANVAS_ERRORS,
)
def update_canvas(canvas_id: CanvasPath, body: CanvasUpdate, service: Service) -> CanvasResponse:
    """Rename or resize a canvas. Every brand that uses it follows the change."""
    with canvas_mapped():
        canvas = service.canvases.update(
            canvas_id,
            name=body.name,
            width=body.width,
            height=body.height,
            platform_id=body.platform_id,
        )
        return CanvasResponse.from_core(canvas)


@router.post(
    "/canvases/{canvas_id}/duplicate",
    status_code=status.HTTP_201_CREATED,
    summary="Copy a canvas",
    responses=COMMON | CANVAS_CHANGE_ERRORS | CANVAS_ERRORS,
)
def duplicate_canvas(
    canvas_id: CanvasPath, body: CanvasDuplicate, service: Service
) -> CanvasResponse:
    """Copy any canvas, built in or not, as a new canvas of your own."""
    with canvas_mapped():
        return CanvasResponse.from_core(service.canvases.duplicate(canvas_id, body.name))


@router.delete(
    "/canvases/{canvas_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a canvas",
    responses=COMMON | CANVAS_CHANGE_ERRORS | CANVAS_ERRORS,
)
def delete_canvas(canvas_id: CanvasPath, service: Service) -> Response:
    """Remove a canvas that no brand uses."""
    with canvas_mapped():
        service.canvases.delete(canvas_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/brands/contrast", summary="Check contrast of colors", responses=COMMON)
def check_contrast(body: ContrastRequest) -> list[ContrastItem]:
    """Check colors that may not be saved yet. Nothing is changed or stored."""
    return [ContrastItem.from_core(r) for r in check_colors(body.colors)]
