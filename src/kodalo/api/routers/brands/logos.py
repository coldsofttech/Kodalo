"""Brand logo files."""

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool

from kodalo.api.routers.brands.common import (
    LOGO_BODY,
    LOGO_CSP,
    LOGO_TYPES,
    BrandPath,
    Service,
    Variant,
    brand_mapped,
)
from kodalo.api.routers.common import (
    COMMON,
    INVALID,
    NOT_FOUND,
)
from kodalo.api.schemas import (
    BrandResponse,
)
from kodalo.core.brands.brand.logos import MAX_LOGO_BYTES

router = APIRouter(tags=["v1"])


@router.put(
    "/brands/{brand_id}/logo",
    summary="Set a logo",
    responses=COMMON
    | NOT_FOUND
    | INVALID
    | {
        status.HTTP_413_CONTENT_TOO_LARGE: {"description": "The file is larger than 2 MB."},
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {"description": "Send image/png or image/svg+xml."},
    },
    openapi_extra=LOGO_BODY,
)
async def set_logo(
    brand_id: BrandPath, request: Request, service: Service, variant: Variant = "light"
) -> BrandResponse:
    """Store the request body as the profile's logo. SVG files with scripts are refused."""
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type not in LOGO_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Send the logo as image/png or image/svg+xml."
        )
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_LOGO_BYTES:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "The logo is larger than 2 MB.")

    def store() -> BrandResponse:
        with brand_mapped():
            return BrandResponse.from_core(
                service.set_logo(brand_id, bytes(body), dark=variant == "dark")
            )

    return await run_in_threadpool(store)


@router.get(
    "/brands/{brand_id}/logo",
    summary="Get a logo",
    response_class=Response,
    responses=COMMON
    | NOT_FOUND
    | {
        status.HTTP_200_OK: {
            "description": "The logo file.",
            "content": {"image/png": {}, "image/svg+xml": {}},
        }
    },
)
def get_logo(brand_id: BrandPath, service: Service, variant: Variant = "light") -> Response:
    """Return the logo file, safe to show in an image tag. 404 if the profile has none."""
    with brand_mapped():
        logo = service.get(brand_id).data.logo
        name = logo.dark_file if variant == "dark" else logo.file
        if name is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "This brand has no such logo.")
        content = service.logos.read(name)
    media_type = "image/png" if name.endswith(".png") else "image/svg+xml"
    return Response(
        content,
        media_type=media_type,
        headers={"Content-Security-Policy": LOGO_CSP, "X-Content-Type-Options": "nosniff"},
    )


@router.delete(
    "/brands/{brand_id}/logo",
    summary="Remove a logo",
    responses=COMMON | NOT_FOUND,
)
def remove_logo(brand_id: BrandPath, service: Service, variant: Variant = "light") -> BrandResponse:
    with brand_mapped():
        return BrandResponse.from_core(service.remove_logo(brand_id, dark=variant == "dark"))
