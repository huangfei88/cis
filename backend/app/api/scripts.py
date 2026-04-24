from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.deps import get_client_ip, get_current_user, require_role
from app.models.script import Script, ScriptStatus
from app.models.user import User
from app.schemas.script import ScriptCreate, ScriptResponse, ScriptReviewRequest
from app.services.audit_service import AuditService
from app.services.script_validator import ScriptValidator

router = APIRouter(prefix="/scripts", tags=["scripts"])


@router.get("/", response_model=list[ScriptResponse])
async def list_scripts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = 1,
    per_page: int = 20,
) -> list[Script]:
    """List approved scripts (all authenticated users)."""
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Script)
        .where(Script.status == ScriptStatus.approved)
        .order_by(Script.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    return result.scalars().all()


@router.post("/", response_model=ScriptResponse, status_code=status.HTTP_201_CREATED)
async def submit_script(
    payload: ScriptCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Script:
    """Submit a new script for review."""
    if payload.script_type.value == "ansible":
        valid, errors = ScriptValidator.validate_ansible_playbook(payload.content)
    else:
        valid, errors = ScriptValidator.validate_shell_script(payload.content)

    if not valid:
        raise HTTPException(
            status_code=422,
            detail={"message": "Script failed static validation", "errors": errors},
        )

    script = Script(
        title=payload.title,
        description=payload.description,
        script_type=payload.script_type,
        content=payload.content,
        submitted_by=current_user.id,
    )
    db.add(script)
    await db.flush()

    await AuditService.log_action(
        db, action="script.submit", user_id=current_user.id,
        resource_type="script", resource_id=str(script.id),
        ip_address=get_client_ip(request),
        request_path=request.url.path, request_method=request.method,
        status_code=201,
    )
    return script


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(
    script_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Script:
    script = await db.get(Script, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.delete("/{script_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_script(
    script_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    script = await db.get(Script, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if str(script.submitted_by) != str(current_user.id) and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.delete(script)
    await AuditService.log_action(
        db, action="script.delete", user_id=current_user.id,
        resource_type="script", resource_id=script_id,
        ip_address=get_client_ip(request),
        request_path=request.url.path, request_method=request.method,
        status_code=204,
    )


@router.post("/{script_id}/review", response_model=ScriptResponse)
async def review_script(
    script_id: str,
    payload: ScriptReviewRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("admin", "reviewer"))],
) -> Script:
    """Approve or reject a pending script."""
    script = await db.get(Script, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if script.status not in (ScriptStatus.pending, ScriptStatus.under_review):
        raise HTTPException(status_code=409, detail="Script is not awaiting review")
    if payload.action == "approve":
        script.status = ScriptStatus.approved
    elif payload.action == "reject":
        script.status = ScriptStatus.rejected
    else:
        raise HTTPException(status_code=422, detail="action must be 'approve' or 'reject'")
    script.reviewed_by = current_user.id
    script.review_comment = payload.comment

    await AuditService.log_action(
        db, action=f"script.{payload.action}", user_id=current_user.id,
        resource_type="script", resource_id=script_id,
        ip_address=get_client_ip(request),
        request_path=request.url.path, request_method=request.method,
        status_code=200,
    )
    return script
