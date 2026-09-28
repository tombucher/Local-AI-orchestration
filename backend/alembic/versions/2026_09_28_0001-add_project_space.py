"""Espace d'un projet (Recherche, Pro, Mairie…) = dossier parent de sa fiche

Revision ID: add_project_space
Revises: add_project_folders
Create Date: 2026-09-28
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_project_space'
down_revision = 'add_project_folders'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('space', sa.String(length=120), nullable=True))
    op.create_index('ix_projects_space', 'projects', ['space'])


def downgrade() -> None:
    op.drop_index('ix_projects_space', table_name='projects')
    op.drop_column('projects', 'space')
