"""Bibliothèque de flux RSS par utilisateur

Table `rss_feeds` : sources que l'utilisateur ajoute au fil de ses recherches.
Étiquettes déduites du contenu pour que la veille choisisse les bonnes sources,
et état de la dernière vérification pour repérer les flux morts.

Revision ID: add_rss_feeds
Revises: add_veille_advanced_fields
Create Date: 2026-09-20

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_rss_feeds'
down_revision = 'add_veille_advanced_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'rss_feeds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=1000), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('last_checked', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_status', sa.String(length=255), nullable=True),
        sa.Column('last_entry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'url', name='uq_rss_feeds_user_url'),
    )
    op.create_index(op.f('ix_rss_feeds_id'), 'rss_feeds', ['id'])
    op.create_index(op.f('ix_rss_feeds_user_id'), 'rss_feeds', ['user_id'])
    op.create_index(op.f('ix_rss_feeds_enabled'), 'rss_feeds', ['enabled'])


def downgrade() -> None:
    op.drop_index(op.f('ix_rss_feeds_enabled'), table_name='rss_feeds')
    op.drop_index(op.f('ix_rss_feeds_user_id'), table_name='rss_feeds')
    op.drop_index(op.f('ix_rss_feeds_id'), table_name='rss_feeds')
    op.drop_table('rss_feeds')
