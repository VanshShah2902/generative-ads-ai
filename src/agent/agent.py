from __future__ import annotations

from typing import Any

from src.agent.executor import AgentExecutor
from src.agent.planner import build_plan
from src.modeling.agent import AgentInput
from src.tools.ad_generator import AdGeneratorTool
from src.tools.meta_ads import MetaAdsTool


class AdsAgent:
    """
    Orchestrates planning and execution for an ad campaign.

    Usage:
        agent = AdsAgent()
        results = agent.run(agent_input)
    """

    def __init__(self) -> None:
        self._executor = AgentExecutor(tools=[
            AdGeneratorTool(),
            MetaAdsTool(),
        ])

    def run(self, agent_input: AgentInput) -> list[dict[str, Any]]:
        plan = build_plan(agent_input)
        return self._executor.execute(plan)
