from __future__ import annotations

from typing import Optional, List

from pydantic import BaseModel


class SignatureResponse(BaseModel):
    """Response after signing a resolution."""
    status: str
    signature_id: int
    signed_at: str


class MemberSignatureStatus(BaseModel):
    """Signature status for a single member."""
    member_id: int
    member_name: str
    signed_at: Optional[str] = None
    ip_address: Optional[str] = None


class SignatureStatusResponse(BaseModel):
    """Response for GET /resolutions/{id}/signatures."""
    resolution_id: int
    signatures: List[MemberSignatureStatus]
    signed_count: int
    total_members: int


class ResolutionListItem(BaseModel):
    """A resolution in the list response."""
    id: int
    title: str
    description: Optional[str] = None
    type: str
    status: str
    visibility: str
    resolution_number: Optional[str] = None
    document_id: Optional[int] = None
    meeting_id: Optional[int] = None
    created_by_id: int
    created_at: str
    updated_at: str
    closed_at: Optional[str] = None
    signature_count: int
    total_signers: int
