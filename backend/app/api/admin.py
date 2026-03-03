"""
Admin API endpoints for user management, roles, permissions, and settings.
"""
from datetime import datetime, timedelta
from typing import List, Optional
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import get_db
from app.models.member import BoardMember
from app.models.admin import Invitation, Permission, RolePermission, Setting, UserSession
from app.models.audit import AuditLog
from app.api.auth import require_admin, require_board

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class InviteUserRequest(BaseModel):
    email: EmailStr
    name: str
    role: str = "board"
    message: Optional[str] = None


class InvitationResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    invited_by_id: Optional[int]
    message: Optional[str]
    expires_at: datetime
    created_at: datetime
    accepted_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    created_at: datetime
    deleted_at: Optional[datetime]
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None


class PermissionResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str]
    category: str

    class Config:
        from_attributes = True


class RolePermissionsResponse(BaseModel):
    role: str
    permissions: List[str]


class SettingResponse(BaseModel):
    key: str
    value: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


class UpdateSettingsRequest(BaseModel):
    settings: dict[str, str]


class AuditLogResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    entity_name: Optional[str]
    action: str
    changed_by_id: Optional[int]
    changed_by_name: Optional[str] = None
    changed_at: datetime
    changes: Optional[dict]
    ip_address: Optional[str]

    class Config:
        from_attributes = True


# =============================================================================
# User Management Endpoints
# =============================================================================

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """List all users with last login info."""
    query = db.query(BoardMember)
    if not include_deleted:
        query = query.filter(BoardMember.deleted_at.is_(None))

    users = query.order_by(BoardMember.name).all()

    # Get last login for each user
    result = []
    for user in users:
        last_session = db.query(UserSession).filter(
            UserSession.user_id == user.id
        ).order_by(UserSession.started_at.desc()).first()

        user_dict = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "created_at": user.created_at,
            "deleted_at": user.deleted_at,
            "last_login": last_session.started_at if last_session else None
        }
        result.append(UserResponse(**user_dict))

    return result


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Get user details by ID."""
    user = db.query(BoardMember).filter(BoardMember.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    last_session = db.query(UserSession).filter(
        UserSession.user_id == user.id
    ).order_by(UserSession.started_at.desc()).first()

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        created_at=user.created_at,
        deleted_at=user.deleted_at,
        last_login=last_session.started_at if last_session else None
    )


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Update user details (role, name)."""
    user = db.query(BoardMember).filter(
        BoardMember.id == user_id,
        BoardMember.deleted_at.is_(None)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_id == current_user.id and request.role and request.role != user.role:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    changes = {}
    if request.name and request.name != user.name:
        changes["name"] = {"old": user.name, "new": request.name}
        user.name = request.name

    if request.role and request.role != user.role:
        if request.role not in ("admin", "chair", "board", "shareholder"):
            raise HTTPException(status_code=400, detail="Invalid role")
        changes["role"] = {"old": user.role, "new": request.role}
        user.role = request.role

    if changes:
        db.add(AuditLog(
            entity_type="user",
            entity_id=user.id,
            entity_name=user.email,
            action="update",
            changed_by_id=current_user.id,
            changes=changes
        ))

    db.commit()
    return {"status": "updated", "id": user_id}


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Deactivate (soft delete) a user."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    user = db.query(BoardMember).filter(
        BoardMember.id == user_id,
        BoardMember.deleted_at.is_(None)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.deleted_at = datetime.utcnow()
    user.deleted_by_id = current_user.id

    db.add(AuditLog(
        entity_type="user",
        entity_id=user.id,
        entity_name=user.email,
        action="delete",
        changed_by_id=current_user.id
    ))

    db.commit()
    return {"status": "deactivated", "id": user_id}


@router.post("/users/{user_id}/restore")
async def restore_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Restore a deactivated user."""
    user = db.query(BoardMember).filter(
        BoardMember.id == user_id,
        BoardMember.deleted_at.isnot(None)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found or not deactivated")

    user.deleted_at = None
    user.deleted_by_id = None

    db.add(AuditLog(
        entity_type="user",
        entity_id=user.id,
        entity_name=user.email,
        action="restore",
        changed_by_id=current_user.id
    ))

    db.commit()
    return {"status": "restored", "id": user_id}


# =============================================================================
# Invitation Endpoints
# =============================================================================

@router.get("/invites", response_model=List[InvitationResponse])
async def list_invitations(
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """List pending invitations."""
    invites = db.query(Invitation).filter(
        Invitation.accepted_at.is_(None),
        Invitation.expires_at > datetime.utcnow()
    ).order_by(Invitation.created_at.desc()).all()

    return invites


@router.post("/users/invite", response_model=InvitationResponse)
async def invite_user(
    request: InviteUserRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Send invitation to a new board member."""
    # Check if email already exists
    existing_user = db.query(BoardMember).filter(
        BoardMember.email == request.email
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    # Check for existing pending invite
    existing_invite = db.query(Invitation).filter(
        Invitation.email == request.email,
        Invitation.accepted_at.is_(None),
        Invitation.expires_at > datetime.utcnow()
    ).first()
    if existing_invite:
        raise HTTPException(status_code=400, detail="Pending invitation already exists for this email")

    # Create invitation
    invitation = Invitation(
        email=request.email,
        name=request.name,
        role=request.role,
        invited_by_id=current_user.id,
        token=secrets.token_urlsafe(32),
        message=request.message,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )

    db.add(invitation)
    db.add(AuditLog(
        entity_type="invitation",
        entity_id=0,  # Will update after commit
        entity_name=request.email,
        action="create",
        changed_by_id=current_user.id
    ))
    db.commit()
    db.refresh(invitation)

    # TODO: Send invitation email

    return invitation


@router.post("/invites/{invite_id}/resend")
async def resend_invitation(
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Resend an invitation email and extend expiry."""
    invitation = db.query(Invitation).filter(
        Invitation.id == invite_id,
        Invitation.accepted_at.is_(None)
    ).first()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # Generate new token and extend expiry
    invitation.token = secrets.token_urlsafe(32)
    invitation.expires_at = datetime.utcnow() + timedelta(days=7)

    db.commit()

    # TODO: Send invitation email

    return {"status": "resent", "id": invite_id, "expires_at": invitation.expires_at}


@router.delete("/invites/{invite_id}")
async def cancel_invitation(
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Cancel a pending invitation."""
    invitation = db.query(Invitation).filter(
        Invitation.id == invite_id,
        Invitation.accepted_at.is_(None)
    ).first()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    db.delete(invitation)
    db.commit()

    return {"status": "cancelled", "id": invite_id}


# =============================================================================
# Roles & Permissions Endpoints
# =============================================================================

@router.get("/roles")
async def list_roles(
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """List all roles with user counts."""
    roles = ["admin", "chair", "board", "shareholder"]
    result = []

    for role in roles:
        count = db.query(BoardMember).filter(
            BoardMember.role == role,
            BoardMember.deleted_at.is_(None)
        ).count()

        permissions = db.query(Permission.code).join(RolePermission).filter(
            RolePermission.role == role
        ).all()

        result.append({
            "role": role,
            "user_count": count,
            "permissions": [p[0] for p in permissions]
        })

    return result


@router.get("/roles/{role_name}")
async def get_role(
    role_name: str,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Get role details with permissions."""
    if role_name not in ("admin", "chair", "board", "shareholder"):
        raise HTTPException(status_code=404, detail="Role not found")

    permissions = db.query(Permission).join(RolePermission).filter(
        RolePermission.role == role_name
    ).all()

    return {
        "role": role_name,
        "permissions": [PermissionResponse.model_validate(p) for p in permissions]
    }


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Get all available permissions."""
    return db.query(Permission).order_by(Permission.category, Permission.code).all()


# =============================================================================
# Branding (public, no auth required)
# =============================================================================

@router.get("/branding")
async def get_branding(db: Session = Depends(get_db)):
    """Get public branding settings. No auth required."""
    keys = ["app_name", "organization_name", "organization_logo_url"]
    settings = db.query(Setting).filter(Setting.key.in_(keys)).all()
    result = {s.key: s.value for s in settings}
    result.setdefault("app_name", "Board Portal")
    result.setdefault("organization_name", "")
    result.setdefault("organization_logo_url", None)
    return result


# =============================================================================
# Settings Endpoints
# =============================================================================

@router.get("/settings")
async def get_settings(
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Get all settings."""
    settings = db.query(Setting).all()
    return {s.key: s.value for s in settings}


@router.patch("/settings")
async def update_settings(
    request: UpdateSettingsRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Update multiple settings."""
    for key, value in request.settings.items():
        setting = db.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = value
            setting.updated_by_id = current_user.id
        else:
            db.add(Setting(key=key, value=value, updated_by_id=current_user.id))

    db.add(AuditLog(
        entity_type="settings",
        entity_id=0,
        action="update",
        changed_by_id=current_user.id,
        changes={"updated_keys": list(request.settings.keys())}
    ))

    db.commit()
    return {"status": "updated", "keys": list(request.settings.keys())}


# =============================================================================
# Audit Trail Endpoints
# =============================================================================

@router.get("/audit", response_model=List[AuditLogResponse])
async def list_audit_logs(
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """List audit log entries with filtering."""
    query = db.query(AuditLog)

    if user_id:
        query = query.filter(AuditLog.changed_by_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if start_date:
        query = query.filter(AuditLog.changed_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.changed_at <= end_date)

    logs = query.order_by(AuditLog.changed_at.desc()).offset(offset).limit(limit).all()

    # Add changed_by_name
    result = []
    for log in logs:
        log_dict = {
            "id": log.id,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "entity_name": log.entity_name,
            "action": log.action,
            "changed_by_id": log.changed_by_id,
            "changed_by_name": log.changed_by.name if log.changed_by else None,
            "changed_at": log.changed_at,
            "changes": log.changes,
            "ip_address": log.ip_address
        }
        result.append(AuditLogResponse(**log_dict))

    return result
