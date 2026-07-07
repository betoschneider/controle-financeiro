"""add tipos and categorias tables

Revision ID: e5f6a7b8c9d0
Revises: a1b2c3d4e5f6
Create Date: 2026-07-10 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### tipos table ###
    op.create_table('tipos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(50), nullable=False),
        sa.Column('is_protegido', sa.Boolean(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_tipos_id'), 'tipos', ['id'], unique=False)
    op.create_index(op.f('ix_tipos_nome'), 'tipos', ['nome'], unique=True)

    # ### categorias table ###
    op.create_table('categorias',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('valor', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('tipo_id', sa.Integer(), sa.ForeignKey('tipos.id'), nullable=False),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('is_protegido', sa.Boolean(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_categorias_id'), 'categorias', ['id'], unique=False)
    op.create_index(op.f('ix_categorias_nome'), 'categorias', ['nome'], unique=False)
    op.create_index(op.f('ix_categorias_tipo_id'), 'categorias', ['tipo_id'], unique=False)
    op.create_index(op.f('ix_categorias_owner_id'), 'categorias', ['owner_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_categorias_owner_id'), table_name='categorias')
    op.drop_index(op.f('ix_categorias_tipo_id'), table_name='categorias')
    op.drop_index(op.f('ix_categorias_nome'), table_name='categorias')
    op.drop_index(op.f('ix_categorias_id'), table_name='categorias')
    op.drop_table('categorias')

    op.drop_index(op.f('ix_tipos_nome'), table_name='tipos')
    op.drop_index(op.f('ix_tipos_id'), table_name='tipos')
    op.drop_table('tipos')
