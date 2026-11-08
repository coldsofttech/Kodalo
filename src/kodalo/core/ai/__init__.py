"""AI connections and calls: the models each provider offers, and asking them.

The prompts live in ``prompts/``.
"""

from kodalo.core.ai.clients import GenerateRequest, Generation, Generator, Probe, Prober
from kodalo.core.ai.service import AiConnection, AiConnections, AiModel, AiTarget, ConnectionCheck
from kodalo.core.ai.tasks import TASK_IDS, TASKS, AiTask

__all__ = [
    "TASKS",
    "TASK_IDS",
    "AiConnection",
    "AiConnections",
    "AiModel",
    "AiTarget",
    "AiTask",
    "ConnectionCheck",
    "GenerateRequest",
    "Generation",
    "Generator",
    "Probe",
    "Prober",
]
