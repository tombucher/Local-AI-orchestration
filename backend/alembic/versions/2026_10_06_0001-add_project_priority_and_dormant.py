"""Priorité des projets, date de reprise, état « en sommeil »

Revision ID: add_project_priority
Revises: add_project_space
Create Date: 2026-10-06
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_project_priority'
down_revision = 'add_project_space'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Une valeur d'enum Postgres s'ajoute hors transaction
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'DORMANT'")
    op.add_column('projects', sa.Column('priority_rank', sa.Integer(), nullable=True))
    op.add_column('projects', sa.Column('resume_on', sa.Date(), nullable=True))
    op.create_index('ix_projects_priority_rank', 'projects', ['priority_rank'])


def downgrade() -> None:
    # Postgres ne retire pas une valeur d'enum : DORMANT reste déclarée
    op.drop_index('ix_projects_priority_rank', table_name='projects')
    op.drop_column('projects', 'resume_on')
    op.drop_column('projects', 'priority_rank')
