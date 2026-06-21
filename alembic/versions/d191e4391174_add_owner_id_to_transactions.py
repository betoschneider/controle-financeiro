"""add_owner_id_to_transactions

Revision ID: d191e4391174
Revises: 61f5ca4cd77f
Create Date: 2026-06-20 12:06:29.092542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd191e4391174'
down_revision: Union[str, Sequence[str], None] = '61f5ca4cd77f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('transacoes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('owner_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_transacoes_owner_id'), ['owner_id'], unique=False)
        batch_op.create_foreign_key('fk_transacoes_owner_id_users', 'users', ['owner_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('transacoes', schema=None) as batch_op:
        batch_op.drop_constraint('fk_transacoes_owner_id_users', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_transacoes_owner_id'))
        batch_op.drop_column('owner_id')

