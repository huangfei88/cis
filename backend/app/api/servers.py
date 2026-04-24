from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.deps import get_client_ip, get_current_user
from app.models.server import Server
from app.models.user import User
from app.schemas.server import ServerCreate, ServerResponse, ServerUpdate
from app.services.audit_service import AuditService

router = APIRouter(prefix="/servers", tags=["servers"])
_MAX_PER_PAGE = 100


def _check_access(server: Server, current_user: User) -> None:
    if str(server.owner_id) != str(current_user.id) and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/", response_model=list[ServerResponse])
async def list_servers(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = 1,
    per_page: int = 20,
) -> list[Server]:
    per_page = min(per_page, _MAX_PER_PAGE)
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Server)
        .where(Server.owner_id == current_user.id)
        .order_by(Server.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    return result.scalars().all()


@router.post("/", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
async def create_server(
    payload: ServerCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Server:
    server = Server(
        owner_id=current_user.id,
        name=payload.name,
        host=payload.host,
        port=payload.port,
        conn_type=payload.conn_type,
        tags=payload.tags,
    )
    db.add(server)
    await db.flush()
    await AuditService.log_action(
        db,
        action="server.create",
        user_id=current_user.id,
        resource_type="server",
        resource_id=str(server.id),
        ip_address=get_client_ip(request),
        request_path=request.url.path,
        request_method=request.method,
        status_code=201,
        result="success",
    )
    return server


@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Server:
    server = await db.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    _check_access(server, current_user)
    return server


@router.put("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: str,
    payload: ServerUpdate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Server:
    server = await db.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    _check_access(server, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(server, field, value)
    await db.flush()
    await AuditService.log_action(
        db,
        action="server.update",
        user_id=current_user.id,
        resource_type="server",
        resource_id=str(server.id),
        ip_address=get_client_ip(request),
        request_path=request.url.path,
        request_method=request.method,
        status_code=200,
        result="success",
    )
    return server


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_server(
    server_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    server = await db.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    _check_access(server, current_user)
    await db.delete(server)
    await AuditService.log_action(
        db,
        action="server.delete",
        user_id=current_user.id,
        resource_type="server",
        resource_id=server_id,
        ip_address=get_client_ip(request),
        request_path=request.url.path,
        request_method=request.method,
        status_code=204,
        result="success",
    )
