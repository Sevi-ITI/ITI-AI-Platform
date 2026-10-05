"""PgStore: a handle on one collection: the database engine plus the collection name.
It holds no data itself, so many requests and several workers can share it safely."""

from dataclasses import dataclass

from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class PgStore:
    engine: Engine
    collection: str
