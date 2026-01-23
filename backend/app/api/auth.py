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


async def require_member(
    user: Optional[BoardMember] = Depends(get_current_user)
) -> BoardMember:
    """
    Enforces authentication (401 if missing).
    Use this for endpoints that require a logged-in user.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_chair(
    user: BoardMember = Depends(require_member)
) -> BoardMember:
    """
    Enforces Chair or Admin role (403 if not).
    Use this for endpoints that require chair-level access.
    """
    if user.role not in ("chair", "admin"):
        raise HTTPException(status_code=403, detail="Chair or Admin access required")
    return user


async def require_admin(
    user: BoardMember = Depends(require_member)
) -> BoardMember:
    """
    Enforces Admin role (403 if not).
    Use this for endpoints that require admin-level access.
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# =============================================================================
# Auth Endpoints
# =============================================================================

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


@router.get("/me", response_model=BoardMemberResponse)
async def get_current_user_info(
    current_user: BoardMember = Depends(require_member)
):
    """Get current authenticated user's info."""
    return current_user


@router.post("/logout")
async def logout():
    """
    Logout endpoint.

    Note: Session management is handled by the frontend.
    This endpoint exists for API completeness.
    """
    return {"status": "ok", "message": "Logged out"}
