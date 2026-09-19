"""add veille system (topics, results, task types)

Revision ID: 005_add_veille_system
Revises: 004_add_missing_event_types
Create Date: 2026-01-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_add_veille_system'
down_revision = '004_add_missing_event_types'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Les enums sont créés automatiquement par SQLAlchemy lors de create_table()
    # Pas besoin de les créer manuellement

    # Create veille_topics table
    op.create_table(
        'veille_topics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('scope', sa.Enum('tech', 'funding', 'cultural', 'academic', 'news', 'collaboration', name='veillescope'), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('keywords', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('excluded_keywords', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('location_filters', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('date_filters', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('sources', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('scan_frequency', sa.String(length=50), nullable=False),
        sa.Column('min_relevance_score', sa.Integer(), nullable=True),
        sa.Column('last_scan', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_scan', sa.DateTime(timezone=True), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_veille_topics_id'), 'veille_topics', ['id'], unique=False)
    op.create_index(op.f('ix_veille_topics_project_id'), 'veille_topics', ['project_id'], unique=False)
    op.create_index(op.f('ix_veille_topics_scope'), 'veille_topics', ['scope'], unique=False)
    op.create_index(op.f('ix_veille_topics_enabled'), 'veille_topics', ['enabled'], unique=False)

    # Create veille_results table
    op.create_table(
        'veille_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('topic_id', sa.Integer(), nullable=False),
        sa.Column('result_type', sa.Enum('funding_opportunity', 'tech_article', 'tech_tool', 'event', 'collaboration', 'academic_paper', 'news_article', 'artist_work', 'call_for_proposals', name='veilleresulttype'), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('url', sa.String(length=1000), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ai_summary', sa.Text(), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=False),
        sa.Column('key_points', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('relevance_reason', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('source', sa.String(length=255), nullable=True),
        sa.Column('source_platform', sa.String(length=100), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('found_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('status', sa.Enum('new', 'read', 'saved', 'actionable', 'dismissed', name='veilleresultstatus'), nullable=False),
        sa.Column('user_notes', sa.Text(), nullable=True),
        sa.Column('user_rating', sa.Integer(), nullable=True),
        sa.Column('task_created', sa.Boolean(), nullable=True),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['topic_id'], ['veille_topics.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_veille_results_id'), 'veille_results', ['id'], unique=False)
    op.create_index(op.f('ix_veille_results_topic_id'), 'veille_results', ['topic_id'], unique=False)
    op.create_index(op.f('ix_veille_results_result_type'), 'veille_results', ['result_type'], unique=False)
    op.create_index(op.f('ix_veille_results_found_at'), 'veille_results', ['found_at'], unique=False)
    op.create_index(op.f('ix_veille_results_status'), 'veille_results', ['status'], unique=False)

    # Add task_type column to tasks table
    op.add_column('tasks', sa.Column('task_type', sa.Enum('code_generation', 'document_writing', 'funding_search', 'veille_tech', 'veille_cultural', 'veille_events', 'administrative', 'research', name='tasktype'), nullable=False, server_default='code_generation'))
    op.create_index(op.f('ix_tasks_task_type'), 'tasks', ['task_type'], unique=False)


def downgrade() -> None:
    # Remove task_type column and index
    op.drop_index(op.f('ix_tasks_task_type'), table_name='tasks')
    op.drop_column('tasks', 'task_type')

    # Drop veille_results table and indexes
    op.drop_index(op.f('ix_veille_results_status'), table_name='veille_results')
    op.drop_index(op.f('ix_veille_results_found_at'), table_name='veille_results')
    op.drop_index(op.f('ix_veille_results_result_type'), table_name='veille_results')
    op.drop_index(op.f('ix_veille_results_topic_id'), table_name='veille_results')
    op.drop_index(op.f('ix_veille_results_id'), table_name='veille_results')
    op.drop_table('veille_results')

    # Drop veille_topics table and indexes
    op.drop_index(op.f('ix_veille_topics_enabled'), table_name='veille_topics')
    op.drop_index(op.f('ix_veille_topics_scope'), table_name='veille_topics')
    op.drop_index(op.f('ix_veille_topics_project_id'), table_name='veille_topics')
    op.drop_index(op.f('ix_veille_topics_id'), table_name='veille_topics')
    op.drop_table('veille_topics')

    # Drop enums (les enums sont automatiquement supprimés par SQLAlchemy en mode CASCADE)
    op.execute('DROP TYPE IF EXISTS tasktype CASCADE')
    op.execute('DROP TYPE IF EXISTS veilleresultstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS veilleresulttype CASCADE')
    op.execute('DROP TYPE IF EXISTS veillescope CASCADE')
