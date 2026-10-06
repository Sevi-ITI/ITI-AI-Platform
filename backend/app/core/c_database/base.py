"""Base: every table class (the b_models folders) inherits from this."""

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass