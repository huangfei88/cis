from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CredentialCreate(BaseModel):
    name: str
    cred_type: Literal["password", "private_key"]
    username: str
    secret: str  # plaintext, will be encrypted server-side


class CredentialResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    cred_type: str
    username: str
    created_at: datetime
    model_config = {"from_attributes": True}
