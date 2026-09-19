"""Refactor veille system: unified VEILLE type + radar_report + recurrence

Revision ID: refactor_veille_unified
Revises: add_task_retry_fields
Create Date: 2026-02-15

Changes:
- Add 'veille' value to tasktype enum
- Migrate existing veille_tech/veille_cultural/veille_events tasks to 'veille'
- Add radar_report (JSON) column to tasks
- Add veille_topic_id (FK) column to tasks
- Add refinement_history (JSON) column to veille_topics
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'refactor_veille_unified'
down_revision = 'add_task_retry_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add 'veille' to tasktype enum
    # PostgreSQL requires a special approach: can't use ADD VALUE inside a transaction
    # so we commit the current transaction first
    op.execute("COMMIT")
    op.execute("ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'veille'")
    # Start a new transaction for the rest
    op.execute("BEGIN")

    # 2. Migrate existing veille tasks to unified type
    op.execute("""
        UPDATE tasks
        SET task_type = 'veille'
        WHERE task_type IN ('veille_tech', 'veille_cultural', 'veille_events')
    """)

    # 3. Add radar_report column to tasks (structured JSON report)
    op.add_column('tasks', sa.Column('radar_report', sa.JSON(), nullable=True))

    # 4. Add veille_topic_id FK to tasks (links veille task to its topic for recurrence)
    op.add_column('tasks', sa.Column(
        'veille_topic_id',
        sa.Integer(),
        sa.ForeignKey('veille_topics.id', ondelete='SET NULL'),
        nullable=True
    ))

    # 5. Add refinement_history to veille_topics (tracks user adjustments over time)
    op.add_column('veille_topics', sa.Column(
        'refinement_history',
        sa.JSON(),
        nullable=True,
        server_default='[]'
    ))


def downgrade() -> None:
    # Remove new columns
    op.drop_column('veille_topics', 'refinement_history')
    op.drop_column('tasks', 'veille_topic_id')
    op.drop_column('tasks', 'radar_report')

    # Revert task types (best effort - map back to veille_tech as default)
    op.execute("""
        UPDATE tasks
        SET task_type = 'veille_tech'
        WHERE task_type = 'veille'
    """)
    # Note: Cannot remove 'veille' from PostgreSQL enum - it stays as unused value
