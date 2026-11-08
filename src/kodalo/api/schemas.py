"""Request and response models. They define the API contract in the OpenAPI document."""

from dataclasses import asdict
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

from kodalo.core.ai import TASKS, AiConnection, AiModel
from kodalo.core.ai import ConnectionCheck as AiCheck
from kodalo.core.brands.brand import Brand, BrandColors, BrandData, ContrastResult, FontInfo
from kodalo.core.brands.brand.logos import MAX_LOGO_BYTES
from kodalo.core.brands.canvas import Canvas, SocialPlatform
from kodalo.core.brands.layout import Layout, LayoutSettings
from kodalo.core.brands.palette import Palette
from kodalo.core.brands.palette.suggest import PalettePlan
from kodalo.core.doctor import Check
from kodalo.core.repositories import (
    AnalyzerPlan,
    AnalyzerResult,
    Evidence,
    LocalDetails,
    ReadmeAnalysis,
    ReadmePlan,
    ReadmeResult,
    RepoInfo,
    Suggestion,
)
from kodalo.core.repositories.readme import CLAIM_TYPES, IMPORTANCE, MATURITY
from kodalo.core.settings.ai import (
    AiCallDetail,
    AiCallRecord,
    AiHistorySettings,
    HistoryPage,
    Usage,
)
from kodalo.core.settings.github import ConnectionCheck, GitHubSettings
from kodalo.core.settings.platforms import InstagramAccount, PlatformSettings
from kodalo.core.studio import Source
from kodalo.core.studio.copy import CopyPlan, PostCopy
from kodalo.core.studio.design import Design, DesignPlan
from kodalo.core.studio.ideas import Claim, Ideas, IdeasPlan, PostIdea


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
    platform_id: str = Field(max_length=36, examples=["instagram"])
    platform: str = Field(max_length=64, examples=["Instagram"])
    size_concern: str | None = Field(
        default=None,
        max_length=300,
        description="Set when the platform does not recommend this size; saving is still allowed.",
        examples=["Instagram recommends 1080 x 1350, 1080 x 1080, 1080 x 1920."],
    )
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


class PlatformSizeResponse(BaseModel):
    name: str = Field(max_length=64, examples=["Portrait"])
    width: int = Field(ge=1, le=10000, examples=[1080])
    height: int = Field(ge=1, le=10000, examples=[1350])


class SocialPlatformResponse(BaseModel):
    """A social network a canvas can be made for, with the sizes it recommends."""

    id: str = Field(max_length=36, examples=["instagram"])
    name: str = Field(max_length=64, examples=["Instagram"])
    sizes: list[PlatformSizeResponse] = Field(
        max_length=50, description="Empty for Custom, which accepts any size."
    )

    @classmethod
    def from_core(cls, platform: SocialPlatform) -> Self:
        return cls(**platform.model_dump())


class CanvasCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64, examples=["Feed post"])
    width: int = Field(ge=200, le=4000, examples=[1080])
    height: int = Field(ge=200, le=4000, examples=[1350])
    platform_id: str = Field(default="custom", min_length=1, max_length=36, examples=["instagram"])


class CanvasUpdate(BaseModel):
    """Fields left out are not changed."""

    name: str | None = Field(default=None, min_length=1, max_length=64, examples=["Feed post"])
    width: int | None = Field(default=None, ge=200, le=4000, examples=[1080])
    height: int | None = Field(default=None, ge=200, le=4000, examples=[1350])
    platform_id: str | None = Field(default=None, min_length=1, max_length=36, examples=["custom"])


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


class PaletteSuggestion(BaseModel):
    """A palette the AI suggested. Nothing is saved until it is created."""

    name: str = Field(min_length=1, max_length=64, examples=["Desert Dusk"])
    colors: BrandColors


class PaletteSuggestionPlan(BaseModel):
    """What asking the AI for a palette would send and cost. Nothing has been sent yet."""

    provider: str = Field(max_length=32)
    label: str = Field(max_length=64, examples=["Claude API"])
    model: str = Field(max_length=128, examples=["claude-haiku-5-5"])
    palettes: int = Field(ge=0, description="Existing palettes sent so the AI avoids them.")
    input_tokens: int = Field(ge=0, description="Estimated tokens sent.", examples=[900])
    max_output_tokens: int = Field(ge=0, description="The most tokens the answer can use.")

    @classmethod
    def from_core(cls, plan: PalettePlan) -> Self:
        return cls(
            provider=plan.provider,
            label=plan.label,
            model=plan.model,
            palettes=plan.palettes,
            input_tokens=plan.input_tokens,
            max_output_tokens=plan.max_output_tokens,
        )


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
    manifest_limit: int = Field(
        ge=1,
        le=100,
        description="How many project files (package.json, pyproject.toml ...) to read when "
        "reading a repository from GitHub. Each one is a request to GitHub.",
        examples=[10],
    )
    document_limit: int = Field(
        ge=1,
        le=50,
        description="How many documents (the README and the docs it links to) to read for "
        "the README analysis.",
        examples=[10],
    )
    document_max_kb: int = Field(
        ge=1,
        le=2000,
        description="How much of each document to read, in KB. The rest is left out.",
        examples=[200],
    )

    @classmethod
    def from_core(cls, settings: GitHubSettings) -> Self:
        return cls(
            mode=settings.mode,
            local_folder=settings.local_folder,
            manifest_limit=settings.manifest_limit,
            document_limit=settings.document_limit,
            document_max_kb=settings.document_max_kb,
        )


class GitHubSettingsUpdate(BaseModel):
    """``local_folder`` or a limit left out keeps the saved value."""

    mode: GitHubMode = Field(examples=["gh_cli"])
    local_folder: str | None = Field(default=None, max_length=1024, examples=["C:/Users/me/code"])
    manifest_limit: int | None = Field(default=None, ge=1, le=100, examples=[10])
    document_limit: int | None = Field(default=None, ge=1, le=50, examples=[10])
    document_max_kb: int | None = Field(default=None, ge=1, le=2000, examples=[200])


class GitHubCheckResponse(BaseModel):
    """Whether the chosen way of reaching GitHub works."""

    mode: GitHubMode
    ok: bool = Field(description="Whether the chosen way works.")
    detail: str = Field(max_length=256, examples=["The GitHub CLI is installed and signed in."])

    @classmethod
    def from_core(cls, check: ConnectionCheck) -> Self:
        return cls(mode=check.mode, ok=check.ok, detail=check.detail)


AiProvider = Literal["claude_api", "claude_code", "chatgpt_api", "gemini_api"]


class AiModelDefaultsResponse(BaseModel):
    """The settings a model starts with: shipped for a well-known model, else Kodalo's standard."""

    max_tokens: int = Field(ge=1, le=1_000_000, examples=[128000])
    temperature: float = Field(ge=0, le=2, examples=[1.0])
    timeout_s: int = Field(ge=1, le=600, examples=[300])


class AiModelResponse(BaseModel):
    """A model of an AI connection. An empty setting means the provider's own default."""

    name: str = Field(max_length=128, examples=["claude-sonnet-5-5"])
    source: Literal["fetched", "manual"] = Field(
        description="fetched from the provider, or typed in by hand.", examples=["fetched"]
    )
    is_default: bool = Field(description="Whether the connection uses this model by default.")
    max_tokens: int | None = Field(default=None, ge=1, le=1_000_000, examples=[4096])
    temperature: float | None = Field(default=None, ge=0, le=2, examples=[0.7])
    timeout_s: int | None = Field(default=None, ge=1, le=600, examples=[60])

    @classmethod
    def from_core(cls, model: AiModel) -> Self:
        return cls(
            name=model.name,
            source=model.source,  # type: ignore[arg-type]
            is_default=model.is_default,
            max_tokens=model.max_tokens,
            temperature=model.temperature,
            timeout_s=model.timeout_s,
        )


class AiConnectionResponse(BaseModel):
    """How Kodalo reaches one AI provider. The API key is never returned, only its end."""

    provider: AiProvider = Field(examples=["claude_api"])
    label: str = Field(max_length=64, examples=["Claude API"])
    kind: Literal["api_key", "local_cli"] = Field(
        description="api_key needs a key; local_cli uses a program on this computer."
    )
    saved: bool = Field(description="Whether the connection was ever configured.")
    enabled: bool
    is_default: bool = Field(description="Whether this is the default connection.")
    base_url: str = Field(
        max_length=512, description="The address in use; empty for the provider's own."
    )
    default_base_url: str = Field(max_length=512, examples=["https://api.anthropic.com"])
    has_key: bool = Field(description="Whether an API key is saved.")
    key_hint: str = Field(
        max_length=8,
        description="The last characters of the key, to recognise it.",
        examples=["a1b2"],
    )
    status: Literal["", "ok", "failed"] = Field(
        description="The outcome of the last test; empty when never tested."
    )
    status_detail: str = Field(max_length=256, examples=["Connected. 12 models available."])
    checked_at: str | None = Field(
        default=None, max_length=32, examples=["2026-11-03T09:30:00+00:00"]
    )
    default_model: str | None = Field(default=None, max_length=128)
    models: list[AiModelResponse]

    @classmethod
    def from_core(cls, connection: AiConnection) -> Self:
        return cls(
            provider=connection.provider,  # type: ignore[arg-type]
            label=connection.label,
            kind=connection.kind,
            saved=connection.saved,
            enabled=connection.enabled,
            is_default=connection.is_default,
            base_url=connection.base_url,
            default_base_url=connection.default_base_url,
            has_key=connection.has_key,
            key_hint=connection.key_hint,
            status=connection.status,  # type: ignore[arg-type]
            status_detail=connection.status_detail,
            checked_at=connection.checked_at,
            default_model=connection.default_model,
            models=[AiModelResponse.from_core(model) for model in connection.models],
        )


class AiConnectionUpdate(BaseModel):
    """Anything left out keeps the saved value. An empty ``base_url`` resets the address."""

    enabled: bool | None = None
    api_key: str | None = Field(
        default=None, min_length=1, max_length=512, repr=False, examples=["sk-ant-..."]
    )
    base_url: str | None = Field(
        default=None, max_length=512, examples=["https://api.anthropic.com"]
    )


class AiCheckResponse(BaseModel):
    """Whether a connection works."""

    provider: AiProvider
    ok: bool = Field(description="Whether the connection works.")
    detail: str = Field(max_length=256, examples=["Connected. 12 models available."])

    @classmethod
    def from_core(cls, check: AiCheck) -> Self:
        return cls(
            provider=check.provider,  # type: ignore[arg-type]
            ok=check.ok,
            detail=check.detail,
        )


class AiDefaultConnection(BaseModel):
    """The provider to use by default."""

    provider: AiProvider


class AiModelUpdate(BaseModel):
    """The settings of a model. They replace the saved ones, so a missing one is cleared."""

    max_tokens: int | None = Field(default=None, ge=1, le=1_000_000, examples=[4096])
    temperature: float | None = Field(default=None, ge=0, le=2, examples=[0.7])
    timeout_s: int | None = Field(default=None, ge=1, le=600, examples=[60])


class AiDefaultModel(BaseModel):
    """The model a connection uses by default."""

    name: str = Field(min_length=1, max_length=128, examples=["claude-sonnet-5-5"])


AiTaskName = Literal[
    "palette",
    "repo_metadata",
    "repo_features",
    "studio_ideas",
    "studio_copy",
    "studio_design",
]


class AiTaskModelResponse(BaseModel):
    """A job done by AI and the model chosen for it."""

    task: AiTaskName = Field(examples=["studio_copy"])
    label: str = Field(max_length=64, examples=["Studio copywriter"])
    description: str = Field(max_length=256, examples=["Writes the text of a post."])
    model: str | None = Field(
        default=None,
        max_length=128,
        description="The chosen model, or empty to use the default connection's default model.",
        examples=["claude-sonnet-5-5"],
    )

    @classmethod
    def from_core(cls, chosen: dict[str, str]) -> list[Self]:
        return [
            cls(
                task=task.id,  # type: ignore[arg-type]
                label=task.label,
                description=task.description,
                model=chosen.get(task.id),
            )
            for task in TASKS
        ]


class AiTaskModelUpdate(BaseModel):
    """The model for a job; empty uses the default connection's default model."""

    model: str | None = Field(
        default=None, min_length=1, max_length=128, examples=["claude-opus-5-5"]
    )


class AiIdeaCount(BaseModel):
    """How many post ideas Studio asks the AI for."""

    idea_count: int = Field(ge=1, le=20, description="From 1 to 20.", examples=[5])


ThemeName = Literal["system", "light", "dark"]


class ThemeResponse(BaseModel):
    """The theme the window uses."""

    theme: ThemeName = Field(
        description="light, dark, or system to follow the operating system.", examples=["system"]
    )


class ThemeUpdate(BaseModel):
    """The theme to use."""

    theme: ThemeName = Field(examples=["dark"])


LogLevelName = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class LogsResponse(BaseModel):
    """How much Kodalo logs and for how long it keeps the files."""

    level: LogLevelName = Field(description="The lowest level that is logged.", examples=["INFO"])
    retention_days: int = Field(
        ge=1, le=3650, description="Days a log file is kept.", examples=[90]
    )
    folder: str = Field(
        max_length=1024,
        description="Folder the log files are written to.",
        examples=["C:/Kodalo/logs"],
    )


class LogsUpdate(BaseModel):
    """The log settings to change; anything left out stays as it is."""

    level: LogLevelName | None = Field(default=None, examples=["DEBUG"])
    retention_days: int | None = Field(default=None, ge=1, le=3650, examples=[30])


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


class NotableDirResponse(BaseModel):
    path: str = Field(max_length=512, examples=["tests"])
    purpose: str = Field(max_length=32, examples=["tests"])


class ManifestResponse(BaseModel):
    path: str = Field(max_length=512, examples=["pyproject.toml"])
    ecosystem: str = Field(max_length=32, examples=["python"])
    is_lockfile: bool
    package_name: str | None = Field(max_length=256, examples=["kodalo"])
    version: str | None = Field(max_length=256, examples=["1.0.0"])
    dependencies: list[str] = Field(max_length=50, description="Package names, at most 50.")
    dev_dependencies: list[str] = Field(max_length=50, description="Test and tooling packages.")
    evidence: str = Field(
        max_length=128,
        description="A line of the file, at most 120 characters, that shows what was read.",
        examples=['name = "kodalo"'],
    )


class DocumentationResponse(BaseModel):
    readmes: list[str] = Field(max_length=20, description="README files at the top level.")
    docs_dir: str = Field(max_length=512, description="The documentation folder, if any.")
    changelog: str = Field(max_length=512, examples=["CHANGELOG.md"])
    contributing: str = Field(max_length=512, examples=["CONTRIBUTING.md"])
    license_file: str = Field(max_length=512, examples=["LICENSE"])
    code_of_conduct: str = Field(max_length=512)
    security: str = Field(max_length=512)


class SkippedFileResponse(BaseModel):
    path: str = Field(max_length=512, examples=[".env"])
    reason: str = Field(max_length=32, examples=["secret", "too large or unreadable"])


class FrameworkResponse(BaseModel):
    id: str = Field(max_length=64, examples=["fastapi"])
    name: str = Field(max_length=64, examples=["FastAPI"])
    category: str = Field(max_length=24, examples=["web", "lint_format"])
    evidence: str = Field(
        max_length=128, description="What shows it.", examples=['pyproject.toml: "fastapi"']
    )
    path: str = Field(max_length=1024, description="The file that shows it.")


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
    notable_dirs: list[NotableDirResponse] = Field(
        max_length=200, description="Folders with a well-known name, and what they are for."
    )
    manifests: list[ManifestResponse] = Field(
        max_length=200, description="Project files such as package.json, and lockfiles."
    )
    frameworks: list[FrameworkResponse] = Field(
        max_length=200, description="Frameworks and libraries in use, each with its evidence."
    )
    tooling: list[FrameworkResponse] = Field(
        max_length=200,
        description="Build, test, lint and format, CI, container and package tools in use.",
    )
    is_monorepo: bool = Field(description="Whether the repository holds several projects.")
    monorepo_signals: list[str] = Field(
        max_length=50,
        description="Why it was judged a monorepo.",
        examples=[["turbo.json"]],
    )
    documentation: DocumentationResponse = Field(
        description="README, changelog, contributing, license and docs folder, by file name."
    )
    skipped: list[SkippedFileResponse] = Field(
        max_length=200,
        description="Project files that were not read (secret-looking, over 200 KB or unreadable).",
    )
    has_social_preview: bool = Field(
        description="Whether the owner's social preview image is saved."
    )
    has_icon: bool = Field(description="Whether the repository's own icon is saved.")
    icon_path: str = Field(
        max_length=1024, description="The icon's path in the repository; empty when none."
    )
    icon_checked: bool = Field(
        description="Whether the README analysis with AI has looked for an icon. Checked with "
        "no icon means it found none."
    )

    @classmethod
    def from_core(cls, info: RepoInfo) -> Self:
        return cls(
            has_social_preview=info.has_social_preview,
            has_icon=info.has_icon,
            icon_path=info.icon_path,
            icon_checked=info.icon_checked_at is not None,
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
            notable_dirs=[
                NotableDirResponse(path=d.path, purpose=d.purpose) for d in info.notable_dirs
            ],
            manifests=[
                ManifestResponse(
                    path=m.path,
                    ecosystem=m.ecosystem,
                    is_lockfile=m.is_lockfile,
                    package_name=m.package_name,
                    version=m.version,
                    dependencies=list(m.dependencies),
                    dev_dependencies=list(m.dev_dependencies),
                    evidence=m.evidence,
                )
                for m in info.manifests
            ],
            frameworks=[
                FrameworkResponse(
                    id=f.id, name=f.name, category=f.category, evidence=f.evidence, path=f.path
                )
                for f in info.frameworks
            ],
            tooling=[
                FrameworkResponse(
                    id=t.id, name=t.name, category=t.category, evidence=t.evidence, path=t.path
                )
                for t in info.tooling
            ],
            is_monorepo=info.is_monorepo,
            monorepo_signals=list(info.monorepo_signals),
            documentation=DocumentationResponse(
                readmes=list(info.documentation.readmes),
                docs_dir=info.documentation.docs_dir,
                changelog=info.documentation.changelog,
                contributing=info.documentation.contributing,
                license_file=info.documentation.license_file,
                code_of_conduct=info.documentation.code_of_conduct,
                security=info.documentation.security,
            ),
            skipped=[SkippedFileResponse(path=s.path, reason=s.reason) for s in info.skipped],
        )


class AnalysisPlanResponse(BaseModel):
    """What asking the AI to analyze a repository would send and cost. Nothing has been sent yet."""

    provider: str = Field(max_length=32, description="Empty when there is nothing to do.")
    label: str = Field(max_length=64, examples=["Claude API"])
    model: str = Field(max_length=128, examples=["claude-haiku-5-5"])
    files: list[str] = Field(
        max_length=5, description="Project files whose start would be sent to write parsers."
    )
    dependencies: list[str] = Field(
        max_length=80, description="Package names no framework config covers; only names are sent."
    )
    names: list[str] = Field(max_length=40, description="Top-level file names that would be sent.")
    tool_files: list[str] = Field(
        max_length=40, description="Top-level names no tooling config covers; only names are sent."
    )
    input_tokens: int = Field(ge=0, description="Estimated tokens sent.", examples=[2100])
    max_output_tokens: int = Field(ge=0, description="The most tokens the answer can use.")

    @classmethod
    def from_core(cls, plan: AnalyzerPlan) -> Self:
        return cls(
            provider=plan.provider,
            label=plan.label,
            model=plan.model,
            files=list(plan.files),
            dependencies=list(plan.dependencies),
            names=list(plan.names),
            tool_files=list(plan.tool_files),
            input_tokens=plan.input_tokens,
            max_output_tokens=plan.max_output_tokens,
        )


class AnalysisResultResponse(BaseModel):
    """What asking the AI to analyze a repository did."""

    parsers: list[str] = Field(max_length=5, description="Ids of the parser configs saved.")
    frameworks: list[str] = Field(max_length=20, description="Ids of the frameworks saved.")
    tools: list[str] = Field(max_length=20, description="Ids of the tooling configs saved.")
    skipped: list[str] = Field(max_length=60, description="Plain sentences about what was left.")
    input_tokens: int = Field(ge=0, description="Tokens the provider counted for the request.")
    output_tokens: int = Field(ge=0, description="Tokens the provider counted for the answer.")

    @classmethod
    def from_core(cls, result: AnalyzerResult) -> Self:
        return cls(
            parsers=list(result.parsers),
            frameworks=list(result.frameworks),
            tools=list(result.tools),
            skipped=[s[:300] for s in result.skipped],
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )


class ReadmeReadRequest(BaseModel):
    """Read the README analysis, or return the saved one unless ``refresh`` is set."""

    refresh: bool = Field(default=False, description="Read the documents again.")


class EvidenceResponse(BaseModel):
    """A short quote from a document."""

    file: str = Field(max_length=1024, examples=["README.md"])
    quote: str = Field(max_length=128, examples=["pip install sweepito"])
    status: Literal["documented", "inferred"] = Field(
        description="Whether a document says it directly or it follows from what it says."
    )

    @classmethod
    def from_core(cls, evidence: Evidence) -> Self:
        return cls(
            file=evidence.file,
            quote=evidence.quote,
            status="inferred" if evidence.status == "inferred" else "documented",
        )


class InstallationResponse(BaseModel):
    method: str = Field(max_length=32, examples=["pip"])
    command: str = Field(max_length=512, examples=["pip install sweepito"])
    note: str = Field(max_length=256)
    evidence: EvidenceResponse


class CapabilityResponse(BaseModel):
    name: str = Field(max_length=128, examples=["Clean caches"])
    description: str = Field(max_length=512)
    note: str = Field(
        max_length=256, description="Says so when a document calls it planned or experimental."
    )
    evidence: EvidenceResponse


def _pick(value: str, allowed: tuple[str, ...], default: str) -> Any:
    """The value when it is one of the allowed ones, so a stored odd value cannot break a reply."""
    return value if value in allowed else default


class ClaimFlagResponse(BaseModel):
    type: Literal["number", "absolute", "comparison", "performance", "compatibility"]
    text: str = Field(max_length=120, examples=["97 rules"])
    reason: str = Field(max_length=200, description="Why it should be repeated with care.")


class FeatureResponse(BaseModel):
    name: str = Field(max_length=128, examples=["Scheduled cleanup"])
    description: str = Field(max_length=512)
    importance: Literal["headline", "supporting", "minor"] = Field(
        description="A ranking aid: how central the feature is to the product."
    )
    maturity: Literal["stable", "experimental", "planned", "unspecified"]
    claims: list[ClaimFlagResponse] = Field(
        max_length=5, description="Statements to repeat only with care."
    )
    use_cases: list[str] = Field(
        max_length=6, description="Titles of the use cases the documents tie to the feature."
    )
    evidence: EvidenceResponse


class UseCaseResponse(BaseModel):
    title: str = Field(max_length=128, examples=["Free disk space before a release"])
    description: str = Field(max_length=512)
    evidence: EvidenceResponse


class DocumentResponse(BaseModel):
    path: str = Field(max_length=1024, examples=["docs/cli.md"])
    status: Literal["read", "skipped"]
    reason: str = Field(max_length=128, description="Why a document was skipped.")
    size: int = Field(ge=0, description="Bytes read.")


class ReadmeResponse(BaseModel):
    """What the README and the docs it links to say the product is, does and how to install it."""

    repository_id: str = Field(max_length=64)
    tagline: str = Field(max_length=256, examples=["Clean up caches and build folders."])
    summary: str = Field(max_length=1000)
    purpose_file: str = Field(max_length=1024, examples=["README.md"])
    installation: list[InstallationResponse] = Field(max_length=40)
    capabilities: list[CapabilityResponse] = Field(max_length=30)
    features: list[FeatureResponse] = Field(
        max_length=12, description="Empty until the AI is asked for them."
    )
    use_cases: list[UseCaseResponse] = Field(
        max_length=6, description="Empty until the AI is asked for them."
    )
    documents: list[DocumentResponse] = Field(max_length=120)
    warnings: list[str] = Field(max_length=40)
    analyzed_at: str = Field(max_length=32)
    use_cases_at: str | None = Field(max_length=32, description="When use cases were last asked.")

    @classmethod
    def from_core(cls, analysis: ReadmeAnalysis) -> Self:
        return cls(
            repository_id=analysis.repository_id,
            tagline=analysis.tagline,
            summary=analysis.summary,
            purpose_file=analysis.purpose_file,
            installation=[
                InstallationResponse(
                    method=i.method,
                    command=i.command,
                    note=i.note,
                    evidence=EvidenceResponse.from_core(i.evidence),
                )
                for i in analysis.installation
            ],
            capabilities=[
                CapabilityResponse(
                    name=c.name,
                    description=c.description,
                    note=c.note,
                    evidence=EvidenceResponse.from_core(c.evidence),
                )
                for c in analysis.capabilities
            ],
            features=[
                FeatureResponse(
                    name=f.name,
                    description=f.description,
                    importance=_pick(f.importance, IMPORTANCE, "supporting"),
                    maturity=_pick(f.maturity, MATURITY, "unspecified"),
                    claims=[
                        ClaimFlagResponse(
                            type=_pick(c.type, CLAIM_TYPES, "number"), text=c.text, reason=c.reason
                        )
                        for c in f.claims
                    ],
                    use_cases=list(f.use_cases),
                    evidence=EvidenceResponse.from_core(f.evidence),
                )
                for f in analysis.features
            ],
            use_cases=[
                UseCaseResponse(
                    title=u.title,
                    description=u.description,
                    evidence=EvidenceResponse.from_core(u.evidence),
                )
                for u in analysis.use_cases
            ],
            documents=[
                DocumentResponse(
                    path=d.path,
                    status="read" if d.status == "read" else "skipped",
                    reason=d.reason,
                    size=d.size,
                )
                for d in analysis.documents
            ],
            warnings=[w[:300] for w in analysis.warnings],
            analyzed_at=analysis.analyzed_at,
            use_cases_at=analysis.use_cases_at,
        )


class ReadmePlanResponse(BaseModel):
    """What asking the AI to read the documents would send and cost. Nothing has been sent yet."""

    provider: str = Field(max_length=32, description="Empty when there is nothing to send.")
    label: str = Field(max_length=64, examples=["Claude API"])
    model: str = Field(max_length=128, examples=["claude-haiku-5-5"])
    documents: list[str] = Field(
        max_length=50, description="The documents whose text would be sent, secrets removed."
    )
    input_tokens: int = Field(ge=0, description="Estimated tokens sent.", examples=[6000])
    max_output_tokens: int = Field(ge=0, description="The most tokens the answer can use.")

    @classmethod
    def from_core(cls, plan: ReadmePlan) -> Self:
        return cls(
            provider=plan.provider,
            label=plan.label,
            model=plan.model,
            documents=list(plan.documents),
            input_tokens=plan.input_tokens,
            max_output_tokens=plan.max_output_tokens,
        )


class ReadmeResultResponse(BaseModel):
    """What asking the AI to read the documents did."""

    installation: int = Field(ge=0, description="Installation methods saved.")
    capabilities: int = Field(ge=0, description="Capabilities saved.")
    features: int = Field(ge=0, description="Features saved.")
    use_cases: int = Field(ge=0, description="Use cases saved.")
    icon: str = Field(
        max_length=1024, description="The icon kept from the repository; empty when none."
    )
    skipped: list[str] = Field(max_length=100, description="Plain sentences about what was left.")
    input_tokens: int = Field(ge=0, description="Tokens the provider counted for the request.")
    output_tokens: int = Field(ge=0, description="Tokens the provider counted for the answer.")

    @classmethod
    def from_core(cls, result: ReadmeResult) -> Self:
        return cls(
            installation=result.installation,
            capabilities=result.capabilities,
            features=result.features,
            use_cases=result.use_cases,
            icon=result.icon[:1024],
            skipped=[s[:300] for s in result.skipped],
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )


MAX_SAVED_IDEAS = 1000


class IdeasRequest(BaseModel):
    """What the post is about: the whole tool, or one feature, use case or capability."""

    post_type: Literal["tool", "feature"] = Field(description="The kind of post.")
    kind: Literal["", "features", "use_cases", "capabilities"] = Field(
        default="", description="Which list the focus is in; empty for a tool post."
    )
    name: str = Field(
        default="", max_length=128, description="The focus's name; empty for a tool post."
    )


class IdeasPlanResponse(BaseModel):
    """What asking the AI for post ideas would send and cost. Nothing has been sent yet."""

    provider: str = Field(max_length=32)
    label: str = Field(max_length=64, examples=["Claude API"])
    model: str = Field(max_length=128, examples=["claude-haiku-5-5"])
    items: list[str] = Field(max_length=20, description="What the post is about.")
    input_tokens: int = Field(ge=0, description="Estimated tokens sent.", examples=[2000])
    max_output_tokens: int = Field(ge=0, description="The most tokens the answer can use.")

    @classmethod
    def from_core(cls, plan: IdeasPlan) -> Self:
        return cls(
            provider=plan.provider,
            label=plan.label,
            model=plan.model,
            items=[i[:128] for i in plan.items],
            input_tokens=plan.input_tokens,
            max_output_tokens=plan.max_output_tokens,
        )


class ClaimResponse(BaseModel):
    """A short statement about the product and the quote it rests on."""

    text: str = Field(max_length=200, examples=["Reads a repository without cloning it"])
    file: str = Field(max_length=512, examples=["README.md"])
    quote: str = Field(max_length=200, description="Found in the saved analysis.")
    needs_review: bool = Field(description="True when the wording needs a check before use.")


class HookResponse(BaseModel):
    """One opening line for a post."""

    id: str = Field(max_length=32, examples=["hook-1-1"])
    text: str = Field(max_length=200, description="At most 12 words.")
    type: str = Field(max_length=32, examples=["question"])


class AngleResponse(BaseModel):
    """One way to lead with the product, with its hooks."""

    id: str = Field(max_length=32, examples=["angle-1"])
    type: str = Field(max_length=32, examples=["problem"])
    name: str = Field(max_length=80)
    summary: str = Field(max_length=300)
    audience_pain: str = Field(max_length=300)
    key_claims: list[ClaimResponse] = Field(max_length=5)
    hooks: list[HookResponse] = Field(
        max_length=MAX_SAVED_IDEAS, description="Grows as new ideas are added to the saved ones."
    )
    cautions: list[str] = Field(max_length=4)


class PostIdeaResponse(BaseModel):
    """A plan for one post, not finished copy."""

    id: str = Field(max_length=32, examples=["idea-1"])
    angle_id: str = Field(max_length=32, description="Empty when the angle is unknown.")
    hook_id: str = Field(max_length=32, description="Empty when the hook is unknown.")
    format: Literal["single_image", "carousel"]
    working_title: str = Field(max_length=120)
    objective: str = Field(max_length=300)
    outline: list[str] = Field(max_length=8, description="Short beats, not finished text.")
    visual_concept: str = Field(max_length=400)
    asset_needs: list[str] = Field(max_length=6)
    cta_type: str = Field(max_length=16, examples=["learn_more"])
    claims_used: list[ClaimResponse] = Field(max_length=6)
    risk_notes: str = Field(max_length=300)
    posted: bool = Field(
        default=False, description="Whether the post made from this idea was posted already."
    )

    @classmethod
    def from_core(cls, i: PostIdea) -> Self:
        return cls(
            id=i.id,
            angle_id=i.angle_id,
            hook_id=i.hook_id,
            format="carousel" if i.format == "carousel" else "single_image",
            working_title=i.working_title,
            objective=i.objective,
            outline=list(i.outline),
            visual_concept=i.visual_concept,
            asset_needs=list(i.asset_needs),
            cta_type=i.cta_type,
            claims_used=[_claim(c) for c in i.claims_used],
            risk_notes=i.risk_notes,
            posted=i.posted,
        )


class IdeaPostedUpdate(IdeasRequest):
    """The focus the idea is in, and whether its post was posted."""

    posted: bool = Field(description="True to flag the idea as posted, false to clear it.")


class PillarResponse(BaseModel):
    name: str = Field(max_length=80)
    description: str = Field(max_length=300)


class StrategyResponse(BaseModel):
    """The plan behind the angles."""

    objective: str = Field(max_length=300)
    audience: str = Field(max_length=200)
    pain_points: list[str] = Field(max_length=5)
    positioning: str = Field(max_length=300)
    pillars: list[PillarResponse] = Field(max_length=4)
    key_messages: list[ClaimResponse] = Field(max_length=6)


class AvoidedClaimResponse(BaseModel):
    """A statement from the analysis that should not be repeated without care."""

    text: str = Field(max_length=120)
    type: str = Field(max_length=16)
    reason: str = Field(max_length=200)


def _claim(claim: Claim) -> ClaimResponse:
    return ClaimResponse(
        text=claim.text, file=claim.file, quote=claim.quote, needs_review=claim.needs_review
    )


class IdeasResponse(BaseModel):
    """A strategy, angles and post ideas for one selection. Refreshing adds to the saved ones."""

    post_type: Literal["tool", "feature"]
    focus: str = Field(max_length=128, description="The focus's name; empty for a tool post.")
    strategy: StrategyResponse
    angles: list[AngleResponse] = Field(max_length=MAX_SAVED_IDEAS)
    post_ideas: list[PostIdeaResponse] = Field(max_length=MAX_SAVED_IDEAS)
    claims_to_avoid: list[AvoidedClaimResponse] = Field(
        max_length=100, description="Statements from the analysis not to repeat without care."
    )
    warnings: list[str] = Field(max_length=100, description="Plain sentences about what was left.")
    input_tokens: int = Field(ge=0, description="Tokens the provider counted for the request.")
    output_tokens: int = Field(ge=0, description="Tokens the provider counted for the answer.")

    @classmethod
    def from_core(cls, ideas: Ideas) -> Self:
        s = ideas.strategy
        return cls(
            post_type="feature" if ideas.post_type == "feature" else "tool",
            focus=ideas.focus,
            strategy=StrategyResponse(
                objective=s.objective,
                audience=s.audience,
                pain_points=list(s.pain_points),
                positioning=s.positioning,
                pillars=[PillarResponse(name=n, description=d) for n, d in s.pillars],
                key_messages=[_claim(c) for c in s.key_messages],
            ),
            angles=[
                AngleResponse(
                    id=a.id,
                    type=a.type,
                    name=a.name,
                    summary=a.summary,
                    audience_pain=a.audience_pain,
                    key_claims=[_claim(c) for c in a.key_claims],
                    hooks=[HookResponse(id=h.id, text=h.text, type=h.type) for h in a.hooks],
                    cautions=list(a.cautions),
                )
                for a in ideas.angles
            ],
            post_ideas=[PostIdeaResponse.from_core(i) for i in ideas.post_ideas],
            claims_to_avoid=[
                AvoidedClaimResponse(text=a.text, type=a.type, reason=a.reason)
                for a in ideas.claims_to_avoid
            ],
            warnings=[w[:300] for w in ideas.warnings],
            input_tokens=ideas.input_tokens,
            output_tokens=ideas.output_tokens,
        )


AiPeriod = Literal["day", "week", "month", "year", "all", "custom"]


class AiHistorySettingsResponse(BaseModel):
    """How the AI history is kept."""

    store_text: bool = Field(description="Whether the text of prompts and answers is kept.")
    retention_days: int = Field(
        ge=0, le=3650, description="Entries older than this many days are removed; 0 keeps them."
    )

    @classmethod
    def from_core(cls, value: AiHistorySettings) -> Self:
        return cls(store_text=value.store_text, retention_days=value.retention_days)


class AiHistorySettingsUpdate(BaseModel):
    """Changes to the AI history settings. A field left out keeps its saved value."""

    store_text: bool | None = Field(default=None, description="Keep the text of calls.")
    retention_days: int | None = Field(default=None, ge=0, le=3650, examples=[90])


class AiCallResponse(BaseModel):
    """One call to an AI provider, without its text."""

    id: str = Field(max_length=36)
    created_at: str = Field(max_length=32, examples=["2026-11-04T20:15:09+00:00"])
    title: str = Field(max_length=128, examples=["Suggest a palette"])
    purpose: str = Field(max_length=24, examples=["palette"])
    provider: str = Field(max_length=16, examples=["claude_api"])
    model: str = Field(max_length=128, examples=["claude-haiku-5-5"])
    status: str = Field(max_length=8, examples=["ok"])
    error: str = Field(max_length=256, description="Why the call failed; empty when it worked.")
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    has_text: bool = Field(description="Whether the prompt and answer text was kept.")

    @classmethod
    def from_core(cls, call: AiCallRecord) -> Self:
        return cls(
            id=call.id,
            created_at=call.created_at,
            title=call.title,
            purpose=call.purpose,
            provider=call.provider,
            model=call.model,
            status=call.status,
            error=call.error,
            input_tokens=call.input_tokens,
            output_tokens=call.output_tokens,
            has_text=call.has_text,
        )


class AiCallDetailResponse(AiCallResponse):
    """One call with what was sent and what came back, when the text was kept."""

    prompt_text: str | None = Field(max_length=200_000, description="What was sent.")
    reply_text: str | None = Field(max_length=200_000, description="What came back.")

    @classmethod
    def from_detail(cls, detail: AiCallDetail) -> Self:
        base = AiCallResponse.from_core(detail.record).model_dump()
        return cls(**base, prompt_text=detail.prompt_text, reply_text=detail.reply_text)


class AiHistoryPageResponse(BaseModel):
    """A page of calls, newest first."""

    total: int = Field(ge=0, description="How many calls match the period in all.")
    items: list[AiCallResponse] = Field(max_length=200)

    @classmethod
    def from_core(cls, page: HistoryPage) -> Self:
        return cls(total=page.total, items=[AiCallResponse.from_core(c) for c in page.items])


class AiUsageRowResponse(BaseModel):
    """Calls and tokens for one connection and model."""

    provider: str = Field(max_length=16, examples=["claude_api"])
    model: str = Field(max_length=128, examples=["claude-haiku-5-5"])
    calls: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


class AiDayUsageResponse(BaseModel):
    """Tokens used on one UTC day."""

    day: str = Field(max_length=10, examples=["2026-11-04"])
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


class AiUsageResponse(BaseModel):
    """Tokens used in a period, in all, per connection and model and per day."""

    calls: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    rows: list[AiUsageRowResponse] = Field(max_length=500)
    days: list[AiDayUsageResponse] = Field(max_length=3700)

    @classmethod
    def from_core(cls, usage: Usage) -> Self:
        return cls(
            calls=usage.calls,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            rows=[
                AiUsageRowResponse(
                    provider=r.provider,
                    model=r.model,
                    calls=r.calls,
                    input_tokens=r.input_tokens,
                    output_tokens=r.output_tokens,
                )
                for r in usage.rows
            ],
            days=[
                AiDayUsageResponse(
                    day=d.day, input_tokens=d.input_tokens, output_tokens=d.output_tokens
                )
                for d in usage.days
            ],
        )


class AiPurgeResponse(BaseModel):
    """How many history entries a purge removed."""

    deleted: int = Field(ge=0)


class CopyRequest(BaseModel):
    """Which post idea to write, with which hook, for the platform of the chosen brand."""

    brand_id: str = Field(min_length=1, max_length=64, description="The brand the post is for.")
    post_type: Literal["tool", "feature"] = Field(description="The kind of post of the ideas.")
    kind: Literal["", "features", "use_cases", "capabilities"] = Field(
        default="", description="Which list the focus is in; empty for a tool post."
    )
    name: str = Field(default="", max_length=128, description="The focus's name.")
    idea_id: str = Field(min_length=1, max_length=64, examples=["idea-1"])
    hook_id: str = Field(
        default="", max_length=64, description="The hook to open with; empty for the idea's own."
    )


class PostRequest(CopyRequest):
    """Which designed post to post, in which of the brand's colors."""

    mode: Literal["light", "dark"] = Field(
        default="light", description="The brand's colors the pictures are made in."
    )


class ExportRequest(PostRequest):
    """Which designed post to export, in which colors, and into which folder."""

    folder: str = Field(
        min_length=1,
        max_length=1024,
        description="An existing folder on this computer. The post goes into a new folder inside.",
        examples=["C:\\Users\\me\\Documents"],
    )


class ExportResultResponse(BaseModel):
    """Where the exported post was written."""

    folder: str = Field(max_length=1100, description="The new folder holding the files.")
    pictures: list[str] = Field(
        max_length=12, description="The picture files, one per slide, in order."
    )
    caption_file: str = Field(max_length=1100, description="The caption.txt file.")


class PostResultResponse(BaseModel):
    """The post that is now on Instagram."""

    media_id: str = Field(max_length=64, description="Instagram's ID of the post.")
    permalink: str = Field(
        max_length=300, description="The post's address, when Instagram gave it."
    )


class SlideModel(BaseModel):
    """One slide of a carousel, or the text of a single image."""

    role: str = Field(max_length=16, examples=["hook"])
    headline: str = Field(max_length=120)
    body: str = Field(max_length=300)
    visual_note: str = Field(max_length=300)
    alt_text: str = Field(max_length=200)


class CaptionModel(BaseModel):
    """The caption without its hashtags."""

    opening: str = Field(max_length=200)
    body: list[Annotated[str, Field(max_length=300)]] = Field(max_length=8)
    cta: str = Field(max_length=200)
    repo_url: str = Field(
        default="", max_length=512, description="The repository address shown in the caption."
    )


class CopyEdit(CopyRequest):
    """The text as the user edited it. The saved copy is replaced."""

    slides: list[SlideModel] = Field(min_length=1, max_length=12)
    caption: CaptionModel
    alt_opening: str = Field(max_length=200, description="The alternative opening line.")
    hashtags: list[Annotated[str, Field(max_length=60)]] = Field(max_length=30)


class CopyPlanResponse(BaseModel):
    """What asking the AI for the copy would send and cost. Nothing has been sent yet."""

    provider: str = Field(max_length=32)
    label: str = Field(max_length=64, examples=["Claude API"])
    model: str = Field(max_length=128, examples=["claude-haiku-5-5"])
    items: list[str] = Field(max_length=20, description="The post idea the copy is for.")
    input_tokens: int = Field(ge=0, description="Estimated tokens sent.", examples=[1500])
    max_output_tokens: int = Field(ge=0, description="The most tokens the answer can use.")

    @classmethod
    def from_core(cls, plan: CopyPlan) -> Self:
        return cls(
            provider=plan.provider,
            label=plan.label,
            model=plan.model,
            items=[i[:128] for i in plan.items],
            input_tokens=plan.input_tokens,
            max_output_tokens=plan.max_output_tokens,
        )


class ReviewFlagResponse(BaseModel):
    """A sentence to check before posting."""

    type: str = Field(max_length=24, examples=["needs_review"])
    text: str = Field(max_length=300)
    reason: str = Field(max_length=300)


class AltOpeningResponse(BaseModel):
    """A different opening line for the same caption."""

    text: str = Field(max_length=200)
    hook_id: str = Field(max_length=64)


class PostCopyResponse(BaseModel):
    """The written post: slides, caption, alternative opening and hashtags."""

    platform: str = Field(max_length=32, examples=["instagram"])
    idea_id: str = Field(max_length=64)
    hook_id: str = Field(max_length=64)
    hook_text: str = Field(max_length=200)
    format: Literal["single_image", "carousel"]
    slides: list[SlideModel] = Field(max_length=12)
    caption: CaptionModel
    alt_opening: AltOpeningResponse
    hashtags: list[str] = Field(max_length=30)
    review_flags: list[ReviewFlagResponse] = Field(max_length=20)
    warnings: list[str] = Field(max_length=100, description="Plain sentences about what to check.")
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)

    @classmethod
    def from_core(cls, post: PostCopy) -> Self:
        return cls(
            platform=post.platform,
            idea_id=post.idea_id,
            hook_id=post.hook_id,
            hook_text=post.hook_text[:200],
            format="carousel" if post.format == "carousel" else "single_image",
            slides=[SlideModel(**asdict(s)) for s in post.slides],
            caption=CaptionModel(
                opening=post.caption.opening,
                body=list(post.caption.body),
                cta=post.caption.cta,
                repo_url=post.caption.repo_url,
            ),
            alt_opening=AltOpeningResponse(
                text=post.alt_opening.text, hook_id=post.alt_opening.hook_id
            ),
            hashtags=list(post.hashtags),
            review_flags=[ReviewFlagResponse(**asdict(f)) for f in post.review_flags],
            warnings=[w[:300] for w in post.warnings],
            input_tokens=post.input_tokens,
            output_tokens=post.output_tokens,
        )


class PlatformSettingsResponse(BaseModel):
    """What a platform's posts get."""

    platform: Literal["instagram", "custom"] = Field(examples=["instagram"])
    hashtag_count: int = Field(
        ge=0, le=30, description="Hashtags on each post, the default ones included.", examples=[5]
    )
    default_hashtags: list[Annotated[str, Field(max_length=61)]] = Field(
        max_length=30, description="Hashtags every post carries, before the ones the AI writes."
    )
    use_social_preview: bool = Field(
        description="The designer may use the repository's social preview."
    )
    use_repo_icon: bool = Field(description="The designer may use the repository's icon.")
    use_icons: bool = Field(description="The designer may use icons.")
    build_custom_images: bool = Field(description="The designer may build custom images as needed.")
    use_ai_templates: bool = Field(
        description="The AI writes the HTML and CSS of each slide instead of the fixed templates."
    )

    @classmethod
    def from_core(cls, settings: PlatformSettings) -> Self:
        return cls(
            platform=settings.platform,  # type: ignore[arg-type]
            hashtag_count=settings.hashtag_count,
            default_hashtags=list(settings.default_hashtags),
            use_social_preview=settings.use_social_preview,
            use_repo_icon=settings.use_repo_icon,
            use_icons=settings.use_icons,
            build_custom_images=settings.build_custom_images,
            use_ai_templates=settings.use_ai_templates,
        )


class PlatformSettingsUpdate(BaseModel):
    """The hashtag settings of a platform. The saved ones are replaced."""

    hashtag_count: int = Field(ge=0, le=30, examples=[5])
    default_hashtags: list[Annotated[str, Field(max_length=61)]] = Field(
        max_length=30, examples=[["#sweepito"]]
    )
    use_social_preview: bool = False
    use_repo_icon: bool = False
    use_icons: bool = False
    build_custom_images: bool = False
    use_ai_templates: bool = False


class InstagramConnectRequest(BaseModel):
    """The access token and account ID to connect Instagram with."""

    access_token: str = Field(
        min_length=1,
        max_length=1024,
        description="An access token, from the Meta developer dashboard.",
        examples=["EAAxxxxxxxxxxxx"],
    )
    account_id: str = Field(
        min_length=1,
        max_length=40,
        description="The Instagram account's ID, shown next to the token in the dashboard.",
        examples=["17841400000000000"],
    )


class TunnelStatusResponse(BaseModel):
    """Whether cloudflared, the tool posting needs, is installed."""

    installed: bool = Field(description="Whether cloudflared is installed.")


class InstagramAccountResponse(BaseModel):
    """The connected Instagram account. The token is never returned, only its last characters."""

    connected: bool = Field(description="Whether Instagram is connected.")
    username: str = Field(max_length=100, description="The account's name.", examples=["sweepito"])
    account_id: str = Field(max_length=40, description="The account's ID.", examples=["1784140"])
    account_type: str = Field(
        max_length=40, description="Business or Media_Creator.", examples=["BUSINESS"]
    )
    token_hint: str = Field(max_length=4, description="The last characters of the token.")
    connected_at: str = Field(max_length=40, description="When it was connected (UTC).")

    @classmethod
    def from_core(cls, account: InstagramAccount | None) -> Self:
        if account is None:
            return cls(
                connected=False,
                username="",
                account_id="",
                account_type="",
                token_hint="",
                connected_at="",
            )
        return cls(
            connected=True,
            username=account.username,
            account_id=account.account_id,
            account_type=account.account_type,
            token_hint=account.token_hint,
            connected_at=account.connected_at,
        )


class DesignPlanResponse(CopyPlanResponse):
    """What asking the AI for the design would send and cost. Nothing has been sent yet."""

    sees_social_preview: bool = Field(
        description="Whether the repository's social preview is sent too, to find its logo."
    )
    writes_html: bool = Field(
        description="Whether the AI writes each slide as HTML and CSS (much longer answers)."
    )

    @classmethod
    def from_design(cls, plan: DesignPlan) -> Self:
        return cls(
            provider=plan.provider,
            label=plan.label,
            model=plan.model,
            items=[i[:128] for i in plan.items],
            input_tokens=plan.input_tokens,
            max_output_tokens=plan.max_output_tokens,
            sees_social_preview=plan.sees_social_preview,
            writes_html=plan.writes_html,
        )


class SlideDesignResponse(BaseModel):
    """How one slide is laid out. Its text is the saved copy's, never the design's."""

    template: Literal["hook", "problem", "step", "proof", "summary", "cta", "image"]
    align: Literal["left", "center"]
    media: Literal["none", "top", "bottom"]
    accent: Literal["primary", "secondary"]
    icon: str = Field(max_length=64, description="A Bootstrap Icons name without bi-; or empty.")
    image_source: Literal["none", "social_preview", "repo_icon", "custom_svg"]
    image_fit: Literal["cover", "contain"]
    has_svg: bool = Field(description="Whether the slide has a drawing, served by `design/svg`.")
    has_html: bool = Field(
        description="Whether the AI wrote the slide as HTML and CSS, served by `design/slide`."
    )


class LogoBox(BaseModel):
    """Where the logo is in the social preview, as fractions of its width and height."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0, le=1)
    h: float = Field(gt=0, le=1)


class DesignResponse(BaseModel):
    """How the slides of a written post are laid out."""

    platform: str = Field(max_length=32, examples=["instagram"])
    idea_id: str = Field(max_length=64)
    hook_id: str = Field(max_length=64)
    slides: list[SlideDesignResponse] = Field(max_length=12)
    logo_box: LogoBox | None = Field(description="The logo in the social preview, if found.")
    warnings: list[str] = Field(max_length=100, description="Plain sentences about what changed.")
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)

    @classmethod
    def from_core(cls, design: Design) -> Self:
        box = design.logo_box
        return cls(
            platform=design.platform,
            idea_id=design.idea_id,
            hook_id=design.hook_id,
            slides=[
                SlideDesignResponse(
                    template=s.template,  # type: ignore[arg-type]
                    align=s.align,  # type: ignore[arg-type]
                    media=s.media,  # type: ignore[arg-type]
                    accent=s.accent,  # type: ignore[arg-type]
                    icon=s.icon,
                    image_source=s.image_source,  # type: ignore[arg-type]
                    image_fit=s.image_fit,  # type: ignore[arg-type]
                    has_svg=bool(s.svg),
                    has_html=bool(s.html),
                )
                for s in design.slides
            ],
            logo_box=LogoBox(x=box[0], y=box[1], w=box[2], h=box[3]) if box else None,
            warnings=[w[:300] for w in design.warnings],
            input_tokens=design.input_tokens,
            output_tokens=design.output_tokens,
        )
