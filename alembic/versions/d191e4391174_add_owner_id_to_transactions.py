"""add_owner_id_to_transactions (now a no-op since owner_id is in initial migration)

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
    """Upgrade schema.
    This migration is now a no-op because the transacoes table (including
    owner_id) is already created in the initial migration 61f5ca4cd77f.
    """
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
