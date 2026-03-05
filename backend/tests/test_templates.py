"""Tests for MeetingTemplate and TemplateAgendaItem models and API."""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session


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
