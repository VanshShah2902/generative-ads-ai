from __future__ import annotations

import uuid
from typing import Any

from src.tools.base import BaseTool


class MetaAdsTool(BaseTool):
    """
    Launches ad campaigns on Meta (Facebook/Instagram).
    Mock implementation — replace body of launch_campaign() with real Meta API calls.
    """

    @property
    def name(self) -> str:
        return "launch_campaign"

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.launch_campaign(payload)

    def launch_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
        budget_usd = payload.get("budget_usd")
        if not budget_usd or float(budget_usd) <= 0:
            raise ValueError("launch_campaign requires a positive budget_usd.")

        creatives = payload.get("creatives", [])

        return {
            "status": "launched",
            "campaign_id": str(uuid.uuid4()),
            "platform": "meta",
            "budget_usd": float(budget_usd),
            "ad_set_id": str(uuid.uuid4()),
            "creatives_submitted": len(creatives),
        }
