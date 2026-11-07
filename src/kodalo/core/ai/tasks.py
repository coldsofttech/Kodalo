"""The jobs Kodalo asks an AI model to do. Each can use its own model of the default connection."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AiTask:
    """One job: ``id`` is stored, ``label`` and ``description`` are shown in Settings."""

    id: str
    label: str
    description: str


TASKS = (
    AiTask("palette", "Palette suggestion", "Suggests brand colors for a palette."),
    AiTask(
        "repo_metadata",
        "Repository metadata",
        "Reads a repository's manifest, frameworks and tooling.",
    ),
    AiTask(
        "repo_features",
        "Repository features",
        "Describes a repository's capabilities, use cases and features.",
    ),
    AiTask("studio_ideas", "Studio ideas", "Comes up with post ideas."),
    AiTask("studio_copy", "Studio copywriter", "Writes the text of a post."),
    AiTask("studio_design", "Studio designer", "Designs the canvas of a post."),
)
TASK_IDS = tuple(task.id for task in TASKS)
