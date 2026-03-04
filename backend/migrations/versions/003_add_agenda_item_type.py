"""Add item_type column to agenda_items

Revision ID: 003_add_agenda_item_type
Revises: 002_add_audit_columns
Create Date: 2026-03-03

Adds item_type column to agenda_items table.
Valid values: information, discussion, decision_required, consent_agenda.
"""
from alembic import op
import sqlalchemy as sa


revision = '003_add_agenda_item_type'
down_revision = '002_add_audit_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('agenda_items', sa.Column('item_type', sa.String(30), nullable=False, server_default='information'))


def downgrade() -> None:
    op.drop_column('agenda_items', 'item_type')
