"""Projets tenus dans des dossiers du Mac (fiche .md par projet)

Revision ID: add_project_folders
Revises: add_project_documents
Create Date: 2026-09-27
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_project_folders'
down_revision = 'add_project_documents'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('source_path', sa.String(length=1000), nullable=True))
    op.add_column('projects', sa.Column('source_hash', sa.String(length=64), nullable=True))
    op.create_index('ix_projects_source_path', 'projects', ['source_path'])
    op.add_column('user_settings', sa.Column('projects_folder', sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column('user_settings', 'projects_folder')
    op.drop_index('ix_projects_source_path', table_name='projects')
    op.drop_column('projects', 'source_hash')
    op.drop_column('projects', 'source_path')
