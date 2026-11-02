"""Request and response models. They define the API contract in the OpenAPI document."""

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from kodalo.core.brand import Brand, BrandColors, BrandData, ContrastResult, FontInfo, Palette
from kodalo.core.brand.logos import MAX_LOGO_BYTES
from kodalo.core.doctor import Check
from kodalo.core.github import ConnectionCheck, GitHubSettings


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    status: Literal["ready"] = "ready"
    version: str = Field(max_length=32, description="Version of the running service.")


class BrandResponse(BaseModel):
    """A stored brand profile."""

    id: str = Field(max_length=64, examples=["5b0c9f0e-3c0e-4f43-9d0b-2d8f6a4c1e11"])
    name: str = Field(max_length=64, examples=["Main"])
    is_default: bool = Field(description="Whether this is the default profile.")
    data: BrandData
    created_at: str = Field(max_length=40, examples=["2026-11-01T09:30:00+00:00"])
    updated_at: str = Field(max_length=40, examples=["2026-11-01T09:30:00+00:00"])

    @classmethod
    def from_core(cls, brand: Brand) -> Self:
        return cls(
            id=brand.id,
            name=brand.name,
            is_default=brand.is_default,
            data=brand.data,
            created_at=brand.created_at,
            updated_at=brand.updated_at,
        )


class BrandCreate(BaseModel):
    """Give a ``palette`` to start from a starter palette, or full ``data``; not both."""

    name: str = Field(min_length=1, max_length=64, examples=["Main"])
    palette: str | None = Field(
        default=None, max_length=32, description="Starter palette key.", examples=["midnight"]
    )
    data: BrandData | None = None

    @model_validator(mode="after")
    def _one_source(self) -> Self:
        if self.palette is not None and self.data is not None:
            raise ValueError("send either palette or data, not both")
        return self


class BrandUpdate(BaseModel):
    """Fields left out are not changed. ``data`` replaces all brand data."""

    name: str | None = Field(default=None, min_length=1, max_length=64, examples=["Renamed"])
    data: BrandData | None = None


class BrandDuplicate(BaseModel):
    name: str = Field(min_length=1, max_length=64, examples=["Main copy"])


class LogoPayload(BaseModel):
    content_base64: str = Field(
        max_length=MAX_LOGO_BYTES * 4 // 3 + 8, description="The logo file, base64 encoded."
    )


class BrandExport(BaseModel):
    """A self-contained brand file: the profile and its logos."""

    format: Literal["kodalo-brand"] = "kodalo-brand"
    version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=64, examples=["Main"])
    data: BrandData
    logos: dict[str, LogoPayload] = Field(
        default_factory=dict, max_length=2, description="Logo files by the names data refers to."
    )


class ContrastItem(BaseModel):
    color: str = Field(max_length=32, examples=["text"])
    on: str = Field(max_length=32, examples=["background"])
    mode: Literal["light", "dark"]
    ratio: float = Field(description="WCAG contrast ratio, 1 to 21.", examples=[7.4])
    minimum: float = Field(description="The ratio this pair needs.", examples=[4.5])
    passes: bool

    @classmethod
    def from_core(cls, result: ContrastResult) -> Self:
        return cls(
            color=result.foreground,
            on=result.background,
            mode=result.mode,
            ratio=result.ratio,
            minimum=result.minimum,
            passes=result.passes,
        )


class ContrastRequest(BaseModel):
    colors: BrandColors


class PaletteResponse(BaseModel):
    key: str = Field(max_length=32, examples=["midnight"])
    title: str = Field(max_length=64, examples=["Midnight"])
    data: BrandData = Field(description="Complete brand data to start a new profile from.")

    @classmethod
    def from_core(cls, palette: Palette, data: BrandData) -> Self:
        return cls(key=palette.key, title=palette.title, data=data)


class FontResponse(BaseModel):
    family: str = Field(max_length=100, examples=["Inter"])
    category: Literal["sans", "serif", "display", "mono"]
    source: Literal["bundled", "system"]

    @classmethod
    def from_core(cls, font: FontInfo) -> Self:
        return cls(family=font.family, category=font.category, source=font.source)


class CanvasPresetResponse(BaseModel):
    key: str = Field(max_length=32, examples=["instagram_portrait"])
    width: int = Field(examples=[1080])
    height: int = Field(examples=[1350])


class DoctorCheck(BaseModel):
    name: str = Field(max_length=64, examples=["Python"])
    ok: bool
    detail: str = Field(max_length=512, examples=["3.11.9 (requires 3.11+)"])
    required: bool = Field(description="A failed required check makes the diagnosis fail.")

    @classmethod
    def from_core(cls, check: Check) -> Self:
        return cls(name=check.name, ok=check.ok, detail=check.detail, required=check.required)


class DoctorResponse(BaseModel):
    healthy: bool = Field(description="Whether every required check passed.")
    checks: list[DoctorCheck]


GitHubMode = Literal["local_folder", "gh_cli", "web_fetch"]


class GitHubSettingsResponse(BaseModel):
    """How Kodalo reaches GitHub."""

    mode: GitHubMode = Field(description="The chosen way to reach GitHub.", examples=["gh_cli"])
    local_folder: str = Field(
        max_length=1024,
        description="Folder holding your repositories. Used by the local_folder mode.",
        examples=["C:/Users/me/code"],
    )

    @classmethod
    def from_core(cls, settings: GitHubSettings) -> Self:
        return cls(mode=settings.mode, local_folder=settings.local_folder)


class GitHubSettingsUpdate(BaseModel):
    """``local_folder`` left out keeps the saved folder."""

    mode: GitHubMode = Field(examples=["gh_cli"])
    local_folder: str | None = Field(default=None, max_length=1024, examples=["C:/Users/me/code"])


class GitHubCheckResponse(BaseModel):
    """Whether the chosen way of reaching GitHub works."""

    mode: GitHubMode
    ok: bool = Field(description="Whether the chosen way works.")
    detail: str = Field(max_length=256, examples=["The GitHub CLI is installed and signed in."])

    @classmethod
    def from_core(cls, check: ConnectionCheck) -> Self:
        return cls(mode=check.mode, ok=check.ok, detail=check.detail)
