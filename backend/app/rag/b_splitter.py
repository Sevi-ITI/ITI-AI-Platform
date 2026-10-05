"""b_splitter: cut each Page into overlapping chunks that keep their source file and page number."""
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.a_loader import Page

# Characters, not tokens: 2,000 chars is about 500 tokens (spec 5.5).
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200


@dataclass(frozen=True)
class Chunk:
    id: str      # "<source>:p<page>:c<index>", stable so the vector store can update/delete it
    source: str
    page: int
    index: int   # position within the document, 0-based
    text: str


def split_pages(
    pages: list[Page], chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP
) -> list[Chunk]:
    # Tries paragraph breaks first, then lines, then words, so chunks end at natural boundaries.
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = []
    # Split page by page so every chunk belongs to exactly one page and its citation is exact.
    for page in pages:
        for text in splitter.split_text(page.text):
            index = len(chunks)
            chunks.append(
                Chunk(
                    id=f"{page.source}:p{page.page}:c{index}",
                    source=page.source,
                    page=page.page,
                    index=index,
                    text=text,
                )
            )
    return chunks
