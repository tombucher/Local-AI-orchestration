"""Réponse de l'utilisateur sur une tâche terminée (user_notes)

Revision ID: add_task_user_notes
Revises: add_project_priority
Create Date: 2026-11-12
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_task_user_notes'
down_revision = 'add_project_priority'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('user_notes', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'user_notes')
