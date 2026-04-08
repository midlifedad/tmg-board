"""API router for meeting minutes generation and document template management."""
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from jinja2 import Environment, BaseLoader, TemplateSyntaxError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.api.auth import require_chair, require_admin, require_member
from app.models.generation import DocumentTemplate, MeetingMinutes
from app.models.meeting import Meeting, AgendaItem, MeetingAttendance
from app.services.document_generator import document_generator

router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class GenerateMinutesRequest(BaseModel):
    transcript: str


class MinutesResponse(BaseModel):
    id: int
    meeting_id: int
    content_markdown: str
    created_at: str
    generated_by_id: int


class TemplateResponse(BaseModel):
    id: int
    name: str
    template_type: str
    system_prompt: str
    user_prompt_template: str
    is_active: bool
    created_at: str
    updated_at: str


class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    is_active: Optional[bool] = None


# ============================================================================
# Helpers
# ============================================================================

def build_meeting_context(meeting: Meeting, attendance: list, agenda: list) -> dict:
    """Assemble meeting context dict for Jinja2 template rendering."""
    return {
        "meeting": {
            "title": meeting.title,
            "date": meeting.scheduled_date.strftime("%B %d, %Y"),
            "location": meeting.location or "Virtual",
            "duration_minutes": meeting.duration_minutes,
        },
        "attendees": [
            {"name": a.member.name, "status": a.status}
            for a in attendance
            if a.status == "present"
        ],
        "agenda_items": [
            {
                "order": item.order_index + 1,
                "title": item.title,
                "type": item.item_type,
                "presenter": item.presenter.name if item.presenter else None,
                "description": item.description,
            }
            for item in sorted(agenda, key=lambda x: x.order_index)
        ],
    }


def _validate_jinja2_template(template_str: str) -> None:
    """Raise HTTPException 400 if template_str has a Jinja2 syntax error."""
    env = Environment(loader=BaseLoader())
    try:
        env.parse(template_str)
        # Also try rendering with a dummy context to catch runtime errors
        tmpl = env.from_string(template_str)
        tmpl.render(
            meeting={"title": "", "date": "", "location": "", "duration_minutes": 0},
            attendees=[],
            agenda_items=[],
            transcript="",
        )
    except TemplateSyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Invalid Jinja2 template: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Template rendering error: {e}")


# ============================================================================
# Meeting Minutes Endpoints
# ============================================================================

@router.post("/meetings/{meeting_id}/minutes", response_model=MinutesResponse)
async def generate_minutes(
    meeting_id: int,
    request: GenerateMinutesRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_chair),
):
    """Generate meeting minutes from transcript (Chair/Admin only)."""
    # Validate meeting exists and is not cancelled
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.deleted_at.is_(None),
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot generate minutes for a cancelled meeting")

    # Get active meeting_minutes template
    template = db.query(DocumentTemplate).filter(
        DocumentTemplate.template_type == "meeting_minutes",
        DocumentTemplate.is_active.is_(True),
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="No active meeting_minutes template found")

    # Check AI service is configured
    if document_generator is None:
        raise HTTPException(status_code=503, detail="AI service not configured — ANTHROPIC_API_KEY is not set")

    # Build meeting context from DB relationships
    attendance = db.query(MeetingAttendance).filter(
        MeetingAttendance.meeting_id == meeting_id
    ).all()
    agenda = db.query(AgendaItem).filter(
        AgendaItem.meeting_id == meeting_id
    ).all()
    meeting_context = build_meeting_context(meeting, attendance, agenda)

    # Call Anthropic
    try:
        import anthropic
        content_markdown = await document_generator.generate_meeting_minutes(
            transcript=request.transcript,
            meeting_context=meeting_context,
            system_prompt=template.system_prompt,
            user_prompt_template=template.user_prompt_template,
        )
    except Exception as e:
        # Catch Anthropic API errors broadly
        raise HTTPException(status_code=502, detail=f"AI generation failed: {str(e)}")

    # Upsert MeetingMinutes row
    existing = db.query(MeetingMinutes).filter(
        MeetingMinutes.meeting_id == meeting_id
    ).first()

    now = datetime.utcnow()
    if existing:
        existing.content_markdown = content_markdown
        existing.updated_at = now
        existing.generated_by_id = current_user.id
        existing.template_id = template.id
        db.commit()
        db.refresh(existing)
        minutes = existing
    else:
        minutes = MeetingMinutes(
            meeting_id=meeting_id,
            content_markdown=content_markdown,
            generated_by_id=current_user.id,
            template_id=template.id,
        )
        db.add(minutes)
        db.commit()
        db.refresh(minutes)

    return MinutesResponse(
        id=minutes.id,
        meeting_id=minutes.meeting_id,
        content_markdown=minutes.content_markdown,
        created_at=minutes.created_at.isoformat(),
        generated_by_id=minutes.generated_by_id,
    )


@router.get("/meetings/{meeting_id}/minutes", response_model=MinutesResponse)
async def get_minutes(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_member),
):
    """Get generated minutes for a meeting (Board member access)."""
    minutes = db.query(MeetingMinutes).filter(
        MeetingMinutes.meeting_id == meeting_id
    ).first()
    if not minutes:
        raise HTTPException(status_code=404, detail="No minutes found for this meeting")

    return MinutesResponse(
        id=minutes.id,
        meeting_id=minutes.meeting_id,
        content_markdown=minutes.content_markdown,
        created_at=minutes.created_at.isoformat(),
        generated_by_id=minutes.generated_by_id,
    )


# ============================================================================
# Template Management Endpoints (Admin only)
# ============================================================================

@router.get("/admin/templates", response_model=List[TemplateResponse])
async def list_templates(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """List all document templates (Admin only)."""
    templates = db.query(DocumentTemplate).all()
    return [
        TemplateResponse(
            id=t.id,
            name=t.name,
            template_type=t.template_type,
            system_prompt=t.system_prompt,
            user_prompt_template=t.user_prompt_template,
            is_active=t.is_active,
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat(),
        )
        for t in templates
    ]


@router.get("/admin/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Get a single document template by ID (Admin only)."""
    template = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return TemplateResponse(
        id=template.id,
        name=template.name,
        template_type=template.template_type,
        system_prompt=template.system_prompt,
        user_prompt_template=template.user_prompt_template,
        is_active=template.is_active,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
    )


@router.put("/admin/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    request: TemplateUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Update a document template (Admin only)."""
    template = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Validate Jinja2 syntax if user_prompt_template is being updated
    if request.user_prompt_template is not None:
        _validate_jinja2_template(request.user_prompt_template)

    # Apply non-None updates
    if request.name is not None:
        template.name = request.name
    if request.system_prompt is not None:
        template.system_prompt = request.system_prompt
    if request.user_prompt_template is not None:
        template.user_prompt_template = request.user_prompt_template
    if request.is_active is not None:
        template.is_active = request.is_active

    template.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(template)

    return TemplateResponse(
        id=template.id,
        name=template.name,
        template_type=template.template_type,
        system_prompt=template.system_prompt,
        user_prompt_template=template.user_prompt_template,
        is_active=template.is_active,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
    )
