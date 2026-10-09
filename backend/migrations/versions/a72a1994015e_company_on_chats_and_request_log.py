"""company on chats and request log (6C.2): a person is app + company + user. Existing chats and request-log
rows (all made before companies existed) belong to ITI.

company on chats and request log

Revision ID: a72a1994015e
Revises: e62354be629f
Create Date: 2026-10-09 16:21:38.000148

"""
from typing import Sequence, Union

import pgvector.sqlalchemy  # noqa: F401  the Vector type used by the chunks table
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a72a1994015e'
down_revision: Union[str, Sequence[str], None] = 'e62354be629f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """company_id on conversations (required; existing ones -> 'iti') and on request_logs (existing rows that
    name an app -> 'iti'; rows with no app, e.g. failed logins, stay empty)."""
    op.add_column("conversations", sa.Column("company_id", sa.String(length=64), nullable=True))
    op.execute("UPDATE conversations SET company_id = 'iti'")
    op.alter_column("conversations", "company_id", nullable=False)
    op.create_index(op.f("ix_conversations_company_id"), "conversations", ["company_id"], unique=False)

    op.add_column("request_logs", sa.Column("company_id", sa.String(length=64), nullable=True))
    op.execute("UPDATE request_logs SET company_id = 'iti' WHERE app_id IS NOT NULL")
    op.create_index(op.f("ix_request_logs_company_id"), "request_logs", ["company_id"], unique=False)


def downgrade() -> None:
    """Drops the company columns (chats and logs are kept, without their company)."""
    op.drop_index(op.f("ix_request_logs_company_id"), table_name="request_logs")
    op.drop_column("request_logs", "company_id")
    op.drop_index(op.f("ix_conversations_company_id"), table_name="conversations")
    op.drop_column("conversations", "company_id")
