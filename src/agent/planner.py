from __future__ import annotations

from src.modeling.agent import AgentInput, AgentOutput, ExecutionStep, TargetSystem


def build_plan(agent_input: AgentInput) -> AgentOutput:
    """
    Rule-based planner. Produces a fixed two-step execution plan:
      1. Generate creatives (AdGeneratorTool)
      2. Launch campaign   (MetaAdsTool)

    Extend this function to add goal-based branching or dynamic step ordering.
    """
    steps = [
        ExecutionStep(
            step=1,
            action="generate_creatives",
            target_system=TargetSystem.CREATIVE_ENGINE,
            payload={
                "product_name": agent_input.product.name,
                "cluster": agent_input.campaign_goal.value,
                "max_creatives": agent_input.constraints.max_creatives,
            },
            depends_on=[],
        ),
        ExecutionStep(
            step=2,
            action="launch_campaign",
            target_system=TargetSystem.MEDIA_BUYER,
            payload={
                "budget_usd": agent_input.budget_usd,
                "regions": agent_input.constraints.target_regions,
            },
            depends_on=[1],
        ),
    ]

    return AgentOutput(
        campaign_goal=agent_input.campaign_goal,
        total_steps=len(steps),
        execution_plan=steps,
    )
