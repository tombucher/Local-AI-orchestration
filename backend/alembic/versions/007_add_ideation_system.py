"""Add ideation system

Revision ID: 007
Revises: 006
Create Date: 2026-01-03 06:30:00.000000

Migration pour ajouter le système d'idéation socratique:
- Nouveaux statuts de projet: IDEATION, PLANNING
- Champs ideation dans la table projects
- Nouvelle table ideation_messages pour stocker le dialogue
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_add_ideation_system'
down_revision = '006_add_daily_reports'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Migration UP: Ajoute le système d'idéation
    """

    # 1. Créer le nouvel enum ProjectStatus avec IDEATION et PLANNING
    # Note: PostgreSQL nécessite une approche spéciale pour modifier un enum
    op.execute("ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'ideation'")
    op.execute("ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'planning'")

    # 2. Ajouter les nouveaux champs au modèle Project
    op.add_column('projects', sa.Column('ideation_transcript', sa.JSON(), nullable=True))
    op.add_column('projects', sa.Column('ideation_context', sa.JSON(), nullable=True))
    op.add_column('projects', sa.Column('ideation_completed_at', sa.DateTime(timezone=True), nullable=True))

    # 3. Créer l'enum MessageRole
    message_role_enum = postgresql.ENUM('user', 'assistant', 'system', name='messagerole', create_type=True)
    message_role_enum.create(op.get_bind())

    # 4. Créer la table ideation_messages
    op.create_table(
        'ideation_messages',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('role', postgresql.ENUM('user', 'assistant', 'system', name='messagerole', create_type=False), nullable=False, index=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('meta', sa.JSON(), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, index=True),
    )

    # 5. Créer un index composite pour accélérer les requêtes de conversation
    op.create_index(
        'ix_ideation_messages_project_created',
        'ideation_messages',
        ['project_id', 'created_at'],
        unique=False
    )

    print("✅ Migration 007: Système d'idéation ajouté avec succès")


def downgrade() -> None:
    """
    Migration DOWN: Supprime le système d'idéation
    """

    # 1. Supprimer l'index composite
    op.drop_index('ix_ideation_messages_project_created', table_name='ideation_messages')

    # 2. Supprimer la table ideation_messages
    op.drop_table('ideation_messages')

    # 3. Supprimer l'enum MessageRole
    message_role_enum = postgresql.ENUM('user', 'assistant', 'system', name='messagerole')
    message_role_enum.drop(op.get_bind())

    # 4. Supprimer les colonnes ideation du modèle Project
    op.drop_column('projects', 'ideation_completed_at')
    op.drop_column('projects', 'ideation_context')
    op.drop_column('projects', 'ideation_transcript')

    # Note: On ne peut pas facilement supprimer des valeurs d'un enum PostgreSQL
    # Les valeurs 'ideation' et 'planning' resteront dans l'enum mais ne seront pas utilisées

    print("✅ Migration 007: Système d'idéation supprimé (statuts enum conservés)")
