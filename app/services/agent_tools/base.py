"""Base class for all agent tools.

Every concrete tool must subclass AgentTool and implement run().
Tools are atomic, single-purpose, and must NOT generate final user-facing answers.
They return structured JSON-serialisable dicts and handle their own errors gracefully.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger("explaingithub.agent")


class AgentTool(ABC):
    """Abstract base for all GitHub investigation agent tools."""

    # ── Subclasses MUST set these ───────────────────────────────────────────
    name: str = ""
    description: str = ""

    @abstractmethod
    def run(self, **kwargs: Any) -> dict[str, Any]:
        """Execute the tool and return a structured result dict.

        Must never raise — catch all exceptions and return
        ``{"error": "<message>"}`` instead, so the agent loop can continue.
        """

    # ── Shared helpers ──────────────────────────────────────────────────────
    def _log(self, message: str) -> None:
        """Emit a clearly-prefixed terminal log line for this tool."""
        print(f"[AGENT TOOL] {self.name} → {message}")
        logger.info("[AGENT TOOL] %s → %s", self.name, message)
