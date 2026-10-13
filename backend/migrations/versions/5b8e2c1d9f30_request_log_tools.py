"""request log tools

Revision ID: 5b8e2c1d9f30
Revises: c9aed37d15a4
Create Date: 2026-10-13 17:30:00.000000

"""
from typing import Sequence, Union

import pgvector.sqlalchemy  # noqa: F401  the Vector type used by the chunks table
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5b8e2c1d9f30'
down_revision: Union[str, Sequence[str], None] = 'c9aed37d15a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('request_logs', sa.Column('tools', sa.String(length=120), nullable=True))
    op.add_column('request_logs', sa.Column('tools_ms', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('request_logs', 'tools_ms')
    op.drop_column('request_logs', 'tools')
