"""Communication agent for drafting status updates."""

from .agent import CommunicationAgent, CommunicationInput, CommunicationOutput
from .templates import (
    FL_COMMUNICATION_TEMPLATES,
    CommunicationType,
    get_template,
)

__all__ = [
    "CommunicationAgent",
    "CommunicationInput",
    "CommunicationOutput",
    "FL_COMMUNICATION_TEMPLATES",
    "CommunicationType",
    "get_template",
]
