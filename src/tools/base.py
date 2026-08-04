from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """
    Base class for all agent tools.
    Each tool represents a capability the agent can invoke against a target system.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier. Used for routing and logging."""

    @abstractmethod
    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the tool with the given payload.
        Must return a result dict. Raise ValueError for invalid payloads.
        """
