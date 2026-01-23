from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.member import BoardMember
from app.schemas.member import BoardMemberResponse

router = APIRouter()


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

@router.post("/google")
async def verify_google_auth(
    google_token: str,
    db: Session = Depends(get_db)
):
    """
    Verify Google OAuth token and check if user is a board member.

    This endpoint is called by the frontend after Google sign-in.
    It verifies the token with Google and checks the email against
    the board member whitelist.
    """
    # TODO: Implement Google token verification
    # 1. Verify token with google-auth library
    # 2. Extract email from token
    # 3. Check email exists in board_members table
    # 4. Return user info if authorized

    raise HTTPException(status_code=501, detail="Not implemented")


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
