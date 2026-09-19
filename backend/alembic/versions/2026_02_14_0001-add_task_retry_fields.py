"""Add retry_count and last_failed_at to tasks

Revision ID: add_task_retry_fields
Revises: fix_generation_failed_case
Create Date: 2026-02-14

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_task_retry_fields'
down_revision = 'fix_generation_failed_case'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('tasks', sa.Column('last_failed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'last_failed_at')
    op.drop_column('tasks', 'retry_count')
