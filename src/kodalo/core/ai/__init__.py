"""AI connections and calls: the models each provider offers, and asking them.

The prompts live in ``prompts/``.
"""

from kodalo.core.ai.clients import GenerateRequest, Generation, Generator, Probe, Prober
from kodalo.core.ai.service import AiConnection, AiConnections, AiModel, AiTarget, ConnectionCheck

__all__ = [
    "AiConnection",
    "AiConnections",
    "AiModel",
    "AiTarget",
    "ConnectionCheck",
    "GenerateRequest",
    "Generation",
    "Generator",
    "Probe",
    "Prober",
]
