"""Add missing audit_log columns

Revision ID: 002_add_audit_columns
Revises: 001_add_crud_columns
Create Date: 2026-01-24

Adds entity_name, ip_address, user_agent columns to audit_log table.
"""
from alembic import op
import sqlalchemy as sa


revision = '002_add_audit_columns'
down_revision = '001_add_crud_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('audit_log', sa.Column('entity_name', sa.String(255), nullable=True))
    op.add_column('audit_log', sa.Column('ip_address', sa.String(45), nullable=True))
    op.add_column('audit_log', sa.Column('user_agent', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('audit_log', 'user_agent')
    op.drop_column('audit_log', 'ip_address')
    op.drop_column('audit_log', 'entity_name')
