from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ScriptType(str, enum.Enum):
    ansible = "ansible"
    shell = "shell"


class ScriptStatus(str, enum.Enum):
    pending = "pending"
    under_review = "under_review"
    approved = "approved"
    rejected = "rejected"


class Script(TimestampMixin, Base):
    __tablename__ = "scripts"

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    script_type: Mapped[ScriptType] = mapped_column(
        Enum(ScriptType, name="scripttype"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ScriptStatus] = mapped_column(
        Enum(ScriptStatus, name="scriptstatus"),
        default=ScriptStatus.pending,
        nullable=False,
        index=True,
    )
    submitted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    def __repr__(self) -> str:
        return f"<Script id={self.id} title={self.title!r} status={self.status}>"
