"""companies (6C.1): ITI's clients. Existing keys and collections go under the company "iti".

companies

Revision ID: e62354be629f
Revises: 04e83c756c65
Create Date: 2026-10-09 15:43:49.799962

"""
from typing import Sequence, Union

import pgvector.sqlalchemy  # noqa: F401  the Vector type used by the chunks table
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e62354be629f'
down_revision: Union[str, Sequence[str], None] = '04e83c756c65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Companies table with ITI in it; company_id on keys (required) and collections (empty = Global).
    Every existing key and collection is put under ITI before the key column becomes required."""
    op.create_table(
        "companies",
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("company_id"),
    )
    op.execute(
        "INSERT INTO companies (company_id, name, created_at) VALUES ('iti', 'Intellismart Technology Inc.', now())"
    )

    op.add_column("api_keys", sa.Column("company_id", sa.String(length=64), nullable=True))
    op.execute("UPDATE api_keys SET company_id = 'iti'")
    op.alter_column("api_keys", "company_id", nullable=False)
    op.create_index(op.f("ix_api_keys_company_id"), "api_keys", ["company_id"], unique=False)
    op.create_foreign_key("fk_api_keys_company_id", "api_keys", "companies", ["company_id"], ["company_id"])

    op.add_column("collections", sa.Column("company_id", sa.String(length=64), nullable=True))
    op.execute("UPDATE collections SET company_id = 'iti'")
    op.create_index(op.f("ix_collections_company_id"), "collections", ["company_id"], unique=False)
    op.create_foreign_key("fk_collections_company_id", "collections", "companies", ["company_id"], ["company_id"])


def downgrade() -> None:
    """Drops the company columns and the companies table (company assignments are lost)."""
    op.drop_constraint("fk_collections_company_id", "collections", type_="foreignkey")
    op.drop_index(op.f("ix_collections_company_id"), table_name="collections")
    op.drop_column("collections", "company_id")
    op.drop_constraint("fk_api_keys_company_id", "api_keys", type_="foreignkey")
    op.drop_index(op.f("ix_api_keys_company_id"), table_name="api_keys")
    op.drop_column("api_keys", "company_id")
    op.drop_table("companies")
