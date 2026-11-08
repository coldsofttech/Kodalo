"""Appearance routes: the window theme."""

from fastapi import APIRouter, HTTPException, status

from kodalo.api.routers.common import (
    COMMON,
    INVALID,
    ThemeSetting,
)
from kodalo.api.schemas import (
    ThemeResponse,
    ThemeUpdate,
)
from kodalo.core.settings.appearance import AppearanceInvalidError

router = APIRouter()


@router.get("/settings/theme", summary="Get the window theme", responses=COMMON)
def get_theme(appearance: ThemeSetting) -> ThemeResponse:
    """Return the theme the window uses. The default, system, follows the operating system."""
    return ThemeResponse(theme=appearance.get())


@router.put("/settings/theme", summary="Set the window theme", responses=COMMON | INVALID)
def set_theme(body: ThemeUpdate, appearance: ThemeSetting) -> ThemeResponse:
    """Choose light, dark, or system. Only the window uses it."""
    try:
        return ThemeResponse(theme=appearance.save(body.theme))
    except AppearanceInvalidError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
