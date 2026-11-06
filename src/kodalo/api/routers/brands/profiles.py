"""Brand profiles: colors, fonts, logo and layout."""

from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from kodalo.api.routers.brands.common import (
    NAME_TAKEN,
    BrandPath,
    Service,
    brand_mapped,
)
from kodalo.api.routers.common import (
    COMMON,
    INVALID,
    NOT_FOUND,
)
from kodalo.api.schemas import (
    BrandCreate,
    BrandDuplicate,
    BrandExport,
    BrandResponse,
    BrandUpdate,
)

router = APIRouter(tags=["v1"])


@router.get("/brands", summary="List brand profiles", responses=COMMON)
def list_brands(service: Service) -> list[BrandResponse]:
    """Return every profile, sorted by name."""
    return [BrandResponse.from_core(b) for b in service.list_brands()]


@router.post(
    "/brands",
    summary="Create a brand profile",
    status_code=status.HTTP_201_CREATED,
    responses=COMMON | NAME_TAKEN | INVALID,
)
def create_brand(body: BrandCreate, service: Service) -> BrandResponse:
    """Create a profile from a starter palette, or from full data. The first one is the default."""
    with brand_mapped():
        data = body.data if body.data is not None else service.starter(body.palette)
        return BrandResponse.from_core(service.create(body.name, data))


@router.post(
    "/brands/import",
    summary="Import a brand profile",
    status_code=status.HTTP_201_CREATED,
    responses=COMMON | INVALID,
)
def import_brand(
    body: BrandExport,
    service: Service,
    name: Annotated[
        str | None,
        Query(
            min_length=1, max_length=64, description="Name for the profile. Default: the file's."
        ),
    ] = None,
) -> BrandResponse:
    """Add a profile from an exported file. A name already in use gets a number added."""
    with brand_mapped():
        brand = service.import_profile(body.model_dump(mode="json"), name=name)
        return BrandResponse.from_core(brand)


@router.get("/brands/{brand_id}", summary="Get a brand profile", responses=COMMON | NOT_FOUND)
def get_brand(brand_id: BrandPath, service: Service) -> BrandResponse:
    with brand_mapped():
        return BrandResponse.from_core(service.get(brand_id))


@router.patch(
    "/brands/{brand_id}",
    summary="Update a brand profile",
    responses=COMMON | NOT_FOUND | NAME_TAKEN | INVALID,
)
def update_brand(brand_id: BrandPath, body: BrandUpdate, service: Service) -> BrandResponse:
    """Rename a profile and/or replace its brand data. Fields left out are not changed."""
    with brand_mapped():
        brand = service.update(brand_id, name=body.name, data=body.data)
        return BrandResponse.from_core(brand)


@router.delete(
    "/brands/{brand_id}",
    summary="Delete a brand profile",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=COMMON | NOT_FOUND,
)
def delete_brand(brand_id: BrandPath, service: Service) -> Response:
    """Remove a profile and its logo files. If it was the default, another becomes the default."""
    with brand_mapped():
        service.delete(brand_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/brands/{brand_id}/default",
    summary="Make a brand profile the default",
    responses=COMMON | NOT_FOUND,
)
def set_default_brand(brand_id: BrandPath, service: Service) -> BrandResponse:
    with brand_mapped():
        return BrandResponse.from_core(service.set_default(brand_id))


@router.post(
    "/brands/{brand_id}/duplicate",
    summary="Duplicate a brand profile",
    status_code=status.HTTP_201_CREATED,
    responses=COMMON | NOT_FOUND | NAME_TAKEN | INVALID,
)
def duplicate_brand(brand_id: BrandPath, body: BrandDuplicate, service: Service) -> BrandResponse:
    """Copy a profile, including its logo files, under a new name."""
    with brand_mapped():
        return BrandResponse.from_core(service.duplicate(brand_id, body.name))


@router.get(
    "/brands/{brand_id}/export",
    summary="Export a brand profile",
    responses=COMMON | NOT_FOUND,
)
def export_brand(brand_id: BrandPath, service: Service) -> BrandExport:
    """Return the profile and its logos as one file that `import` accepts."""
    with brand_mapped():
        return BrandExport.model_validate(service.export_profile(brand_id))
