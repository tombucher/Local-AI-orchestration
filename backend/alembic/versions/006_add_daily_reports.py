"""Add daily_reports table

Revision ID: 006_add_daily_reports
Revises: 005_add_veille_system
Create Date: 2026-01-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision = '006_add_daily_reports'
down_revision = '005_add_veille_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create daily_reports table."""
    op.create_table(
        'daily_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('total_projects', sa.Integer(), server_default='0'),
        sa.Column('active_projects', sa.Integer(), server_default='0'),
        sa.Column('total_tasks', sa.Integer(), server_default='0'),
        sa.Column('completed_today', sa.Integer(), server_default='0'),
        sa.Column('blockers_count', sa.Integer(), server_default='0'),
        sa.Column('projects_analysis', JSON, nullable=True),
        sa.Column('top_priorities', JSON, nullable=True),
        sa.Column('recommendations', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Créer les index
    op.create_index('ix_daily_reports_id', 'daily_reports', ['id'])
    op.create_index('ix_daily_reports_user_id', 'daily_reports', ['user_id'])
    op.create_index('ix_daily_reports_date', 'daily_reports', ['date'])

    # Index composite pour recherche user + date
    op.create_index('ix_daily_reports_user_date', 'daily_reports', ['user_id', 'date'], unique=True)


def downgrade() -> None:
    """Drop daily_reports table."""
    op.drop_index('ix_daily_reports_user_date')
    op.drop_index('ix_daily_reports_date')
    op.drop_index('ix_daily_reports_user_id')
    op.drop_index('ix_daily_reports_id')
    op.drop_table('daily_reports')
