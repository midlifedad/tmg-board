"""Add resolution_signatures table

Revision ID: 007_add_resolution_signatures
Revises: 006_add_transcripts
Create Date: 2026-03-05

Adds resolution_signatures table for digitally signing board resolutions.
Each board member can sign a resolution once (UniqueConstraint on decision_id + member_id).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '007_add_resolution_signatures'
down_revision = '006_add_transcripts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'resolution_signatures',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('decision_id', sa.Integer(),
                  sa.ForeignKey('decisions.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('member_id', sa.Integer(),
                  sa.ForeignKey('board_members.id'),
                  nullable=False),
        sa.Column('signed_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('signature_hash', sa.String(64), nullable=False),
        sa.UniqueConstraint('decision_id', 'member_id',
                            name='uq_resolution_member_signature'),
    )


def downgrade() -> None:
    op.drop_table('resolution_signatures')
