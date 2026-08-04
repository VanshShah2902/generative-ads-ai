"""
Full system flow demo — Generative Ads AI
==========================================
1. Agent receives input (product, goal, budget, constraints)
2. Planner builds a two-step execution plan
3. AdGeneratorTool generates mock creatives
4. Creatives are forwarded to MetaAdsTool
5. MetaAdsTool launches the campaign with those creatives
"""

import json
import logging

from src.agent.agent import AdsAgent
from src.modeling.agent import AgentConstraints, AgentInput, CampaignGoal, ProductData

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

# ---------------------------------------------------------------------------
# 1. Define agent input
# ---------------------------------------------------------------------------
agent_input = AgentInput(
    campaign_goal=CampaignGoal.CONVERSION,
    product=ProductData(
        name="VitaBoost",
        price="$29.99",
        benefits=["boosts energy", "improves focus", "reduces stress"],
        ingredients=["vitamin B12", "ashwagandha", "magnesium"],
    ),
    budget_usd=5000.0,
    constraints=AgentConstraints(
        max_creatives=3,
        allowed_formats=["static_banner", "video"],
        target_regions=["US", "UK"],
    ),
)

print("\n-- INPUT --------------------------------------------------------------")
print(agent_input.model_dump_json(indent=2))

# ---------------------------------------------------------------------------
# 2. Run the agent
# ---------------------------------------------------------------------------
agent = AdsAgent()
results = agent.run(agent_input)

# ---------------------------------------------------------------------------
# 3. Print results per step
# ---------------------------------------------------------------------------
print("\n-- OUTPUT -------------------------------------------------------------")
for entry in results:
    print(f"\nStep {entry['step']} — {entry['action']}")
    print(json.dumps(entry["result"], indent=2))
