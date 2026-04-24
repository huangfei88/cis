from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.deps import require_role
from app.models.audit import AuditLog
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskResponse
from app.schemas.user import UserResponse, UserRoleUpdate

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_only = require_role("admin")
_admin_or_reviewer = require_role("admin", "reviewer")


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(_admin_only)],
    page: int = 1,
    per_page: int = 50,
) -> list[User]:
    offset = (page - 1) * per_page
    result = await db.execute(select(User).order_by(User.created_at.desc()).offset(offset).limit(per_page))
    return result.scalars().all()


@router.put("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    payload: UserRoleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(_admin_only)],
) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = payload.role
    await db.flush()
    return user


@router.get("/audit-logs")
async def list_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(_admin_only)],
    page: int = 1,
    per_page: int = 50,
) -> list:
    offset = (page - 1) * per_page
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(per_page)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(l.id),
            "created_at": l.created_at.isoformat(),
            "user_id": str(l.user_id) if l.user_id else None,
            "action": l.action,
            "resource_type": l.resource_type,
            "resource_id": l.resource_id,
            "ip_address": l.ip_address,
            "request_path": l.request_path,
            "request_method": l.request_method,
            "status_code": l.status_code,
            "detail": l.detail,
        }
        for l in logs
    ]


@router.get("/tasks", response_model=list[TaskResponse])
async def list_all_tasks(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(_admin_only)],
    page: int = 1,
    per_page: int = 50,
) -> list[Task]:
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Task).order_by(Task.created_at.desc()).offset(offset).limit(per_page)
    )
    return result.scalars().all()


@router.get("/scripts/pending")
async def list_pending_scripts(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(_admin_or_reviewer)],
    page: int = 1,
    per_page: int = 50,
) -> list:
    from app.models.script import Script, ScriptStatus
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Script)
        .where(Script.status.in_([ScriptStatus.pending, ScriptStatus.under_review]))
        .order_by(Script.created_at.asc())
        .offset(offset)
        .limit(per_page)
    )
    scripts = result.scalars().all()
    from app.schemas.script import ScriptResponse
    return [ScriptResponse.model_validate(s) for s in scripts]
