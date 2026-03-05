"""Add meeting templates

Revision ID: 005_add_meeting_templates
Revises: 004_add_timezone_support
Create Date: 2026-03-05

Adds meeting_templates and template_agenda_items tables for reusable
meeting templates with pre-defined agenda items.
"""
from alembic import op
import sqlalchemy as sa


revision = '005_add_meeting_templates'
down_revision = '004_add_timezone_support'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'meeting_templates',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('default_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('default_location', sa.String(255), nullable=True),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('board_members.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
    )

    op.create_table(
        'template_agenda_items',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('template_id', sa.Integer(), sa.ForeignKey('meeting_templates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('item_type', sa.String(30), server_default='information', nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('is_regulatory', sa.Boolean(), server_default='0', nullable=False),
    )


def downgrade() -> None:
    op.drop_table('template_agenda_items')
    op.drop_table('meeting_templates')
