"""Create configuration table

Revision ID: 001_create_config
Create Date: 2025-09-01
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'configuration',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(50), nullable=False),
        sa.Column('value', sa.String(500)),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )

def downgrade():
    op.drop_table('configuration')
