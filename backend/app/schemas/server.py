from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ServerCreate(BaseModel):
    name: str
    host: str
    port: int = 22
    conn_type: Literal["ssh", "agent"]
    tags: list[str] = []


class ServerUpdate(BaseModel):
    name: str | None = None
    host: str | None = None
    port: int | None = None
    conn_type: Literal["ssh", "agent"] | None = None
    tags: list[str] | None = None
    is_active: bool | None = None


class ServerResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    host: str
    port: int
    conn_type: str
    agent_id: str | None
    fingerprint: str | None
    tags: list
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}
