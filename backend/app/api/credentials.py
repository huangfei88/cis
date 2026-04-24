from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.deps import get_client_ip, get_current_user
from app.models.credential import Credential
from app.models.user import User
from app.schemas.credential import CredentialCreate, CredentialResponse
from app.services.audit_service import AuditService
from app.services.credential_service import CredentialService

router = APIRouter(prefix="/credentials", tags=["credentials"])
_MAX_PER_PAGE = 100


def _check_access(credential: Credential, current_user: User) -> None:
    if str(credential.owner_id) != str(current_user.id) and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/", response_model=list[CredentialResponse])
async def list_credentials(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = 1,
    per_page: int = 20,
) -> list[Credential]:
    per_page = min(per_page, _MAX_PER_PAGE)
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Credential)
        .where(Credential.owner_id == current_user.id)
        .order_by(Credential.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    return result.scalars().all()


@router.post("/", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_credential(
    payload: CredentialCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Credential:
    encrypted = CredentialService.encrypt(payload.secret)
    credential = Credential(
        owner_id=current_user.id,
        name=payload.name,
        cred_type=payload.cred_type,
        username=payload.username,
        secret_enc=encrypted,
    )
    db.add(credential)
    await db.flush()
    await AuditService.log_action(
        db,
        action="credential.create",
        user_id=current_user.id,
        resource_type="credential",
        resource_id=str(credential.id),
        ip_address=get_client_ip(request),
        request_path=request.url.path,
        request_method=request.method,
        status_code=201,
        result="success",
    )
    return credential


@router.get("/{credential_id}", response_model=CredentialResponse)
async def get_credential(
    credential_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Credential:
    credential = await db.get(Credential, credential_id)
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    _check_access(credential, current_user)
    return credential


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    credential_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    credential = await db.get(Credential, credential_id)
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    _check_access(credential, current_user)
    await db.delete(credential)
    await AuditService.log_action(
        db,
        action="credential.delete",
        user_id=current_user.id,
        resource_type="credential",
        resource_id=credential_id,
        ip_address=get_client_ip(request),
        request_path=request.url.path,
        request_method=request.method,
        status_code=204,
        result="success",
    )
