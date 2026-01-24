"""Add columns for Full CRUD/RBAC phases 2-5

Revision ID: 001_add_crud_columns
Revises:
Create Date: 2026-01-24

Adds new columns to existing tables that were added in phases 2-5.
SQLAlchemy create_all() only creates new tables, not new columns.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_crud_columns'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Phase 2: Documents - version tracking and archive
    op.add_column('documents', sa.Column('current_version', sa.Integer(), nullable=True, server_default='1'))
    op.add_column('documents', sa.Column('archived_at', sa.DateTime(), nullable=True))
    op.add_column('documents', sa.Column('archived_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_documents_archived_by', 'documents', 'board_members', ['archived_by_id'], ['id'])

    # Phase 3: Meetings - lifecycle tracking
    op.add_column('meetings', sa.Column('duration_minutes', sa.Integer(), nullable=True))
    op.add_column('meetings', sa.Column('started_at', sa.DateTime(), nullable=True))
    op.add_column('meetings', sa.Column('ended_at', sa.DateTime(), nullable=True))
    op.add_column('meetings', sa.Column('recording_url', sa.Text(), nullable=True))

    # Phase 4: Decisions - visibility and archive
    op.add_column('decisions', sa.Column('visibility', sa.String(20), nullable=True, server_default='standard'))
    op.add_column('decisions', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('decisions', sa.Column('archived_at', sa.DateTime(), nullable=True))
    op.add_column('decisions', sa.Column('archived_by_id', sa.Integer(), nullable=True))
    op.add_column('decisions', sa.Column('archived_reason', sa.Text(), nullable=True))
    op.create_foreign_key('fk_decisions_archived_by', 'decisions', 'board_members', ['archived_by_id'], ['id'])

    # Phase 5: Ideas - category and status reason
    op.add_column('ideas', sa.Column('category_id', sa.Integer(), nullable=True))
    op.add_column('ideas', sa.Column('status_reason', sa.Text(), nullable=True))
    op.create_foreign_key('fk_ideas_category', 'ideas', 'idea_categories', ['category_id'], ['id'])

    # Phase 5: Comments - threading, pinning, editing
    op.add_column('comments', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.add_column('comments', sa.Column('is_pinned', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('comments', sa.Column('edited_at', sa.DateTime(), nullable=True))
    op.create_foreign_key('fk_comments_parent', 'comments', 'comments', ['parent_id'], ['id'])


def downgrade() -> None:
    # Phase 5: Comments
    op.drop_constraint('fk_comments_parent', 'comments', type_='foreignkey')
    op.drop_column('comments', 'edited_at')
    op.drop_column('comments', 'is_pinned')
    op.drop_column('comments', 'parent_id')

    # Phase 5: Ideas
    op.drop_constraint('fk_ideas_category', 'ideas', type_='foreignkey')
    op.drop_column('ideas', 'status_reason')
    op.drop_column('ideas', 'category_id')

    # Phase 4: Decisions
    op.drop_constraint('fk_decisions_archived_by', 'decisions', type_='foreignkey')
    op.drop_column('decisions', 'archived_reason')
    op.drop_column('decisions', 'archived_by_id')
    op.drop_column('decisions', 'archived_at')
    op.drop_column('decisions', 'updated_at')
    op.drop_column('decisions', 'visibility')

    # Phase 3: Meetings
    op.drop_column('meetings', 'recording_url')
    op.drop_column('meetings', 'ended_at')
    op.drop_column('meetings', 'started_at')
    op.drop_column('meetings', 'duration_minutes')

    # Phase 2: Documents
    op.drop_constraint('fk_documents_archived_by', 'documents', type_='foreignkey')
    op.drop_column('documents', 'archived_by_id')
    op.drop_column('documents', 'archived_at')
    op.drop_column('documents', 'current_version')
