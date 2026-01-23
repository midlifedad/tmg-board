from typing import List, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.member import BoardMember
from app.models.document import Document
from app.api.auth import require_member, require_chair, require_admin
from app.config import get_settings

router = APIRouter()
settings = get_settings()


class UploadUrlRequest(BaseModel):
    """Request for presigned upload URL."""
    filename: str
    content_type: str = "application/pdf"


class UploadUrlResponse(BaseModel):
    """Response with presigned upload URL."""
    upload_url: str
    file_key: str
    expires_in: int


class CreateDocumentRequest(BaseModel):
    """Request to create document record after upload."""
    title: str
    type: str  # financial, resolution, minutes, audit, strategy, etc.
    description: Optional[str] = None
    file_key: str  # S3 key from upload


@router.get("/")
async def list_documents(
    type: Optional[str] = Query(None, description="Filter by document type"),
    status: Optional[str] = Query(None, description="Filter by signing status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """List documents with optional filtering."""
    query = db.query(Document).filter(Document.deleted_at.is_(None))

    if type:
        query = query.filter(Document.type == type)
    if status:
        query = query.filter(Document.signing_status == status)

    total = query.count()
    documents = query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "items": documents,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Get a single document by ID."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return document


@router.post("/upload-url", response_model=UploadUrlResponse)
async def get_upload_url(
    request: UploadUrlRequest,
    current_user: BoardMember = Depends(require_chair)
):
    """
    Get presigned URL for direct upload to S3.

    Chair or Admin only. Returns a URL valid for 15 minutes.
    Frontend uploads directly to S3, then calls POST /documents with file_key.
    """
    if settings.storage_type != "s3":
        # For local dev, return a mock response
        file_key = f"documents/{uuid.uuid4()}/{request.filename}"
        return UploadUrlResponse(
            upload_url=f"http://localhost:3010/api/documents/upload-local",
            file_key=file_key,
            expires_in=900
        )

    from app.services.storage import storage_service

    if not storage_service:
        raise HTTPException(
            status_code=503,
            detail="Storage service not configured"
        )

    # Generate unique file key
    file_key = f"documents/{uuid.uuid4()}/{request.filename}"

    result = await storage_service.generate_presigned_upload_url(
        file_key=file_key,
        content_type=request.content_type,
        expires_in=900  # 15 minutes
    )

    return UploadUrlResponse(
        upload_url=result["upload_url"],
        file_key=result["file_key"],
        expires_in=result["expires_in"]
    )


@router.post("/")
async def create_document(
    request: CreateDocumentRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """
    Create document record after file upload.

    Chair or Admin only. Call this after uploading to S3.
    """
    document = Document(
        title=request.title,
        type=request.type,
        description=request.description,
        file_path=request.file_key,
        uploaded_by_id=current_user.id,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


@router.get("/{document_id}/download-url")
async def get_download_url(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Get presigned URL for downloading document."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if settings.storage_type != "s3":
        # Local dev - return file path
        return {
            "download_url": f"/uploads/{document.file_path}",
            "expires_in": 3600
        }

    from app.services.storage import storage_service

    if not storage_service:
        raise HTTPException(status_code=503, detail="Storage service not configured")

    url = await storage_service.generate_presigned_download_url(
        file_key=document.file_path,
        expires_in=3600
    )

    return {
        "download_url": url,
        "expires_in": 3600
    }


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Soft delete a document (Admin only)."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    document.deleted_at = datetime.utcnow()
    document.deleted_by_id = current_user.id
    db.commit()

    return {"status": "deleted", "id": document_id}


@router.post("/{document_id}/restore")
async def restore_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin)
):
    """Restore a soft-deleted document (Admin only)."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.isnot(None)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found or not deleted")

    document.deleted_at = None
    document.deleted_by_id = None
    db.commit()

    return {"status": "restored", "id": document_id}


@router.post("/{document_id}/send-for-signature")
async def send_for_signature(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Send document to DocuSign for signature."""
    # TODO: Implement DocuSign integration
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{document_id}/signing-url")
async def get_signing_url(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Get embedded signing URL for current user."""
    # TODO: Implement DocuSign signing URL generation
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{document_id}/signing-status")
async def get_signing_status(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Get current signing status from DocuSign."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document_id": document_id,
        "envelope_id": document.docusign_envelope_id,
        "status": document.signing_status
    }
