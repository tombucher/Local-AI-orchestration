"""Fix GENERATION_FAILED enum case mismatch in taskeventtype

The migration 004 added 'generation_failed' (lowercase) but SQLAlchemy
sends enum member names in UPPERCASE (matching the convention of all other
values: CREATED, CODE_GENERATED, etc.). This migration adds the uppercase
version to fix the mismatch.

Revision ID: fix_generation_failed_case
Revises: dfb94a7cfccc
Create Date: 2026-02-06

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'fix_generation_failed_case'
down_revision = 'dfb94a7cfccc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add uppercase GENERATION_FAILED to match SQLAlchemy enum naming convention
    # The lowercase 'generation_failed' from migration 004 remains but is unused
    # PostgreSQL does not support removing individual enum values
    op.execute("ALTER TYPE taskeventtype ADD VALUE IF NOT EXISTS 'GENERATION_FAILED'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values directly
    # The uppercase value will remain harmless if downgraded
    pass
