"""RagBase: the table base for rag/'s own tables. Separate from the app's Base so rag/ never
imports the API layer; Alembic is told about both."""

from sqlalchemy.orm import DeclarativeBase


class RagBase(DeclarativeBase):
    pass
