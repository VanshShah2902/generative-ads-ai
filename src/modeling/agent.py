from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class CampaignGoal(str, Enum):
    AWARENESS = "awareness"
    CONVERSION = "conversion"
    RETENTION = "retention"
    ENGAGEMENT = "engagement"


class TargetSystem(str, Enum):
    CREATIVE_ENGINE = "creative_engine"
    COPY_GENERATOR = "copy_generator"
    AUDIENCE_SELECTOR = "audience_selector"
    MEDIA_BUYER = "media_buyer"
    ANALYTICS = "analytics"


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------

class ProductData(BaseModel):
    name: str
    price: str
    benefits: list[str]
    ingredients: list[str]
    extra: dict[str, Any] = Field(default_factory=dict)  # extensible


class AgentConstraints(BaseModel):
    max_creatives: int = Field(default=10, ge=1)
    allowed_formats: list[str] = Field(default_factory=lambda: ["static_banner", "video", "carousel"])
    target_regions: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)  # extensible


class AgentInput(BaseModel):
    campaign_goal: CampaignGoal
    product: ProductData
    budget_usd: float = Field(..., gt=0)
    constraints: AgentConstraints = Field(default_factory=AgentConstraints)


# ---------------------------------------------------------------------------
# Output Schema
# ---------------------------------------------------------------------------

class ExecutionStep(BaseModel):
    step: int = Field(..., ge=1)
    action: str                          # e.g. "generate_creatives"
    target_system: TargetSystem
    payload: dict[str, Any]             # system-specific, intentionally open
    depends_on: list[int] = Field(default_factory=list)  # step numbers


class AgentOutput(BaseModel):
    campaign_goal: CampaignGoal
    total_steps: int
    execution_plan: list[ExecutionStep]
    metadata: dict[str, Any] = Field(default_factory=dict)
