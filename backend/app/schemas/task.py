import json
import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.task import TaskStatus

# SECURITY: cap task parameter payload to prevent large JSON bodies being
# persisted in PostgreSQL and passed into container environment variables.
_MAX_PARAMS_BYTES = 4_096


class TaskCreate(BaseModel):
    script_id: uuid.UUID
    parameters: dict | None = None

    @field_validator("parameters")
    @classmethod
    def parameters_size(cls, v: dict | None) -> dict | None:
        if v is None:
            return v
        if len(json.dumps(v).encode("utf-8")) > _MAX_PARAMS_BYTES:
            raise ValueError(f"parameters payload must be at most {_MAX_PARAMS_BYTES} bytes")
        return v


class TaskResponse(BaseModel):
    id: uuid.UUID
    script_id: uuid.UUID
    user_id: uuid.UUID
    status: TaskStatus
    parameters: dict | None
    stdout: str | None
    stderr: str | None
    exit_code: int | None
    container_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
