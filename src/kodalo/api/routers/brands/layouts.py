"""Layouts: named slide settings brands share."""

from fastapi import APIRouter, Response, status

from kodalo.api.routers.brands.common import (
    LAYOUT_CHANGE_ERRORS,
    LAYOUT_ERRORS,
    LayoutPath,
    Service,
    layout_mapped,
)
from kodalo.api.routers.common import (
    COMMON,
    IMPORT_NAME,
)
from kodalo.api.schemas import (
    LayoutCreate,
    LayoutDuplicate,
    LayoutExport,
    LayoutResponse,
    LayoutUpdate,
)
from kodalo.core.brands.layout import (
    LayoutSettings,
)

router = APIRouter(tags=["v1"])


@router.get("/brands/layouts", summary="List layouts", responses=COMMON)
def list_layouts(service: Service) -> list[LayoutResponse]:
    """Return the built-in layouts first, then the user's, each sorted by name."""
    return [LayoutResponse.from_core(lay) for lay in service.layouts.list_layouts()]


@router.post(
    "/brands/layouts",
    status_code=status.HTTP_201_CREATED,
    summary="Create a layout",
    responses=COMMON | LAYOUT_CHANGE_ERRORS | LAYOUT_ERRORS,
)
def create_layout(body: LayoutCreate, service: Service) -> LayoutResponse:
    """Add a layout that brands can share."""
    with layout_mapped():
        return LayoutResponse.from_core(service.layouts.create(body.name, body.settings))


@router.post(
    "/brands/layouts/import",
    status_code=status.HTTP_201_CREATED,
    summary="Import a layout",
    responses=COMMON | LAYOUT_CHANGE_ERRORS,
)
def import_layout(body: LayoutExport, service: Service, name: IMPORT_NAME = None) -> LayoutResponse:
    """Add a layout from an exported file. Its canvas is matched or created."""
    with layout_mapped():
        layout = service.layouts.import_layout(body.model_dump(mode="json"), name=name)
        return LayoutResponse.from_core(layout)


@router.get("/brands/layouts/{layout_id}", summary="Get a layout", responses=COMMON | LAYOUT_ERRORS)
def get_layout(layout_id: LayoutPath, service: Service) -> LayoutResponse:
    with layout_mapped():
        return LayoutResponse.from_core(service.layouts.get(layout_id))


@router.patch(
    "/brands/layouts/{layout_id}",
    summary="Change a layout",
    responses=COMMON | LAYOUT_CHANGE_ERRORS | LAYOUT_ERRORS,
)
def update_layout(layout_id: LayoutPath, body: LayoutUpdate, service: Service) -> LayoutResponse:
    """Rename a layout or change settings. Every brand that uses it follows the change."""
    changes = body.model_dump(exclude_unset=True, exclude={"name"})
    with layout_mapped():
        current = service.layouts.get(layout_id)
        settings = None
        if changes:
            merged = {k: getattr(current, k) for k in LayoutSettings.model_fields} | changes
            settings = LayoutSettings.model_validate(merged)
        layout = service.layouts.update(layout_id, name=body.name, settings=settings)
        return LayoutResponse.from_core(layout)


@router.post(
    "/brands/layouts/{layout_id}/duplicate",
    status_code=status.HTTP_201_CREATED,
    summary="Copy a layout",
    responses=COMMON | LAYOUT_CHANGE_ERRORS | LAYOUT_ERRORS,
)
def duplicate_layout(
    layout_id: LayoutPath, body: LayoutDuplicate, service: Service
) -> LayoutResponse:
    """Copy any layout, built in or not, as a layout of your own."""
    with layout_mapped():
        return LayoutResponse.from_core(service.layouts.duplicate(layout_id, body.name))


@router.get(
    "/brands/layouts/{layout_id}/export",
    summary="Export a layout",
    responses=COMMON | LAYOUT_ERRORS,
)
def export_layout(layout_id: LayoutPath, service: Service) -> LayoutExport:
    """Return the layout, with its canvas, as a file that `import` accepts."""
    with layout_mapped():
        return LayoutExport.model_validate(service.layouts.export_layout(layout_id))


@router.delete(
    "/brands/layouts/{layout_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a layout",
    responses=COMMON | LAYOUT_CHANGE_ERRORS | LAYOUT_ERRORS,
)
def delete_layout(layout_id: LayoutPath, service: Service) -> Response:
    """Remove a layout that no brand uses."""
    with layout_mapped():
        service.layouts.delete(layout_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
