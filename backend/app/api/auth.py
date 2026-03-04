from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests

from app.db import get_db
from app.models.member import BoardMember
from app.schemas.member import BoardMemberResponse
from app.config import get_settings

router = APIRouter()
settings = get_settings()


class GoogleAuthRequest(BaseModel):
    """Request body for Google OAuth verification."""
    id_token: str


class AuthResponse(BaseModel):
    """Response after successful authentication."""
    email: str
    name: str
    role: str
    is_board_member: bool
    google_id: Optional[str] = None


# =============================================================================
# Auth Dependencies
# =============================================================================

async def get_current_user(
    x_user_email: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[BoardMember]:
    """
    Returns the current user or None (optional auth).
    Used when authentication is optional.
    """
    if not x_user_email:
        return None

    member = db.query(BoardMember).filter(
        BoardMember.email == x_user_email,
        BoardMember.deleted_at.is_(None)
    ).first()

    return member


async def require_authenticated(
    user: Optional[BoardMember] = Depends(get_current_user)
) -> BoardMember:
    """
    Enforces authentication (401 if missing).
    Allows any role including shareholder.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_board(
    user: BoardMember = Depends(require_authenticated)
) -> BoardMember:
    """
    Enforces board-level access (403 if shareholder).
    Allows: board, chair, admin. Denies: shareholder.
    """
    if user.role not in ("board", "chair", "admin"):
        raise HTTPException(status_code=403, detail="Board member access required")
    return user


# Keep require_member as alias for backward compatibility
require_member = require_board


async def require_chair(
    user: BoardMember = Depends(require_authenticated)
) -> BoardMember:
    """
    Enforces Chair or Admin role (403 if not).
    Note: board has same permissions as chair for now.
    """
    if user.role not in ("board", "chair", "admin"):
        raise HTTPException(status_code=403, detail="Chair or Admin access required")
    return user


async def require_admin(
    user: BoardMember = Depends(require_authenticated)
) -> BoardMember:
    """
    Enforces Admin role (403 if not).
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# =============================================================================
# Auth Endpoints
# =============================================================================

class VerifyEmailRequest(BaseModel):
    """Request body for email verification."""
    email: str


class VerifyEmailResponse(BaseModel):
    """Response for email verification."""
    exists: bool
    id: Optional[int] = None
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[list[str]] = None


@router.post("/verify", response_model=VerifyEmailResponse)
async def verify_email(
    request: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    """
    Verify if email exists in board_members whitelist.

    Used by NextAuth during sign-in callback to check authorization.
    No authentication required - just checks if email is whitelisted.

    Returns user info + permissions if authorized, exists=false if not.
    """
    member = db.query(BoardMember).filter(
        BoardMember.email == request.email,
        BoardMember.deleted_at.is_(None)
    ).first()

    if not member:
        return VerifyEmailResponse(exists=False)

    # Get permissions for role
    from app.models.admin import Permission, RolePermission
    permissions = db.query(Permission.code).join(RolePermission).filter(
        RolePermission.role == member.role
    ).all()

    return VerifyEmailResponse(
        exists=True,
        id=member.id,
        email=member.email,
        name=member.name,
        role=member.role,
        permissions=[p[0] for p in permissions]
    )


@router.post("/google", response_model=AuthResponse)
async def verify_google_auth(
    request: GoogleAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Verify Google OAuth ID token and check if user is a board member.

    This endpoint is called by the frontend after Google sign-in.
    It verifies the token with Google and checks the email against
    the board member whitelist.

    Returns user info if authorized, 401 if not a board member.
    """
    try:
        # Verify the ID token with Google
        idinfo = id_token.verify_oauth2_token(
            request.id_token,
            requests.Request(),
            settings.google_client_id
        )

        # Get user info from the verified token
        email = idinfo.get("email")
        name = idinfo.get("name", "")
        google_id = idinfo.get("sub")

        if not email:
            raise HTTPException(
                status_code=400,
                detail="Email not found in Google token"
            )

        # Check if user is a board member
        member = db.query(BoardMember).filter(
            BoardMember.email == email,
            BoardMember.deleted_at.is_(None)
        ).first()

        if not member:
            raise HTTPException(
                status_code=401,
                detail="Not authorized. You must be a board member to access this application."
            )

        # Update google_id if not set
        if not member.google_id and google_id:
            member.google_id = google_id
            db.commit()

        return AuthResponse(
            email=member.email,
            name=member.name,
            role=member.role,
            is_board_member=True,
            google_id=member.google_id
        )

    except ValueError as e:
        # Invalid token
        raise HTTPException(
            status_code=401,
            detail=f"Invalid Google token: {str(e)}"
        )


@router.get("/user/{email}", response_model=BoardMemberResponse)
async def get_user_by_email(
    email: str,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """
    Get user details by email.

    Used by frontend to fetch user info after authentication.
    """
    member = db.query(BoardMember).filter(
        BoardMember.email == email,
        BoardMember.deleted_at.is_(None)
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="User not found")

    return member


@router.get("/me")
async def get_current_user_info(
    current_user: BoardMember = Depends(require_member),
    db: Session = Depends(get_db)
):
    """Get current authenticated user's info with effective timezone."""
    from app.models.admin import Setting

    # Determine effective timezone: user preference > org default > America/Los_Angeles
    effective_timezone = current_user.timezone
    if not effective_timezone:
        setting = db.query(Setting).filter(Setting.key == "default_timezone").first()
        effective_timezone = setting.value if setting else "America/Los_Angeles"

    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "google_id": current_user.google_id,
        "timezone": current_user.timezone,
        "effective_timezone": effective_timezone,
        "created_at": current_user.created_at,
        "is_active": current_user.is_active,
    }


class UpdateTimezoneRequest(BaseModel):
    timezone: str


# Common IANA timezones for validation
VALID_TIMEZONES = {
    "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
    "America/Anchorage", "Pacific/Honolulu", "America/Phoenix",
    "America/Toronto", "America/Vancouver", "America/Edmonton",
    "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Copenhagen",
    "Europe/Amsterdam", "Europe/Zurich", "Europe/Stockholm", "Europe/Oslo",
    "Europe/Helsinki", "Europe/Madrid", "Europe/Rome", "Europe/Vienna",
    "Europe/Brussels", "Europe/Dublin", "Europe/Lisbon", "Europe/Warsaw",
    "Europe/Prague", "Europe/Budapest", "Europe/Bucharest", "Europe/Athens",
    "Europe/Moscow", "Europe/Istanbul",
    "Asia/Tokyo", "Asia/Shanghai", "Asia/Hong_Kong", "Asia/Singapore",
    "Asia/Seoul", "Asia/Kolkata", "Asia/Dubai", "Asia/Bangkok",
    "Australia/Sydney", "Australia/Melbourne", "Australia/Perth",
    "Pacific/Auckland", "Africa/Johannesburg", "Africa/Lagos",
    "America/Sao_Paulo", "America/Mexico_City", "America/Argentina/Buenos_Aires",
    "UTC",
}


@router.patch("/me/timezone")
async def update_my_timezone(
    request: UpdateTimezoneRequest,
    current_user: BoardMember = Depends(require_authenticated),
    db: Session = Depends(get_db)
):
    """Update current user's timezone preference."""
    if request.timezone not in VALID_TIMEZONES:
        raise HTTPException(status_code=400, detail=f"Invalid timezone: {request.timezone}")

    current_user.timezone = request.timezone
    db.commit()

    return {"status": "updated", "timezone": request.timezone}


@router.post("/logout")
async def logout():
    """
    Logout endpoint.

    Note: Session management is handled by the frontend.
    This endpoint exists for API completeness.
    """
    return {"status": "ok", "message": "Logged out"}
