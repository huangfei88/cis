import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.script import ScriptStatus, ScriptType

# SECURITY: maximum script content size (64 KiB).  Larger payloads are rejected
# before they reach the database to prevent storage exhaustion.
_MAX_CONTENT_BYTES = 65_536


class ScriptCreate(BaseModel):
    title: str
    description: str | None = None
    script_type: ScriptType
    content: str

    @field_validator("title")
    @classmethod
    def title_length(cls, v: str) -> str:
        if len(v) > 255:
            raise ValueError("Title must be at most 255 characters")
        return v

    @field_validator("content")
    @classmethod
    def content_size(cls, v: str) -> str:
        if len(v.encode("utf-8")) > _MAX_CONTENT_BYTES:
            raise ValueError(f"Script content must be at most {_MAX_CONTENT_BYTES} bytes")
        return v


class ScriptResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    script_type: ScriptType
    status: ScriptStatus
    submitted_by: uuid.UUID
    reviewed_by: uuid.UUID | None
    review_comment: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScriptReviewRequest(BaseModel):
    action: str   # "approve" | "reject"
    comment: str | None = None
