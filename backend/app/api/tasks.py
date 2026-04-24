from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.deps import get_client_ip, get_current_user
from app.models.script import Script, ScriptStatus
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.schemas.task import TaskCreate, TaskResponse
from app.services.audit_service import AuditService
from app.worker.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Task:
    """Create and enqueue a task. Script must be approved."""
    script = await db.get(Script, str(payload.script_id))
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if script.status != ScriptStatus.approved:
        raise HTTPException(status_code=409, detail="Script is not approved for execution")

    task = Task(
        script_id=payload.script_id,
        user_id=current_user.id,
        parameters=payload.parameters,
        status=TaskStatus.queued,
    )
    db.add(task)
    await db.flush()

    # SECURITY: Control Plane never executes scripts directly.
    # The task is handed off to the Celery worker via Redis queue.
    celery_app.send_task("execute_script_task", args=[str(task.id)])

    await AuditService.log_action(
        db, action="task.create", user_id=current_user.id,
        resource_type="task", resource_id=str(task.id),
        ip_address=get_client_ip(request),
        request_path=request.url.path, request_method=request.method,
        status_code=201,
    )
    return task


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = 1,
    per_page: int = 20,
) -> list[Task]:
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Task)
        .where(Task.user_id == current_user.id)
        .order_by(Task.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Task:
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if str(task.user_id) != str(current_user.id) and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return task
