"""Add transcript support, drop recording_url

Revision ID: 006_add_transcripts
Revises: 005_add_meeting_templates
Create Date: 2026-03-05

Adds meeting_transcripts table (one-per-meeting transcript storage),
meeting_documents junction table, and drops the deprecated recording_url
column from meetings.
"""
from alembic import op
import sqlalchemy as sa


revision = '006_add_transcripts'
down_revision = '005_add_meeting_templates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create meeting_transcripts table
    op.create_table(
        'meeting_transcripts',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('meeting_id', sa.Integer(),
                  sa.ForeignKey('meetings.id', ondelete='CASCADE'),
                  nullable=False, unique=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source', sa.String(20), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=True),
        sa.Column('char_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by_id', sa.Integer(),
                  sa.ForeignKey('board_members.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Create meeting_documents junction table
    op.create_table(
        'meeting_documents',
        sa.Column('meeting_id', sa.Integer(),
                  sa.ForeignKey('meetings.id', ondelete='CASCADE'),
                  primary_key=True),
        sa.Column('document_id', sa.Integer(),
                  sa.ForeignKey('documents.id', ondelete='CASCADE'),
                  primary_key=True),
        sa.Column('relationship_type', sa.String(30), nullable=False),
        sa.Column('created_by_id', sa.Integer(),
                  sa.ForeignKey('board_members.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Drop recording_url from meetings
    op.drop_column('meetings', 'recording_url')


def downgrade() -> None:
    op.add_column('meetings',
                  sa.Column('recording_url', sa.Text(), nullable=True))
    op.drop_table('meeting_documents')
    op.drop_table('meeting_transcripts')
