from __future__ import annotations

import logging
from typing import Any

from src.modeling.agent import AgentOutput, ExecutionStep
from src.tools.base import BaseTool

logger = logging.getLogger(__name__)


class AgentExecutor:
    """
    Executes an AgentOutput plan step-by-step using a registry of tools.
    Tools are looked up by their name property, matched against ExecutionStep.action.
    """

    def __init__(self, tools: list[BaseTool]) -> None:
        self._tools: dict[str, BaseTool] = {tool.name: tool for tool in tools}

    def execute(self, plan: AgentOutput) -> list[dict[str, Any]]:
        # Keyed by step number for dependency injection
        completed: dict[int, dict[str, Any]] = {}
        results: list[dict[str, Any]] = []

        for step in plan.execution_plan:
            # Merge results from dependency steps into this step's payload
            payload = {**step.payload}
            for dep_step in step.depends_on:
                payload.update(completed.get(dep_step, {}))

            result = self._run_step(step, payload)
            completed[step.step] = result
            results.append({"step": step.step, "action": step.action, "result": result})

        return results

    def _run_step(self, step: ExecutionStep, payload: dict[str, Any]) -> dict[str, Any]:
        tool = self._tools.get(step.action)
        if tool is None:
            raise RuntimeError(f"No tool registered for action '{step.action}'.")

        logger.info("Executing step %d: %s", step.step, step.action)
        return tool.run(payload)
