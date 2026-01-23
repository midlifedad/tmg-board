from typing import List, Optional
from datetime import datetime
import uuid
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.member import BoardMember
from app.models.document import Document
from app.api.auth import require_member, require_chair, require_admin
from app.config import get_settings

router = APIRouter()
settings = get_settings()

# Storage directory - Railway Volume or local uploads folder
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "./uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    type: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """
    Upload a document file with metadata.

    Chair or Admin only. Accepts multipart form with:
    - file: PDF file
    - title: Document title
    - type: Document type (financial, resolution, minutes, audit, strategy)
    - description: Optional description
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Generate unique filename
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}.pdf"
    file_path = UPLOAD_DIR / safe_filename

    # Save file
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Create document record
    document = Document(
        title=title,
        type=type,
        description=description,
        file_path=safe_filename,
        uploaded_by_id=current_user.id,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


@router.post("/")
async def create_document(
    title: str = Form(...),
    type: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """
    Create document with file upload (alias for /upload).
    """
    return await upload_document(
        file=file,
        title=title,
        type=type,
        description=description,
        db=db,
        current_user=current_user
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Download document file."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = UPLOAD_DIR / document.file_path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file_path,
        filename=f"{document.title}.pdf",
        media_type="application/pdf"
    )


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
