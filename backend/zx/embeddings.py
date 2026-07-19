"""Local, dependency-free embedding function for ChromaDB.

The real design uses text-embedding-3-small behind pgvector. For the POC we feed
ChromaDB a deterministic character-n-gram hashing embedder: no network, no API
key, no native wheels. ChromaDB stays the real vector store — only the embedder is
swapped. Promoting to real embeddings is a one-line change to `embed()`.
"""
from __future__ import annotations

import math
import re

DIM = 256


def _tokens(text: str) -> list[str]:
    text = text.lower()
    words = re.findall(r"[a-z0-9]+", text)
    grams: list[str] = list(words)
    # character trigrams capture fuzzy/typo similarity ("shade" ~ "shades")
    for w in words:
        padded = f"#{w}#"
        for i in range(len(padded) - 2):
            grams.append(padded[i:i + 3])
    return grams


def embed(text: str) -> list[float]:
    vec = [0.0] * DIM
    for tok in _tokens(text):
        h = hash(tok) % DIM
        vec[h] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _embed_many(input):  # noqa: A002
    if isinstance(input, str):
        input = [input]
    return [embed(t) for t in input]


class LocalEmbeddingFunction:
    """Chroma EmbeddingFunction-compatible callable (supports old + new API)."""

    def __call__(self, input):  # noqa: A002 — Chroma's required param name
        return _embed_many(input)

    def embed_documents(self, input):  # noqa: A002 — chromadb >=1.5
        return _embed_many(input)

    def embed_query(self, input):  # noqa: A002 — chromadb >=1.5
        return _embed_many(input)

    # Newer chromadb versions call these for persistence metadata.
    def name(self) -> str:
        return "zx-local-ngram"

    @staticmethod
    def build_from_config(config):
        return LocalEmbeddingFunction()

    def get_config(self):
        return {}
