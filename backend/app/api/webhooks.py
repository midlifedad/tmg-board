import hmac
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.config import get_settings
from app.models.document import Document

router = APIRouter()
settings = get_settings()


def verify_docusign_hmac(payload: bytes, signature: str, hmac_key: str) -> bool:
    """Verify DocuSign webhook HMAC signature."""
    if not hmac_key:
        return True  # Skip verification if no key configured (dev mode)

    expected = hmac.new(
        hmac_key.encode(),
        payload,
        hashlib.sha256
    ).digest()

    import base64
    expected_b64 = base64.b64encode(expected).decode()

    return hmac.compare_digest(expected_b64, signature)


@router.post("/docusign")
async def docusign_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle DocuSign Connect webhook notifications.

    This endpoint receives notifications when envelope status changes:
    - sent: Envelope sent to recipients
    - delivered: Recipient viewed the envelope
    - completed: All recipients signed
    - declined: A recipient declined to sign
    - voided: Sender voided the envelope
    """
    # Get raw payload for HMAC verification
    payload = await request.body()

    # Verify HMAC signature
    signature = request.headers.get("X-DocuSign-Signature-1", "")
    if not verify_docusign_hmac(payload, signature, settings.docusign_hmac_key):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse JSON payload
    data = await request.json()

    # Extract envelope info
    try:
        envelope_id = data["data"]["envelopeId"]
        status = data["data"]["envelopeSummary"]["status"]
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    # Find document by envelope ID
    document = db.query(Document).filter(
        Document.docusign_envelope_id == envelope_id
    ).first()

    if not document:
        # Envelope not found - might be from a different system
        return {"status": "ignored", "reason": "envelope_not_found"}

    # Update document status
    document.signing_status = status

    # If completed, download signed document
    if status == "completed":
        # TODO: Download signed PDF from DocuSign and store
        # signed_pdf = await docusign_service.download_signed_document(envelope_id)
        # document.signed_file_path = await storage.save(signed_pdf, f"signed/{document.id}.pdf")
        pass

    db.commit()

    return {
        "status": "processed",
        "document_id": document.id,
        "envelope_id": envelope_id,
        "new_status": status
    }
