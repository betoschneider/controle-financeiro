"""add_purchase_price_and_transactions

Revision ID: 5f9c3a7b2d1e
Revises: bb8a7514b4ee
Create Date: 2026-07-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f9c3a7b2d1e'
down_revision: Union[str, Sequence[str], None] = 'bb8a7514b4ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add purchase_price column to investment_assets
    op.add_column('investment_assets', sa.Column('purchase_price', sa.Float(), nullable=True))

    # Create investment_transactions table
    op.create_table('investment_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('purchase_price', sa.Float(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_investment_transactions_id'), 'investment_transactions', ['id'], unique=False)
    op.create_index(op.f('ix_investment_transactions_ticker'), 'investment_transactions', ['ticker'], unique=False)
    op.create_index(op.f('ix_investment_transactions_owner_id'), 'investment_transactions', ['owner_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_investment_transactions_owner_id'), table_name='investment_transactions')
    op.drop_index(op.f('ix_investment_transactions_ticker'), table_name='investment_transactions')
    op.drop_index(op.f('ix_investment_transactions_id'), table_name='investment_transactions')
    op.drop_table('investment_transactions')
    op.drop_column('investment_assets', 'purchase_price')
