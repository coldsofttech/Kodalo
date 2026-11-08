"""Platform routes: how many hashtags a post gets and which ones every post carries."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Path, status

from kodalo.api.routers.common import (
    AI_UNREACHABLE,
    COMMON,
    INVALID,
    InstagramPost,
    InstagramSetting,
    PlatformSettings,
)
from kodalo.api.schemas import (
    InstagramAccountResponse,
    InstagramConnectRequest,
    PlatformSettingsResponse,
    PlatformSettingsUpdate,
    TunnelStatusResponse,
)
from kodalo.core.settings.platforms import (
    PlatformConnectionError,
    PlatformInvalidError,
    PlatformSecretError,
)
from kodalo.core.tunnel import TunnelError

router = APIRouter()

NOT_CONNECTED = {status.HTTP_404_NOT_FOUND: {"description": "Instagram is not connected."}}

PlatformName = Annotated[
    Literal["instagram", "custom"],
    Path(description="The social platform.", examples=["instagram"]),
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


@router.get(
    "/settings/platforms/instagram/connection",
    summary="Get the Instagram connection",
    responses=COMMON,
)
def get_instagram(instagram: InstagramSetting) -> InstagramAccountResponse:
    """Return the connected Instagram account, or that none is connected. Never the token."""
    return InstagramAccountResponse.from_core(instagram.get())


@router.put(
    "/settings/platforms/instagram/connection",
    summary="Connect Instagram",
    responses=COMMON | INVALID | AI_UNREACHABLE,
)
def connect_instagram(
    body: InstagramConnectRequest, instagram: InstagramSetting
) -> InstagramAccountResponse:
    """Check the access token with Instagram and keep it in the system keychain. Nothing is kept
    when Instagram refuses it (502) or the keychain is unavailable (503)."""
    try:
        return InstagramAccountResponse.from_core(
            instagram.connect(body.access_token, body.account_id)
        )
    except PlatformInvalidError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    except PlatformConnectionError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    except PlatformSecretError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


@router.post(
    "/settings/platforms/instagram/connection/check",
    summary="Check the Instagram connection",
    responses=COMMON | NOT_CONNECTED | AI_UNREACHABLE,
)
def check_instagram(instagram: InstagramSetting) -> InstagramAccountResponse:
    """Ask Instagram whether the saved token still works."""
    if instagram.get() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Instagram is not connected.")
    try:
        return InstagramAccountResponse.from_core(instagram.check())
    except PlatformConnectionError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    except PlatformSecretError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


@router.get(
    "/settings/platforms/instagram/tunnel",
    summary="Check whether cloudflared is installed",
    responses=COMMON,
)
def get_tunnel(poster: InstagramPost) -> TunnelStatusResponse:
    """Say whether cloudflared, which gives the pictures a temporary public address for posting,
    is installed. Nothing is installed by this call."""
    return TunnelStatusResponse(installed=poster.tunnel_installed())


@router.post(
    "/settings/platforms/instagram/tunnel",
    summary="Install cloudflared",
    responses=COMMON | AI_UNREACHABLE,
)
def install_tunnel(poster: InstagramPost) -> TunnelStatusResponse:
    """Install cloudflared when it is missing (a third-party tool from Cloudflare). It can take a
    minute. Fails with 502 when it cannot be downloaded or installed."""
    try:
        poster.install_tunnel()
    except TunnelError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    return TunnelStatusResponse(installed=True)


@router.delete(
    "/settings/platforms/instagram/connection",
    summary="Disconnect Instagram",
    responses=COMMON,
)
def disconnect_instagram(instagram: InstagramSetting) -> InstagramAccountResponse:
    """Remove the token from the keychain and forget the account."""
    try:
        instagram.disconnect()
    except PlatformSecretError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
    return InstagramAccountResponse.from_core(None)
