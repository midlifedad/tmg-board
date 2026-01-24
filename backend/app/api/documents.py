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
from app.models.document import Document, DocumentVersion, RelatedDocument
from app.models.audit import AuditLog, DocumentAccessLog
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


@router.get("/archived")
async def list_archived_documents(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """List archived documents."""
    query = db.query(Document).filter(
        Document.deleted_at.is_(None),
        Document.archived_at.isnot(None)
    )

    total = query.count()
    documents = query.order_by(Document.archived_at.desc()).offset(offset).limit(limit).all()

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


# =============================================================================
# Document Versions
# =============================================================================

class VersionResponse(BaseModel):
    id: int
    document_id: int
    version_number: int
    file_path: str
    uploaded_by_id: int
    uploaded_by_name: Optional[str] = None
    upload_reason: Optional[str]
    file_size: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/{document_id}/versions", response_model=List[VersionResponse])
async def list_document_versions(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """List all versions of a document."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    versions = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id
    ).order_by(DocumentVersion.version_number.desc()).all()

    result = []
    for v in versions:
        result.append(VersionResponse(
            id=v.id,
            document_id=v.document_id,
            version_number=v.version_number,
            file_path=v.file_path,
            uploaded_by_id=v.uploaded_by_id,
            uploaded_by_name=v.uploaded_by.name if v.uploaded_by else None,
            upload_reason=v.upload_reason,
            file_size=v.file_size,
            created_at=v.created_at
        ))

    return result


@router.post("/{document_id}/versions")
async def upload_new_version(
    document_id: int,
    file: UploadFile = File(...),
    reason: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Upload a new version of a document."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.archived_at:
        raise HTTPException(status_code=400, detail="Cannot upload new version to archived document")

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
        file_size = len(content)
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Create version record
    new_version_number = document.current_version + 1
    version = DocumentVersion(
        document_id=document_id,
        version_number=new_version_number,
        file_path=safe_filename,
        uploaded_by_id=current_user.id,
        upload_reason=reason,
        file_size=file_size
    )

    # Update document
    old_file_path = document.file_path
    document.file_path = safe_filename
    document.current_version = new_version_number
    document.updated_at = datetime.utcnow()

    # Create version record for old version if this is first version upload
    if document.current_version == 2:
        # This means we're going from v1 to v2, so create v1 record
        old_version = DocumentVersion(
            document_id=document_id,
            version_number=1,
            file_path=old_file_path,
            uploaded_by_id=document.uploaded_by_id,
            upload_reason="Original upload",
            created_at=document.created_at
        )
        db.add(old_version)

    db.add(version)

    # Audit log
    db.add(AuditLog(
        entity_type="document",
        entity_id=document_id,
        entity_name=document.title,
        action="version_upload",
        changed_by_id=current_user.id,
        changes={"version": new_version_number, "reason": reason}
    ))

    db.commit()

    return {
        "status": "uploaded",
        "document_id": document_id,
        "version": new_version_number
    }


@router.get("/{document_id}/versions/{version_number}/download")
async def download_document_version(
    document_id: int,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Download a specific version of a document."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    version = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document_id,
        DocumentVersion.version_number == version_number
    ).first()

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    file_path = UPLOAD_DIR / version.file_path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Log access
    db.add(DocumentAccessLog(
        document_id=document_id,
        member_id=current_user.id,
        action="download"
    ))
    db.commit()

    return FileResponse(
        path=file_path,
        filename=f"{document.title}_v{version_number}.pdf",
        media_type="application/pdf"
    )


# =============================================================================
# Archive/Unarchive
# =============================================================================

@router.post("/{document_id}/archive")
async def archive_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Archive a document (Chair or Admin only)."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.archived_at:
        raise HTTPException(status_code=400, detail="Document is already archived")

    document.archived_at = datetime.utcnow()
    document.archived_by_id = current_user.id

    db.add(AuditLog(
        entity_type="document",
        entity_id=document_id,
        entity_name=document.title,
        action="archive",
        changed_by_id=current_user.id
    ))

    db.commit()

    return {"status": "archived", "id": document_id}


@router.post("/{document_id}/unarchive")
async def unarchive_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Unarchive a document (Chair or Admin only)."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None),
        Document.archived_at.isnot(None)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found or not archived")

    document.archived_at = None
    document.archived_by_id = None

    db.add(AuditLog(
        entity_type="document",
        entity_id=document_id,
        entity_name=document.title,
        action="unarchive",
        changed_by_id=current_user.id
    ))

    db.commit()

    return {"status": "unarchived", "id": document_id}


# =============================================================================
# Related Documents
# =============================================================================

class RelatedDocumentResponse(BaseModel):
    id: int
    title: str
    type: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/{document_id}/related", response_model=List[RelatedDocumentResponse])
async def list_related_documents(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """List documents related to this document."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get related documents (both directions)
    related_ids = set()

    # Documents where this is the source
    rels1 = db.query(RelatedDocument).filter(
        RelatedDocument.document_id == document_id
    ).all()
    for r in rels1:
        related_ids.add(r.related_document_id)

    # Documents where this is the target
    rels2 = db.query(RelatedDocument).filter(
        RelatedDocument.related_document_id == document_id
    ).all()
    for r in rels2:
        related_ids.add(r.document_id)

    if not related_ids:
        return []

    related_docs = db.query(Document).filter(
        Document.id.in_(related_ids),
        Document.deleted_at.is_(None)
    ).all()

    return [RelatedDocumentResponse(
        id=d.id,
        title=d.title,
        type=d.type,
        created_at=d.created_at
    ) for d in related_docs]


class LinkDocumentsRequest(BaseModel):
    related_document_id: int


@router.post("/{document_id}/related")
async def link_related_document(
    document_id: int,
    request: LinkDocumentsRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Link two documents as related."""
    if document_id == request.related_document_id:
        raise HTTPException(status_code=400, detail="Cannot link document to itself")

    # Check both documents exist
    doc1 = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()
    doc2 = db.query(Document).filter(
        Document.id == request.related_document_id,
        Document.deleted_at.is_(None)
    ).first()

    if not doc1 or not doc2:
        raise HTTPException(status_code=404, detail="One or both documents not found")

    # Check if already linked
    existing = db.query(RelatedDocument).filter(
        ((RelatedDocument.document_id == document_id) &
         (RelatedDocument.related_document_id == request.related_document_id)) |
        ((RelatedDocument.document_id == request.related_document_id) &
         (RelatedDocument.related_document_id == document_id))
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Documents are already linked")

    # Create link
    link = RelatedDocument(
        document_id=document_id,
        related_document_id=request.related_document_id,
        created_by_id=current_user.id
    )
    db.add(link)

    db.add(AuditLog(
        entity_type="document",
        entity_id=document_id,
        entity_name=doc1.title,
        action="link_related",
        changed_by_id=current_user.id,
        changes={"related_document_id": request.related_document_id, "related_title": doc2.title}
    ))

    db.commit()

    return {"status": "linked", "document_id": document_id, "related_document_id": request.related_document_id}


@router.delete("/{document_id}/related/{related_id}")
async def unlink_related_document(
    document_id: int,
    related_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair)
):
    """Remove link between two documents."""
    # Find the link (either direction)
    link = db.query(RelatedDocument).filter(
        ((RelatedDocument.document_id == document_id) &
         (RelatedDocument.related_document_id == related_id)) |
        ((RelatedDocument.document_id == related_id) &
         (RelatedDocument.related_document_id == document_id))
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    db.delete(link)

    db.add(AuditLog(
        entity_type="document",
        entity_id=document_id,
        action="unlink_related",
        changed_by_id=current_user.id,
        changes={"related_document_id": related_id}
    ))

    db.commit()

    return {"status": "unlinked", "document_id": document_id, "related_document_id": related_id}


# =============================================================================
# Activity Log
# =============================================================================

class ActivityLogResponse(BaseModel):
    id: int
    action: str
    member_id: int
    member_name: Optional[str] = None
    accessed_at: datetime
    ip_address: Optional[str]

    class Config:
        from_attributes = True


@router.get("/{document_id}/activity", response_model=List[ActivityLogResponse])
async def get_document_activity(
    document_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member)
):
    """Get activity log for a document (views, downloads, signatures)."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted_at.is_(None)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    logs = db.query(DocumentAccessLog).filter(
        DocumentAccessLog.document_id == document_id
    ).order_by(DocumentAccessLog.accessed_at.desc()).limit(limit).all()

    result = []
    for log in logs:
        result.append(ActivityLogResponse(
            id=log.id,
            action=log.action,
            member_id=log.member_id,
            member_name=log.member.name if log.member else None,
            accessed_at=log.accessed_at,
            ip_address=log.ip_address
        ))

    return result


# =============================================================================
# DocuSign Integration (TODO)
# =============================================================================

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
