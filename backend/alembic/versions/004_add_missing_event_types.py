"""add missing event types to taskeventtype enum

Revision ID: 004_add_missing_event_types
Revises: 003_add_user_settings
Create Date: 2026-01-01

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_add_missing_event_types'
down_revision = '003_add_user_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing enum values to taskeventtype
    # PostgreSQL requires special handling for enum types
    op.execute("ALTER TYPE taskeventtype ADD VALUE IF NOT EXISTS 'generation_started'")
    op.execute("ALTER TYPE taskeventtype ADD VALUE IF NOT EXISTS 'generation_failed'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # You would need to recreate the enum type if you want to remove values
    pass
