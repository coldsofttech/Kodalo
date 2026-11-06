"""Aliases, error maps and error mapping shared by the brand routers."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Annotated, Any, Literal

from fastapi import Depends, HTTPException, Path, Query, status

from kodalo.api.deps import (
    get_brand_service,
)
from kodalo.core.brands.brand import (
    BrandError,
    BrandInvalidError,
    BrandNameTakenError,
    BrandNotFoundError,
    BrandService,
)
from kodalo.core.brands.canvas import (
    CanvasError,
    CanvasInUseError,
    CanvasNameTakenError,
    CanvasNotFoundError,
    CanvasReadOnlyError,
)
from kodalo.core.brands.layout import (
    LayoutError,
    LayoutInUseError,
    LayoutNameTakenError,
    LayoutNotFoundError,
    LayoutReadOnlyError,
)
from kodalo.core.brands.palette import (
    PaletteError,
    PaletteInvalidError,
    PaletteNameTakenError,
    PaletteNotFoundError,
    PaletteReadOnlyError,
)

Service = Annotated[BrandService, Depends(get_brand_service)]
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

NAME_TAKEN: dict[int | str, dict[str, Any]] = {
    status.HTTP_409_CONFLICT: {"description": "Another brand profile uses that name."}
}


@contextmanager
def brand_mapped() -> Generator[None]:
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


LayoutPath = Annotated[str, Path(max_length=64, description="Layout id.")]
LAYOUT_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"description": "No layout has that id."},
    status.HTTP_409_CONFLICT: {"description": "The name is taken, or brands still use the layout."},
}
LAYOUT_CHANGE_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_403_FORBIDDEN: {"description": "The layout is built in and cannot be changed."},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "The name or settings are not valid."},
}
PalettePath = Annotated[str, Path(max_length=64, description="Palette id.")]
PALETTE_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"description": "No palette has that id."},
    status.HTTP_409_CONFLICT: {"description": "Another palette uses that name."},
}
PALETTE_CHANGE_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_403_FORBIDDEN: {"description": "The palette is built in and cannot be changed."},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "The name or colors are not valid."},
}

CanvasPath = Annotated[str, Path(max_length=64, description="Canvas id.")]
CANVAS_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"description": "No canvas has that id."},
    status.HTTP_409_CONFLICT: {"description": "The name is taken, or brands still use the canvas."},
}
CANVAS_CHANGE_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_403_FORBIDDEN: {"description": "The canvas is built in and cannot be changed."},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "The name or size is not valid."},
}


@contextmanager
def layout_mapped() -> Generator[None]:
    """Turn the library's layout errors into HTTP errors."""
    try:
        yield
    except LayoutNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except (LayoutNameTakenError, LayoutInUseError) as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except LayoutReadOnlyError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
    except LayoutError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@contextmanager
def palette_mapped() -> Generator[None]:
    """Turn the library's palette errors into HTTP errors."""
    try:
        yield
    except PaletteNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except PaletteNameTakenError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except PaletteReadOnlyError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
    except (PaletteInvalidError, PaletteError, BrandInvalidError) as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@contextmanager
def canvas_mapped() -> Generator[None]:
    """Turn the library's canvas errors into HTTP errors."""
    try:
        yield
    except CanvasNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except (CanvasNameTakenError, CanvasInUseError) as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except CanvasReadOnlyError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
    except CanvasError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
