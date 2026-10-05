"""ChunkRow: the chunks table: one row per chunk of text with its embedding (pgvector).
Every collection shares this table; the collection column keeps them apart.
The HNSW index makes "find the nearest chunks" fast even with many thousands of rows."""

from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.rag.d_vectorstore.embedding_dim import EMBEDDING_DIM
from app.rag.d_vectorstore.rag_base import RagBase


class ChunkRow(RagBase):
    __tablename__ = "chunks"

    collection: Mapped[str] = mapped_column(String(64), primary_key=True)
    id: Mapped[str] = mapped_column(String(300), primary_key=True)  # e.g. "handbook.pdf:p10:c21"
    source: Mapped[str] = mapped_column(String(200), index=True)  # the file name citations show
    page: Mapped[int | None] = mapped_column(Integer)  # the PDF viewer's page number
    text: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
