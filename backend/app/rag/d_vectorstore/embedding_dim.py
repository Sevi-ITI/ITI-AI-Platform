"""EMBEDDING_DIM: numbers per embedding. bge-m3 makes 1,024. Changing the model means a new
migration for the chunks table AND re-indexing every document."""

EMBEDDING_DIM = 1024
