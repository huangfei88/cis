import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    script_id: uuid.UUID
    parameters: dict | None = None


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
