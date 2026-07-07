"""add investment_assets table (now a no-op since table is in initial migration)
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
    """This migration is now a no-op because investment_assets table
    is already created in the initial migration 61f5ca4cd77f."""
    pass
def downgrade():
    pass

