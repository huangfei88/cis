import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.script import ScriptStatus, ScriptType


class ScriptCreate(BaseModel):
    title: str
    description: str | None = None
    script_type: ScriptType
    content: str


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
