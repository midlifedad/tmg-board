from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class BoardMemberBase(BaseModel):
    """Base schema for board member data."""
    email: EmailStr
    name: str
    role: str = "member"


class BoardMemberCreate(BoardMemberBase):
    """Schema for creating a new board member."""
    pass


class BoardMemberUpdate(BaseModel):
    """Schema for updating a board member."""
    name: Optional[str] = None
    role: Optional[str] = None


class BoardMemberResponse(BoardMemberBase):
    """Schema for board member response."""
    id: int
    google_id: Optional[str] = None
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True
