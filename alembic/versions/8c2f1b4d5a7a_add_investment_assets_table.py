"""add investment_assets table

Revision ID: 8c2f1b4d5a7a
Revises: 7a9d3b1f4c2c
Create Date: 2026-06-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8c2f1b4d5a7a'
down_revision = '7a9d3b1f4c2c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'investment_assets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('target', sa.Float(), nullable=True),
        sa.Column('sector', sa.String(), nullable=True),
        sa.Column('group', sa.String(), nullable=True),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
    )
    op.create_index(op.f('ix_investment_assets_company'), 'investment_assets', ['company'], unique=False)
    op.create_index(op.f('ix_investment_assets_ticker'), 'investment_assets', ['ticker'], unique=False)
    op.create_index(op.f('ix_investment_assets_owner_id'), 'investment_assets', ['owner_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_investment_assets_owner_id'), table_name='investment_assets')
    op.drop_index(op.f('ix_investment_assets_ticker'), table_name='investment_assets')
    op.drop_index(op.f('ix_investment_assets_company'), table_name='investment_assets')
    op.drop_table('investment_assets')
