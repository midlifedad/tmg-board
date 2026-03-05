"""Tests for MeetingTemplate and TemplateAgendaItem models and API."""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.member import BoardMember


# =============================================================================
# Model Tests
# =============================================================================

class TestMeetingTemplateModel:
    """Tests for the MeetingTemplate SQLAlchemy model."""

    def test_create_meeting_template(self, db_session: Session, seed_user):
        """MeetingTemplate can be created with name, description, default_duration_minutes, default_location, created_by_id."""
        from app.models.template import MeetingTemplate

        template = MeetingTemplate(
            name="Board Meeting",
            description="Standard quarterly board meeting",
            default_duration_minutes=90,
            default_location="Conference Room A",
            created_by_id=seed_user.id,
        )
        db_session.add(template)
        db_session.commit()
        db_session.refresh(template)

        assert template.id is not None
        assert template.name == "Board Meeting"
        assert template.description == "Standard quarterly board meeting"
        assert template.default_duration_minutes == 90
        assert template.default_location == "Conference Room A"
        assert template.created_by_id == seed_user.id

    def test_create_template_agenda_item(self, db_session: Session, seed_user):
        """TemplateAgendaItem can be created with template_id, title, description, item_type, duration_minutes, order_index, is_regulatory."""
        from app.models.template import MeetingTemplate, TemplateAgendaItem

        template = MeetingTemplate(
            name="Test Template",
            created_by_id=seed_user.id,
        )
        db_session.add(template)
        db_session.commit()

        item = TemplateAgendaItem(
            template_id=template.id,
            title="Financial Report",
            description="Quarterly financial review",
            item_type="information",
            duration_minutes=15,
            order_index=0,
            is_regulatory=True,
        )
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        assert item.id is not None
        assert item.template_id == template.id
        assert item.title == "Financial Report"
        assert item.description == "Quarterly financial review"
        assert item.item_type == "information"
        assert item.duration_minutes == 15
        assert item.order_index == 0
        assert item.is_regulatory is True

    def test_template_items_relationship_ordered(self, db_session: Session, seed_user):
        """MeetingTemplate.items relationship loads TemplateAgendaItem ordered by order_index."""
        from app.models.template import MeetingTemplate, TemplateAgendaItem

        template = MeetingTemplate(
            name="Ordered Template",
            created_by_id=seed_user.id,
        )
        db_session.add(template)
        db_session.commit()

        # Add items out of order
        item_b = TemplateAgendaItem(
            template_id=template.id, title="Second Item", order_index=1
        )
        item_c = TemplateAgendaItem(
            template_id=template.id, title="Third Item", order_index=2
        )
        item_a = TemplateAgendaItem(
            template_id=template.id, title="First Item", order_index=0
        )
        db_session.add_all([item_b, item_c, item_a])
        db_session.commit()

        db_session.refresh(template)
        assert len(template.items) == 3
        assert template.items[0].title == "First Item"
        assert template.items[1].title == "Second Item"
        assert template.items[2].title == "Third Item"

    def test_delete_template_cascades_items(self, db_session: Session, seed_user):
        """Deleting a MeetingTemplate cascades to delete its TemplateAgendaItem records."""
        from app.models.template import MeetingTemplate, TemplateAgendaItem

        template = MeetingTemplate(
            name="Cascade Template",
            created_by_id=seed_user.id,
        )
        db_session.add(template)
        db_session.commit()

        item1 = TemplateAgendaItem(
            template_id=template.id, title="Item 1", order_index=0
        )
        item2 = TemplateAgendaItem(
            template_id=template.id, title="Item 2", order_index=1
        )
        db_session.add_all([item1, item2])
        db_session.commit()

        template_id = template.id
        db_session.delete(template)
        db_session.commit()

        remaining = db_session.query(TemplateAgendaItem).filter(
            TemplateAgendaItem.template_id == template_id
        ).all()
        assert len(remaining) == 0

    def test_is_regulatory_defaults_false(self, db_session: Session, seed_user):
        """TemplateAgendaItem.is_regulatory defaults to False."""
        from app.models.template import MeetingTemplate, TemplateAgendaItem

        template = MeetingTemplate(
            name="Default Test",
            created_by_id=seed_user.id,
        )
        db_session.add(template)
        db_session.commit()

        item = TemplateAgendaItem(
            template_id=template.id, title="Regular Item", order_index=0
        )
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)

        assert item.is_regulatory is False

    def test_is_active_defaults_true(self, db_session: Session, seed_user):
        """MeetingTemplate.is_active defaults to True."""
        from app.models.template import MeetingTemplate

        template = MeetingTemplate(
            name="Active Test",
            created_by_id=seed_user.id,
        )
        db_session.add(template)
        db_session.commit()
        db_session.refresh(template)

        assert template.is_active is True


# =============================================================================
# Fixtures for API Tests
# =============================================================================

@pytest.fixture
def seed_chair_user(db_session):
    """Create a non-admin board member for testing non-admin access."""
    user = BoardMember(
        email="chair@themany.com",
        name="Chair User",
        role="board",
    )
    db_session.add(user)
    db_session.commit()
    return user


# =============================================================================
# Template API Tests
# =============================================================================

class TestTemplateAPI:
    """Integration tests for the Template CRUD API."""

    @pytest.mark.asyncio
    async def test_list_templates(self, client, seed_template):
        """GET /api/templates returns list of active templates (any board member)."""
        response = await client.get(
            "/api/templates",
            headers={"X-User-Email": "test@themany.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        template = data[0]
        assert "name" in template
        assert "items_count" in template
        assert "has_regulatory_items" in template

    @pytest.mark.asyncio
    async def test_get_template_detail(self, client, seed_template):
        """GET /api/templates/{id} returns template with its agenda items."""
        response = await client.get(
            f"/api/templates/{seed_template.id}",
            headers={"X-User-Email": "test@themany.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Board Meeting"
        assert "items" in data
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_create_template_admin(self, client, seed_user):
        """POST /api/templates creates template with items (admin only)."""
        response = await client.post(
            "/api/templates",
            json={
                "name": "New Template",
                "description": "Test description",
                "items": [
                    {"title": "Item A", "order_index": 0, "is_regulatory": True},
                    {"title": "Item B", "order_index": 1},
                ],
            },
            headers={"X-User-Email": "test@themany.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Template"
        assert len(data["items"]) == 2
        assert data["items"][0]["is_regulatory"] is True

    @pytest.mark.asyncio
    async def test_create_template_non_admin_forbidden(self, client, seed_chair_user):
        """POST /api/templates returns 403 for non-admin user."""
        response = await client.post(
            "/api/templates",
            json={
                "name": "Forbidden Template",
                "items": [],
            },
            headers={"X-User-Email": "chair@themany.com"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_template(self, client, seed_template):
        """PATCH /api/templates/{id} updates template name/description (admin only)."""
        response = await client.patch(
            f"/api/templates/{seed_template.id}",
            json={"name": "Updated Name", "description": "Updated desc"},
            headers={"X-User-Email": "test@themany.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated desc"

    @pytest.mark.asyncio
    async def test_delete_template_soft_deletes(self, client, seed_template):
        """DELETE /api/templates/{id} soft-deletes (sets is_active=False, admin only)."""
        response = await client.delete(
            f"/api/templates/{seed_template.id}",
            headers={"X-User-Email": "test@themany.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["id"] == seed_template.id

        # Verify it's gone from the list
        list_response = await client.get(
            "/api/templates",
            headers={"X-User-Email": "test@themany.com"},
        )
        assert list_response.status_code == 200
        templates = list_response.json()
        template_ids = [t["id"] for t in templates]
        assert seed_template.id not in template_ids


class TestBatchMeetingCreation:
    """Integration tests for the batch meeting creation endpoint."""

    @pytest.mark.asyncio
    async def test_create_meeting_with_agenda_items(self, client, seed_user):
        """POST /api/meetings/with-agenda creates meeting with agenda items atomically."""
        future_date = (datetime.utcnow() + timedelta(days=7)).isoformat()
        response = await client.post(
            "/api/meetings/with-agenda",
            json={
                "title": "Test Meeting",
                "date": future_date,
                "duration_minutes": 60,
                "agenda_items": [
                    {"title": "Opening", "item_type": "information", "duration_minutes": 5},
                    {"title": "Discussion", "item_type": "discussion", "duration_minutes": 30},
                ],
            },
            headers={"X-User-Email": "test@themany.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Meeting"
        assert "agenda_items" in data
        assert len(data["agenda_items"]) == 2

    @pytest.mark.asyncio
    async def test_create_meeting_from_template(self, client, seed_template):
        """POST /api/meetings/with-agenda with template_id pre-populates from template."""
        future_date = (datetime.utcnow() + timedelta(days=7)).isoformat()
        response = await client.post(
            "/api/meetings/with-agenda",
            json={
                "title": "Template Meeting",
                "date": future_date,
                "template_id": seed_template.id,
            },
            headers={"X-User-Email": "test@themany.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Template Meeting"
        assert len(data["agenda_items"]) == 2  # From seed_template fixture

    @pytest.mark.asyncio
    async def test_create_meeting_with_agenda_creates_audit_log(self, client, seed_user, db_session):
        """POST /api/meetings/with-agenda creates AuditLog entry."""
        from app.models.audit import AuditLog

        future_date = (datetime.utcnow() + timedelta(days=7)).isoformat()
        response = await client.post(
            "/api/meetings/with-agenda",
            json={
                "title": "Audited Meeting",
                "date": future_date,
                "agenda_items": [
                    {"title": "Item", "duration_minutes": 10},
                ],
            },
            headers={"X-User-Email": "test@themany.com"},
        )
        assert response.status_code == 200

        logs = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "meeting",
            AuditLog.action == "create",
        ).all()
        assert len(logs) >= 1

    @pytest.mark.asyncio
    async def test_create_meeting_with_agenda_uses_require_chair(self, client, seed_user):
        """POST /api/meetings/with-agenda uses require_chair auth (board+ can create)."""
        # Without auth header should return 401
        response = await client.post(
            "/api/meetings/with-agenda",
            json={
                "title": "No Auth",
                "date": datetime.utcnow().isoformat(),
                "agenda_items": [],
            },
        )
        assert response.status_code == 401
