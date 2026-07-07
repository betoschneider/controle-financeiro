"""create_initial_tables

Revision ID: 61f5ca4cd77f
Revises: 
Create Date: 2026-06-20 11:44:05.211165

This migration now creates ALL initial tables (users, transacoes, investment_assets).

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61f5ca4cd77f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### users table ###
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('totp_secret', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # ### transacoes table ###
    op.create_table('transacoes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ano', sa.Integer(), nullable=False),
    sa.Column('mes', sa.Integer(), nullable=False),
    sa.Column('item', sa.String(100), nullable=False),
    sa.Column('tipo', sa.String(50), nullable=False),
    sa.Column('categoria', sa.String(50), nullable=False),
    sa.Column('valor', sa.Float(), nullable=False, server_default='0.0'),
    sa.Column('pago', sa.Boolean(), nullable=False, server_default='0'),
    sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transacoes_ano'), 'transacoes', ['ano'], unique=False)
    op.create_index(op.f('ix_transacoes_mes'), 'transacoes', ['mes'], unique=False)
    op.create_index(op.f('ix_transacoes_item'), 'transacoes', ['item'], unique=False)
    op.create_index(op.f('ix_transacoes_tipo'), 'transacoes', ['tipo'], unique=False)
    op.create_index(op.f('ix_transacoes_categoria'), 'transacoes', ['categoria'], unique=False)
    op.create_index(op.f('ix_transacoes_owner_id'), 'transacoes', ['owner_id'], unique=False)

    # ### investment_assets table ###
    op.create_table('investment_assets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('company', sa.String(), nullable=False),
    sa.Column('ticker', sa.String(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False, server_default='0'),
    sa.Column('target', sa.Float(), nullable=True),
    sa.Column('sector', sa.String(), nullable=True),
    sa.Column('group', sa.String(), nullable=True),
    sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_investment_assets_company'), 'investment_assets', ['company'], unique=False)
    op.create_index(op.f('ix_investment_assets_ticker'), 'investment_assets', ['ticker'], unique=False)
    op.create_index(op.f('ix_investment_assets_owner_id'), 'investment_assets', ['owner_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_investment_assets_owner_id'), table_name='investment_assets')
    op.drop_index(op.f('ix_investment_assets_ticker'), table_name='investment_assets')
    op.drop_index(op.f('ix_investment_assets_company'), table_name='investment_assets')
    op.drop_table('investment_assets')

    op.drop_index(op.f('ix_transacoes_owner_id'), table_name='transacoes')
    op.drop_index(op.f('ix_transacoes_categoria'), table_name='transacoes')
    op.drop_index(op.f('ix_transacoes_tipo'), table_name='transacoes')
    op.drop_index(op.f('ix_transacoes_item'), table_name='transacoes')
    op.drop_index(op.f('ix_transacoes_mes'), table_name='transacoes')
    op.drop_index(op.f('ix_transacoes_ano'), table_name='transacoes')
    op.drop_table('transacoes')

    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
