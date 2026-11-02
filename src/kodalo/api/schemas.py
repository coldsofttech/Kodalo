"""Request and response models. They define the API contract in the OpenAPI document."""

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from kodalo.core.brand import Brand, BrandColors, BrandData, ContrastResult, FontInfo
from kodalo.core.brand.logos import MAX_LOGO_BYTES
from kodalo.core.canvas import Canvas
from kodalo.core.doctor import Check
from kodalo.core.github import ConnectionCheck, GitHubSettings
from kodalo.core.layout import Layout, LayoutSettings
from kodalo.core.palette import Palette
from kodalo.core.repo import LocalDetails, RepoInfo, Suggestion
from kodalo.core.studio import Source


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    status: Literal["ready"] = "ready"
    version: str = Field(max_length=32, description="Version of the running service.")


class CanvasResponse(BaseModel):
    """A named slide size. Built-in (``system``) canvases cannot be changed."""

    id: str = Field(max_length=64, examples=["system-instagram_portrait"])
    name: str = Field(max_length=64, examples=["Instagram portrait"])
    width: int = Field(ge=200, le=4000, examples=[1080])
    height: int = Field(ge=200, le=4000, examples=[1350])
    type: Literal["system", "user"]
    used_by: list[str] = Field(
        max_length=1000,
        description="Names of the brand profiles whose layout uses this canvas.",
        examples=[["Main"]],
    )
    created_at: str = Field(max_length=40, examples=["2026-11-01T09:30:00+00:00"])
    updated_at: str = Field(max_length=40, examples=["2026-11-01T09:30:00+00:00"])

    @classmethod
    def from_core(cls, canvas: Canvas) -> Self:
        return cls(**canvas.model_dump())


class CanvasCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64, examples=["Feed post"])
    width: int = Field(ge=200, le=4000, examples=[1080])
    height: int = Field(ge=200, le=4000, examples=[1350])


class CanvasUpdate(BaseModel):
    """Fields left out are not changed."""

    name: str | None = Field(default=None, min_length=1, max_length=64, examples=["Feed post"])
    width: int | None = Field(default=None, ge=200, le=4000, examples=[1080])
    height: int | None = Field(default=None, ge=200, le=4000, examples=[1350])


class CanvasDuplicate(BaseModel):
    name: str = Field(min_length=1, max_length=64, examples=["Feed post copy"])


class CanvasRef(BaseModel):
    """The canvas a brand file was made with, so another computer can match or create it."""

    name: str = Field(min_length=1, max_length=64, examples=["Feed post"])
    width: int = Field(ge=200, le=4000, examples=[1080])
    height: int = Field(ge=200, le=4000, examples=[1350])


class LayoutResponse(BaseModel):
    """A named set of slide settings that brands share. Built-in layouts cannot be changed."""

    id: str = Field(max_length=64, examples=["system-default"])
    name: str = Field(max_length=64, examples=["Default"])
    type: Literal["system", "user"]
    canvas_id: str = Field(max_length=64, examples=["system-instagram_portrait"])
    margin_top: int = Field(ge=0, le=400, examples=[96])
    margin_side: int = Field(ge=0, le=400, examples=[80])
    margin_bottom: int = Field(ge=0, le=400, examples=[96])
    corner_radius: int = Field(ge=0, le=200, examples=[24])
    slide_numbers: bool
    footer_text: str = Field(max_length=120, pattern=r"^[^\x00-\x1f]*$", examples=["@kodalo"])
    align: Literal["left", "center"]
    density: Literal["compact", "regular", "spacious"]
    slides_count: int = Field(ge=1, le=30, examples=[6])
    used_by: list[str] = Field(
        max_length=1000, description="Names of the brand profiles that use this layout."
    )
    created_at: str = Field(max_length=40, examples=["2026-11-01T09:30:00+00:00"])
    updated_at: str = Field(max_length=40, examples=["2026-11-01T09:30:00+00:00"])

    @classmethod
    def from_core(cls, layout: Layout) -> Self:
        return cls(**layout.model_dump())


class LayoutCreate(BaseModel):
    """Fields left out take the default: Instagram portrait, 6 slides."""

    name: str = Field(min_length=1, max_length=64, examples=["Feed"])
    settings: LayoutSettings = Field(default_factory=LayoutSettings)


class LayoutUpdate(BaseModel):
    """Fields left out are not changed."""

    name: str | None = Field(default=None, min_length=1, max_length=64, examples=["Feed"])
    canvas_id: str | None = Field(default=None, max_length=64)
    margin_top: int | None = Field(default=None, ge=0, le=400)
    margin_side: int | None = Field(default=None, ge=0, le=400)
    margin_bottom: int | None = Field(default=None, ge=0, le=400)
    corner_radius: int | None = Field(default=None, ge=0, le=200)
    slide_numbers: bool | None = None
    footer_text: str | None = Field(default=None, max_length=120, pattern=r"^[^\x00-\x1f]*$")
    align: Literal["left", "center"] | None = None
    density: Literal["compact", "regular", "spacious"] | None = None
    slides_count: int | None = Field(default=None, ge=1, le=30)


class LayoutDuplicate(BaseModel):
    name: str = Field(min_length=1, max_length=64, examples=["Feed copy"])


class LayoutExport(BaseModel):
    """A self-contained layout file; its canvas is matched or created on import."""

    format: Literal["kodalo-layout"] = "kodalo-layout"
    version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=64, examples=["Feed"])
    canvas: CanvasRef
    margin_top: int = Field(ge=0, le=400, examples=[96])
    margin_side: int = Field(ge=0, le=400, examples=[80])
    margin_bottom: int = Field(ge=0, le=400, examples=[96])
    corner_radius: int = Field(ge=0, le=200, examples=[24])
    slide_numbers: bool
    footer_text: str = Field(max_length=120, pattern=r"^[^\x00-\x1f]*$")
    align: Literal["left", "center"]
    density: Literal["compact", "regular", "spacious"]
    slides_count: int = Field(ge=1, le=30, examples=[6])


class BrandResponse(BaseModel):
    """A stored brand profile."""

    id: str = Field(max_length=64, examples=["5b0c9f0e-3c0e-4f43-9d0b-2d8f6a4c1e11"])
    name: str = Field(max_length=64, examples=["Main"])
    is_default: bool = Field(description="Whether this is the default profile.")
    data: BrandData
    layout: LayoutResponse = Field(description="The layout the data's layout_id refers to.")
    canvas: CanvasResponse = Field(description="The canvas of that layout.")
    created_at: str = Field(max_length=40, examples=["2026-11-01T09:30:00+00:00"])
    updated_at: str = Field(max_length=40, examples=["2026-11-01T09:30:00+00:00"])

    @classmethod
    def from_core(cls, brand: Brand) -> Self:
        return cls(
            id=brand.id,
            name=brand.name,
            is_default=brand.is_default,
            data=brand.data,
            layout=LayoutResponse.from_core(brand.layout),
            canvas=CanvasResponse.from_core(brand.canvas),
            created_at=brand.created_at,
            updated_at=brand.updated_at,
        )


class BrandCreate(BaseModel):
    """Give a ``palette`` to start from a starter palette, or full ``data``; not both."""

    name: str = Field(min_length=1, max_length=64, examples=["Main"])
    palette: str | None = Field(
        default=None,
        max_length=64,
        description="Name or id of a palette to start from; default Midnight.",
        examples=["Midnight"],
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
    layout: LayoutExport | None = Field(
        default=None, description="The layout to match or create; without it the default is used."
    )
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
    """A named set of brand colors. Built-in (``system``) palettes cannot be changed."""

    id: str = Field(max_length=64, examples=["system-midnight"])
    name: str = Field(max_length=64, examples=["Midnight"])
    type: Literal["system", "user"]
    colors: BrandColors
    data: BrandData = Field(description="Complete brand data to start a new profile from.")
    created_at: str = Field(max_length=40, examples=["2026-11-01T09:30:00+00:00"])
    updated_at: str = Field(max_length=40, examples=["2026-11-01T09:30:00+00:00"])

    @classmethod
    def from_core(cls, palette: Palette, data: BrandData) -> Self:
        return cls(**palette.model_dump(), data=data)


class PaletteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64, examples=["Ocean"])
    colors: BrandColors


class PaletteUpdate(BaseModel):
    """Fields left out are not changed."""

    name: str | None = Field(default=None, min_length=1, max_length=64, examples=["Ocean"])
    colors: BrandColors | None = None


class PaletteDuplicate(BaseModel):
    name: str = Field(min_length=1, max_length=64, examples=["Ocean copy"])


class PaletteExport(BaseModel):
    """A self-contained palette file."""

    format: Literal["kodalo-palette"] = "kodalo-palette"
    version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=64, examples=["Ocean"])
    colors: BrandColors


class CanvasExport(BaseModel):
    """A self-contained canvas file."""

    format: Literal["kodalo-canvas"] = "kodalo-canvas"
    version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=64, examples=["Feed post"])
    width: int = Field(ge=200, le=4000, examples=[1080])
    height: int = Field(ge=200, le=4000, examples=[1350])


class FontResponse(BaseModel):
    family: str = Field(max_length=100, examples=["Inter"])
    category: Literal["sans", "serif", "display", "mono"]
    source: Literal["bundled", "system"]

    @classmethod
    def from_core(cls, font: FontInfo) -> Self:
        return cls(family=font.family, category=font.category, source=font.source)


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


class StudioSourceRequest(BaseModel):
    """The repository to start a post from."""

    source: str = Field(
        max_length=1024,
        description="A folder in local_folder mode, otherwise a GitHub address or owner/repo.",
        examples=["https://github.com/owner/repo"],
    )


class StudioSourceResponse(BaseModel):
    """A checked repository source."""

    kind: Literal["local_folder", "github"]
    value: str = Field(max_length=1024, examples=["https://github.com/owner/repo"])
    name: str = Field(max_length=128, examples=["repo"])
    owner: str = Field(max_length=64, description="Empty for a local folder.", examples=["owner"])
    repo: str = Field(max_length=128, description="Empty for a local folder.", examples=["repo"])
    is_git: bool = Field(description="Whether a local folder holds a git repository.")
    stored_id: str | None = Field(
        default=None, max_length=64, description="Id of the stored repository, if read before."
    )
    suggested: "SuggestedDetails | None" = Field(
        default=None, description="For a local folder: values git could supply to prefill a form."
    )
    next_step: Literal["repository"] = "repository"

    @classmethod
    def from_core(
        cls, source: Source, stored: RepoInfo | None = None, suggested: Suggestion | None = None
    ) -> Self:
        return cls(
            kind=source.kind,
            value=source.value,
            name=source.name,
            owner=source.owner,
            repo=source.repo,
            is_git=source.is_git,
            stored_id=stored.id if stored else None,
            suggested=SuggestedDetails.from_core(suggested) if suggested else None,
        )


class SuggestedDetails(BaseModel):
    """Values read from git to prefill the local folder form."""

    owner: str = Field(max_length=128, examples=["owner"])
    repo: str = Field(max_length=128, examples=["repo"])
    default_branch: str = Field(max_length=128, examples=["main"])

    @classmethod
    def from_core(cls, suggestion: Suggestion) -> Self:
        return cls(
            owner=suggestion.owner,
            repo=suggestion.repo,
            default_branch=suggestion.default_branch,
        )


class LocalDetailsRequest(BaseModel):
    """What git cannot tell about a local folder. Owner, repo, license and branch are required."""

    owner: str = Field(max_length=128, examples=["owner"])
    repo: str = Field(max_length=128, examples=["repo"])
    license: str = Field(max_length=128, examples=["MIT"])
    default_branch: str = Field(max_length=128, examples=["main"])
    description: str = Field(default="", max_length=1024)
    homepage: str = Field(default="", max_length=512)
    topics: list[str] = Field(default_factory=list, max_length=50)
    is_private: bool = False
    is_fork: bool = False
    is_archived: bool = False

    def to_core(self) -> LocalDetails:
        return LocalDetails(
            owner=self.owner,
            repo=self.repo,
            license=self.license,
            default_branch=self.default_branch,
            description=self.description,
            homepage=self.homepage,
            topics=tuple(t[:64] for t in self.topics),
            is_private=self.is_private,
            is_fork=self.is_fork,
            is_archived=self.is_archived,
        )


class RepoReadRequest(BaseModel):
    """Read a repository, or return the stored one unless ``refresh`` is set."""

    source: str = Field(max_length=1024, examples=["https://github.com/owner/repo"])
    refresh: bool = Field(default=False, description="Read again even if it is stored.")
    details: LocalDetailsRequest | None = Field(
        default=None, description="Local folder mode only; needed the first time."
    )


class LanguageResponse(BaseModel):
    name: str = Field(max_length=64, examples=["Python"])
    bytes: int = Field(ge=0, examples=[12345])
    percent: float = Field(ge=0, le=100, examples=[87.5])


class EntryResponse(BaseModel):
    path: str = Field(max_length=512, examples=["src"])
    type: Literal["file", "dir"]


class RepoResponse(BaseModel):
    """What was read about a repository."""

    id: str = Field(max_length=64)
    url: str = Field(max_length=512, examples=["https://github.com/owner/repo"])
    owner: str = Field(max_length=128)
    name: str = Field(max_length=128)
    description: str = Field(max_length=4096)
    homepage: str = Field(max_length=512)
    default_branch: str | None = Field(max_length=128)
    license: str | None = Field(max_length=128)
    topics: list[str] = Field(max_length=100)
    is_private: bool
    is_fork: bool
    is_archived: bool
    last_pushed_at: str | None = Field(max_length=40)
    languages: list[LanguageResponse] = Field(max_length=200)
    top_level: list[EntryResponse] = Field(max_length=500)
    file_count: int = Field(ge=0)
    access_method: str = Field(max_length=16, examples=["gh_cli"])
    tree_truncated: bool
    warnings: list[str] = Field(max_length=20)
    local_path: str = Field(max_length=1024)
    last_scanned_at: str | None = Field(max_length=40)

    @classmethod
    def from_core(cls, info: RepoInfo) -> Self:
        return cls(
            id=info.id,
            url=info.url,
            owner=info.owner,
            name=info.name,
            description=info.description,
            homepage=info.homepage,
            default_branch=info.default_branch,
            license=info.license,
            topics=list(info.topics),
            is_private=info.is_private,
            is_fork=info.is_fork,
            is_archived=info.is_archived,
            last_pushed_at=info.last_pushed_at,
            languages=[
                LanguageResponse(name=x.name, bytes=x.bytes, percent=x.percent)
                for x in info.languages
            ],
            top_level=[EntryResponse(path=e.path, type=e.type) for e in info.top_level],
            file_count=info.file_count,
            access_method=info.access_method,
            tree_truncated=info.tree_truncated,
            warnings=list(info.warnings),
            local_path=info.local_path,
            last_scanned_at=info.last_scanned_at,
        )
