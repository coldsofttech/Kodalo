"""Version 1 of the API, served under ``/api/v1``."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status
from fastapi.concurrency import run_in_threadpool

from kodalo.api.deps import data_dir, get_brand_service, get_github_connectivity
from kodalo.api.schemas import (
    BrandCreate,
    BrandDuplicate,
    BrandExport,
    BrandResponse,
    BrandUpdate,
    CanvasPresetResponse,
    ContrastItem,
    ContrastRequest,
    DoctorCheck,
    DoctorResponse,
    FontResponse,
    GitHubCheckResponse,
    GitHubSettingsResponse,
    GitHubSettingsUpdate,
    PaletteResponse,
)
from kodalo.core.brand import (
    CANVAS_SIZES,
    STARTER_PALETTES,
    BrandError,
    BrandInvalidError,
    BrandNameTakenError,
    BrandNotFoundError,
    BrandService,
    available_fonts,
    check_colors,
    starter_brand,
)
from kodalo.core.brand.logos import MAX_LOGO_BYTES
from kodalo.core.doctor import passed, run_checks
from kodalo.core.github import (
    GitHubConnectivity,
    GitHubInvalidError,
    check_connection,
)

# Cornea has already authenticated the caller by the time a request reaches these routes.
router = APIRouter(tags=["v1"])

Service = Annotated[BrandService, Depends(get_brand_service)]
GitHub = Annotated[GitHubConnectivity, Depends(get_github_connectivity)]
BrandPath = Annotated[str, Path(max_length=64, description="Brand profile id.")]
Variant = Annotated[
    Literal["light", "dark"],
    Query(description="Which logo: the main one, or the one used in dark mode."),
]

LOGO_TYPES = {"image/png": "png", "image/svg+xml": "svg"}
# A logo is only ever shown, never run: no scripts, no outside requests, even if opened directly.
LOGO_CSP = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
LOGO_BODY: dict[str, Any] = {
    "requestBody": {
        "required": True,
        "description": "The logo file, a PNG or an SVG of at most 2 MB.",
        "content": {
            "image/png": {"schema": {"type": "string", "format": "binary"}},
            "image/svg+xml": {"schema": {"type": "string", "format": "binary"}},
        },
    }
}

NOT_FOUND: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"description": "No brand profile has that id."}
}
INVALID: dict[int | str, dict[str, Any]] = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "The brand data or file is not valid."}
}
NAME_TAKEN: dict[int | str, dict[str, Any]] = {
    status.HTTP_409_CONFLICT: {"description": "Another brand profile uses that name."}
}
UNAVAILABLE: dict[int | str, dict[str, Any]] = {
    status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "The local data cannot be opened."}
}
COMMON = UNAVAILABLE


@contextmanager
def _mapped() -> Iterator[None]:
    """Turn the library's brand errors into HTTP errors."""
    try:
        yield
    except BrandNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except BrandNameTakenError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except BrandInvalidError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    except BrandError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.get("/doctor", summary="Diagnose the installation", responses=COMMON)
def doctor() -> DoctorResponse:
    """Run the same checks as `kodalo doctor`: versions, libraries, data folder and database."""
    checks = run_checks(data_dir())
    return DoctorResponse(healthy=passed(checks), checks=[DoctorCheck.from_core(c) for c in checks])


# Settings -----------------------------------------------------------------------------------


@router.get("/settings/github", summary="Get GitHub connectivity", responses=COMMON)
def get_github_settings(github: GitHub) -> GitHubSettingsResponse:
    """Return how Kodalo reaches GitHub. The default is the gh CLI."""
    return GitHubSettingsResponse.from_core(github.get())


@router.put("/settings/github", summary="Set GitHub connectivity", responses=COMMON | INVALID)
def set_github_settings(body: GitHubSettingsUpdate, github: GitHub) -> GitHubSettingsResponse:
    """Choose the way to reach GitHub: a local folder, the gh CLI or the web."""
    try:
        return GitHubSettingsResponse.from_core(github.save(body.mode, body.local_folder))
    except GitHubInvalidError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.post("/settings/github/check", summary="Check GitHub connectivity", responses=COMMON)
def check_github_settings(github: GitHub) -> GitHubCheckResponse:
    """Try the saved way of reaching GitHub once. A failure is reported in the body."""
    return GitHubCheckResponse.from_core(check_connection(github.get()))


# Reference data -----------------------------------------------------------------------------


@router.get("/palettes", summary="List starter palettes", responses=COMMON)
def list_palettes() -> list[PaletteResponse]:
    """Return the starter palettes, each with complete brand data to begin a profile from."""
    return [PaletteResponse.from_core(p, starter_brand(p.key)) for p in STARTER_PALETTES]


@router.get("/fonts", summary="List fonts", responses=COMMON)
def list_fonts() -> list[FontResponse]:
    """Return the bundled fonts first, then the fonts installed on this computer."""
    return [FontResponse.from_core(font) for font in available_fonts()]


@router.get("/canvas-presets", summary="List canvas presets", responses=COMMON)
def list_canvas_presets() -> list[CanvasPresetResponse]:
    """Return the canvas sizes a layout can use. ``custom`` allows any size."""
    return [CanvasPresetResponse(key=k, width=w, height=h) for k, (w, h) in CANVAS_SIZES.items()]


@router.post("/brands/contrast", summary="Check contrast of colors", responses=COMMON)
def check_contrast(body: ContrastRequest) -> list[ContrastItem]:
    """Check colors that may not be saved yet. Nothing is changed or stored."""
    return [ContrastItem.from_core(r) for r in check_colors(body.colors)]


# Profiles -----------------------------------------------------------------------------------


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
    with _mapped():
        if body.data is not None:
            data = body.data
        else:
            try:
                data = starter_brand(body.palette or "midnight")
            except KeyError:
                raise BrandInvalidError(f"Unknown palette: {body.palette}") from None
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
    with _mapped():
        brand = service.import_profile(body.model_dump(mode="json"), name=name)
        return BrandResponse.from_core(brand)


@router.get("/brands/{brand_id}", summary="Get a brand profile", responses=COMMON | NOT_FOUND)
def get_brand(brand_id: BrandPath, service: Service) -> BrandResponse:
    with _mapped():
        return BrandResponse.from_core(service.get(brand_id))


@router.patch(
    "/brands/{brand_id}",
    summary="Update a brand profile",
    responses=COMMON | NOT_FOUND | NAME_TAKEN | INVALID,
)
def update_brand(brand_id: BrandPath, body: BrandUpdate, service: Service) -> BrandResponse:
    """Rename a profile and/or replace its brand data. Fields left out are not changed."""
    with _mapped():
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
    with _mapped():
        service.delete(brand_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/brands/{brand_id}/default",
    summary="Make a brand profile the default",
    responses=COMMON | NOT_FOUND,
)
def set_default_brand(brand_id: BrandPath, service: Service) -> BrandResponse:
    with _mapped():
        return BrandResponse.from_core(service.set_default(brand_id))


@router.post(
    "/brands/{brand_id}/duplicate",
    summary="Duplicate a brand profile",
    status_code=status.HTTP_201_CREATED,
    responses=COMMON | NOT_FOUND | NAME_TAKEN | INVALID,
)
def duplicate_brand(brand_id: BrandPath, body: BrandDuplicate, service: Service) -> BrandResponse:
    """Copy a profile, including its logo files, under a new name."""
    with _mapped():
        return BrandResponse.from_core(service.duplicate(brand_id, body.name))


@router.get(
    "/brands/{brand_id}/export",
    summary="Export a brand profile",
    responses=COMMON | NOT_FOUND,
)
def export_brand(brand_id: BrandPath, service: Service) -> BrandExport:
    """Return the profile and its logos as one file that `import` accepts."""
    with _mapped():
        return BrandExport.model_validate(service.export_profile(brand_id))


# Logos --------------------------------------------------------------------------------------


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
        with _mapped():
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
    with _mapped():
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
    with _mapped():
        return BrandResponse.from_core(service.remove_logo(brand_id, dark=variant == "dark"))
