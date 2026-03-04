"""Add timezone support

Revision ID: 004_add_timezone_support
Revises: 003_add_agenda_item_type
Create Date: 2026-03-04

Adds timezone column to board_members and seeds default_timezone setting.
"""
from alembic import op
import sqlalchemy as sa


revision = '004_add_timezone_support'
down_revision = '003_add_agenda_item_type'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add per-user timezone preference (null = use org default)
    op.add_column('board_members', sa.Column('timezone', sa.String(50), nullable=True))

    # Seed org default timezone setting
    settings = sa.table('settings',
        sa.column('key', sa.String),
        sa.column('value', sa.Text),
    )
    op.bulk_insert(settings, [
        {'key': 'default_timezone', 'value': 'America/Los_Angeles'},
    ])


def downgrade() -> None:
    op.drop_column('board_members', 'timezone')
    op.execute("DELETE FROM settings WHERE key = 'default_timezone'")
