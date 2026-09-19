"""Add due_date to tasks (ancre du Gantt et des nudges de deadline)

Revision ID: add_task_due_date
Revises: refactor_veille_unified
Create Date: 2026-06-12

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_task_due_date'
down_revision = 'refactor_veille_unified'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('due_date', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_tasks_due_date', 'tasks', ['due_date'])


def downgrade() -> None:
    op.drop_index('ix_tasks_due_date', table_name='tasks')
    op.drop_column('tasks', 'due_date')
