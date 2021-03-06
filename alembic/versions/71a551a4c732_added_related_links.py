"""added related links

Revision ID: 71a551a4c732
Revises: 
Create Date: 2020-08-02 00:15:42.217989

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '71a551a4c732'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('related',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('related_to_id', sa.Integer(), nullable=True),
    sa.Column('remote_id', sa.Integer(), nullable=True),
    sa.Column('url', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['related_to_id'], ['remote_post.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['remote_id'], ['remote_post.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_index('idx_remote_posts', table_name='remote_post')
    op.alter_column('remote_post', 'remote_id', new_column_name='original_id')
    op.create_index('idx_remote_posts', 'remote_post', ['source_id', 'original_id'], unique=True)


def downgrade():
    op.drop_index('idx_remote_posts', table_name='remote_post')
    op.alter_column('remote_post', 'original_id', new_column_name='remote_id')
    op.create_index('idx_remote_posts', 'remote_post', ['source_id', 'remote_id'], unique=True)
    op.drop_table('related')
