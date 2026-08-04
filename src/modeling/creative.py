from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Creative(BaseModel):
    creative_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    image_url: str
    prompt: str
    cluster: str
    strategy: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("creative_id")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        uuid.UUID(v)  # raises ValueError if invalid
        return v

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("image_url must be a valid HTTP/HTTPS URL")
        return v

    @field_validator("prompt", "cluster")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must not be empty or whitespace")
        return v

    model_config = {"frozen": True}


class CreativeResponse(BaseModel):
    creatives: list[Creative]

    @classmethod
    def from_list(cls, creatives: list[Creative]) -> "CreativeResponse":
        return cls(creatives=creatives)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)
