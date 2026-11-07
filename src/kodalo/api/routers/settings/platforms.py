"""Platform routes: how many hashtags a post gets and which ones every post carries."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Path, status

from kodalo.api.routers.common import COMMON, INVALID, PlatformSettings
from kodalo.api.schemas import PlatformSettingsResponse, PlatformSettingsUpdate
from kodalo.core.settings.platforms import PlatformInvalidError

router = APIRouter()

PlatformName = Annotated[
    Literal["instagram"], Path(description="The social platform.", examples=["instagram"])
]


@router.get("/settings/platforms/{platform}", summary="Get a platform's settings", responses=COMMON)
def get_platform(platform: PlatformName, platforms: PlatformSettings) -> PlatformSettingsResponse:
    """Return how many hashtags a post for this platform gets and the ones every post carries."""
    return PlatformSettingsResponse.from_core(platforms.get(platform))


@router.put(
    "/settings/platforms/{platform}",
    summary="Set a platform's settings",
    responses=COMMON | INVALID,
)
def set_platform(
    platform: PlatformName, body: PlatformSettingsUpdate, platforms: PlatformSettings
) -> PlatformSettingsResponse:
    """Choose the number of hashtags (the default ones included), the default hashtags and the
    visuals the designer may use. The post copywriter uses the hashtag settings."""
    try:
        return PlatformSettingsResponse.from_core(
            platforms.save(
                platform,
                body.hashtag_count,
                body.default_hashtags,
                use_social_preview=body.use_social_preview,
                use_repo_icon=body.use_repo_icon,
                use_icons=body.use_icons,
                build_custom_images=body.build_custom_images,
                use_ai_templates=body.use_ai_templates,
            )
        )
    except PlatformInvalidError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
