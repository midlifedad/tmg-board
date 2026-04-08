"""Add document_templates and meeting_minutes tables

Revision ID: 005_add_document_templates_and_meeting_minutes
Revises: 004_add_timezone_support
Create Date: 2026-04-07

Adds DocumentTemplate and MeetingMinutes tables.
Seeds a default meeting_minutes template with a professional board secretary prompt.
"""
from alembic import op
import sqlalchemy as sa


revision = '005_add_document_templates_and_meeting_minutes'
down_revision = '004_add_timezone_support'
branch_labels = None
depends_on = None

DEFAULT_SYSTEM_PROMPT = (
    "You are a professional board secretary generating formal meeting minutes. "
    "Output clean, well-structured markdown suitable for a board of directors. "
    "Be concise and factual. Use the transcript to extract discussions, decisions, "
    "and action items."
)

DEFAULT_USER_PROMPT_TEMPLATE = """# Meeting Minutes Request

**Meeting:** {{ meeting.title }}
**Date:** {{ meeting.date }}
**Location:** {{ meeting.location }}

## Attendees
{% for attendee in attendees %}
- {{ attendee.name }}
{% endfor %}

## Agenda
{% for item in agenda_items %}
{{ item.order }}. {{ item.title }} ({{ item.type }}){% if item.presenter %} — Presented by {{ item.presenter }}{% endif %}

{% endfor %}

## Transcript
{{ transcript }}

---

Please generate formal meeting minutes from the above transcript following this structure:
1. Meeting called to order / opening
2. Attendance / quorum
3. Agenda items covered (one section per agenda item)
4. Decisions made
5. Action items with responsible parties
6. Adjournment"""


def upgrade() -> None:
    # Create document_templates table
    op.create_table(
        'document_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('template_type', sa.String(50), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('user_prompt_template', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_document_templates_id'), 'document_templates', ['id'], unique=False)

    # Create meeting_minutes table
    op.create_table(
        'meeting_minutes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('meeting_id', sa.Integer(), nullable=False),
        sa.Column('content_markdown', sa.Text(), nullable=False),
        sa.Column('generated_by_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['generated_by_id'], ['board_members.id']),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id']),
        sa.ForeignKeyConstraint(['template_id'], ['document_templates.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('meeting_id'),
    )
    op.create_index(op.f('ix_meeting_minutes_id'), 'meeting_minutes', ['id'], unique=False)

    # Seed default meeting_minutes template
    document_templates = sa.table(
        'document_templates',
        sa.column('name', sa.String),
        sa.column('template_type', sa.String),
        sa.column('system_prompt', sa.Text),
        sa.column('user_prompt_template', sa.Text),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )
    from datetime import datetime
    now = datetime.utcnow()
    op.bulk_insert(document_templates, [
        {
            'name': 'Meeting Minutes',
            'template_type': 'meeting_minutes',
            'system_prompt': DEFAULT_SYSTEM_PROMPT,
            'user_prompt_template': DEFAULT_USER_PROMPT_TEMPLATE,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        }
    ])


def downgrade() -> None:
    # Drop in reverse order (meeting_minutes has FK to document_templates)
    op.drop_index(op.f('ix_meeting_minutes_id'), table_name='meeting_minutes')
    op.drop_table('meeting_minutes')
    op.drop_index(op.f('ix_document_templates_id'), table_name='document_templates')
    op.drop_table('document_templates')
