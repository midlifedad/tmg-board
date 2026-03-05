"""
Templates API endpoints - CRUD for meeting templates with agenda items.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.member import BoardMember
from app.models.template import MeetingTemplate, TemplateAgendaItem
from app.api.auth import require_member, require_admin

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class TemplateAgendaItemInput(BaseModel):
    title: str
    description: Optional[str] = None
    item_type: str = "information"
    duration_minutes: Optional[int] = None
    order_index: int = 0
    is_regulatory: bool = False


class CreateTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    default_duration_minutes: Optional[int] = None
    default_location: Optional[str] = None
    items: List[TemplateAgendaItemInput] = []


class UpdateTemplateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_duration_minutes: Optional[int] = None
    default_location: Optional[str] = None
    items: Optional[List[TemplateAgendaItemInput]] = None


# =============================================================================
# Helper: serialize template to dict
# =============================================================================

def _template_to_dict(template: MeetingTemplate, include_items: bool = True) -> dict:
    """Convert a MeetingTemplate to a response dict."""
    result = {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "default_duration_minutes": template.default_duration_minutes,
        "default_location": template.default_location,
        "created_by_id": template.created_by_id,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
        "is_active": template.is_active,
        "items_count": len(template.items),
        "has_regulatory_items": any(item.is_regulatory for item in template.items),
    }
    if include_items:
        result["items"] = [
            {
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "item_type": item.item_type,
                "duration_minutes": item.duration_minutes,
                "order_index": item.order_index,
                "is_regulatory": item.is_regulatory,
            }
            for item in template.items
        ]
    return result


# =============================================================================
# Endpoints
# =============================================================================

@router.get("")
async def list_templates(
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),
):
    """List active meeting templates."""
    templates = (
        db.query(MeetingTemplate)
        .filter(MeetingTemplate.is_active == True)
        .order_by(MeetingTemplate.name)
        .all()
    )
    return [_template_to_dict(t, include_items=False) for t in templates]


@router.get("/{template_id}")
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),
):
    """Get a template with its agenda items."""
    template = (
        db.query(MeetingTemplate)
        .filter(
            MeetingTemplate.id == template_id,
            MeetingTemplate.is_active == True,
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return _template_to_dict(template, include_items=True)


@router.post("")
async def create_template(
    request: CreateTemplateRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin),
):
    """Create a new meeting template with agenda items (admin only)."""
    template = MeetingTemplate(
        name=request.name,
        description=request.description,
        default_duration_minutes=request.default_duration_minutes,
        default_location=request.default_location,
        created_by_id=current_user.id,
    )
    db.add(template)
    db.flush()  # Get the template ID

    for item_input in request.items:
        item = TemplateAgendaItem(
            template_id=template.id,
            title=item_input.title,
            description=item_input.description,
            item_type=item_input.item_type,
            duration_minutes=item_input.duration_minutes,
            order_index=item_input.order_index,
            is_regulatory=item_input.is_regulatory,
        )
        db.add(item)

    db.commit()
    db.refresh(template)
    return _template_to_dict(template, include_items=True)


@router.patch("/{template_id}")
async def update_template(
    template_id: int,
    request: UpdateTemplateRequest,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin),
):
    """Update a meeting template (admin only). If items provided, replaces all items."""
    template = (
        db.query(MeetingTemplate)
        .filter(
            MeetingTemplate.id == template_id,
            MeetingTemplate.is_active == True,
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if request.name is not None:
        template.name = request.name
    if request.description is not None:
        template.description = request.description
    if request.default_duration_minutes is not None:
        template.default_duration_minutes = request.default_duration_minutes
    if request.default_location is not None:
        template.default_location = request.default_location

    if request.items is not None:
        # Replace all items
        db.query(TemplateAgendaItem).filter(
            TemplateAgendaItem.template_id == template_id
        ).delete()

        for item_input in request.items:
            item = TemplateAgendaItem(
                template_id=template_id,
                title=item_input.title,
                description=item_input.description,
                item_type=item_input.item_type,
                duration_minutes=item_input.duration_minutes,
                order_index=item_input.order_index,
                is_regulatory=item_input.is_regulatory,
            )
            db.add(item)

    db.commit()
    db.refresh(template)
    return _template_to_dict(template, include_items=True)


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_admin),
):
    """Soft-delete a meeting template (admin only). Sets is_active=False."""
    template = (
        db.query(MeetingTemplate)
        .filter(
            MeetingTemplate.id == template_id,
            MeetingTemplate.is_active == True,
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    template.is_active = False
    db.commit()

    return {"status": "deleted", "id": template_id}
