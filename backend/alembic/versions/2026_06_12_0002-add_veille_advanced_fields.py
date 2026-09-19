"""Veille avancée : deadlines de financement + références visuelles

- veille_results : deadline (triable), image_url/thumbnail_url/license (moodboard)
- enum veilleresulttype : + visual_reference
- enum veillescope : + visual

Revision ID: add_veille_advanced_fields
Revises: add_task_due_date
Create Date: 2026-06-12

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_veille_advanced_fields'
down_revision = 'add_task_due_date'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('veille_results', sa.Column('deadline', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_veille_results_deadline', 'veille_results', ['deadline'])
    op.add_column('veille_results', sa.Column('image_url', sa.String(1000), nullable=True))
    op.add_column('veille_results', sa.Column('thumbnail_url', sa.String(1000), nullable=True))
    op.add_column('veille_results', sa.Column('license', sa.String(100), nullable=True))

    # PostgreSQL : ajout de valeurs d'enum (cf. 004_add_missing_event_types)
    op.execute("ALTER TYPE veilleresulttype ADD VALUE IF NOT EXISTS 'visual_reference'")
    op.execute("ALTER TYPE veillescope ADD VALUE IF NOT EXISTS 'visual'")


def downgrade() -> None:
    op.drop_column('veille_results', 'license')
    op.drop_column('veille_results', 'thumbnail_url')
    op.drop_column('veille_results', 'image_url')
    op.drop_index('ix_veille_results_deadline', table_name='veille_results')
    op.drop_column('veille_results', 'deadline')
    # Les valeurs d'enum ne sont pas retirables sans recréer le type
