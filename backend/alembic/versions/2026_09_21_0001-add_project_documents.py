"""Espace documents par projet

Table `project_documents` : notes, extraits de code et images de référence que
l'utilisateur dépose pour que l'orchestrateur en tienne compte. Les images sont
stockées en binaire — les modèles locaux installés annoncent la capacité vision.

Revision ID: add_project_documents
Revises: add_rss_feeds
Create Date: 2026-09-21

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_project_documents'
down_revision = 'add_rss_feeds'
branch_labels = None
depends_on = None

document_kind = sa.Enum('text', 'code', 'image', name='documentkind')


def upgrade() -> None:
    document_kind.create(op.get_bind(), checkfirst=True)
    op.create_table(
        'project_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('kind', document_kind, nullable=False, server_default='text'),
        sa.Column('mime_type', sa.String(length=100), nullable=False, server_default='text/plain'),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('binary', sa.LargeBinary(), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('note', sa.String(length=500), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_project_documents_id'), 'project_documents', ['id'])
    op.create_index(op.f('ix_project_documents_project_id'), 'project_documents', ['project_id'])
    op.create_index(op.f('ix_project_documents_kind'), 'project_documents', ['kind'])
    op.create_index(op.f('ix_project_documents_enabled'), 'project_documents', ['enabled'])


def downgrade() -> None:
    op.drop_index(op.f('ix_project_documents_enabled'), table_name='project_documents')
    op.drop_index(op.f('ix_project_documents_kind'), table_name='project_documents')
    op.drop_index(op.f('ix_project_documents_project_id'), table_name='project_documents')
    op.drop_index(op.f('ix_project_documents_id'), table_name='project_documents')
    op.drop_table('project_documents')
    document_kind.drop(op.get_bind(), checkfirst=True)
