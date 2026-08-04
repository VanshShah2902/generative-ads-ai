from __future__ import annotations

import uuid
from typing import Any

from src.tools.base import BaseTool


class AdGeneratorTool(BaseTool):
    """
    Generates ad creatives for a given product and campaign goal.
    Mock implementation — replace body of generate_creatives() with real pipeline.
    """

    @property
    def name(self) -> str:
        return "generate_creatives"

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.generate_creatives(payload)

    def generate_creatives(self, payload: dict[str, Any]) -> dict[str, Any]:
        product_name = payload.get("product_name", "Unknown Product")
        cluster = payload.get("cluster", "awareness")
        max_creatives = int(payload.get("max_creatives", 3))

        creatives = [
            {
                "creative_id": str(uuid.uuid4()),
                "image_url": "https://cdn.example.com/mock-ad.png",
                "prompt": f"A compelling {cluster} ad for {product_name}.",
                "cluster": cluster,
            }
            for _ in range(max_creatives)
        ]

        return {"status": "success", "creatives": creatives}
