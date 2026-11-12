"""Historique des descriptions de projet réécrites à partir d'une réponse

Revision ID: add_project_description_history
Revises: add_task_user_notes
Create Date: 2026-11-12
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_project_description_history'
down_revision = 'add_task_user_notes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('description_history', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'description_history')
