"""Embedding providers: OpenAI for real runs and a deterministic hashing embedder for tests."""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections.abc import Callable
from typing import Protocol


class Embedder(Protocol):
    model: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbedder:
    def __init__(
        self, client, model: str, dim: int = 1536, batch: int = 64, on_usage: Callable[[str, int], None] | None = None
    ) -> None:
        self.client, self.model, self.dim, self.batch, self.on_usage = client, model, dim, batch, on_usage
        self.tokens_used = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), self.batch):
            response = self.client.embeddings.create(model=self.model, input=texts[i : i + self.batch])
            self.tokens_used += response.usage.total_tokens
            if self.on_usage:
                self.on_usage(self.model, response.usage.total_tokens)
            vectors.extend(d.embedding for d in sorted(response.data, key=lambda d: d.index))
        return vectors


_STOPWORDS = set(
    "a o e de da do das dos em no na nos nas um uma para por com que se ao os as eu meu minha posso "
    "the of and to in on for is my can i what how do does with an or it at be you your this that".split()
)


def _tokens(text: str) -> list[str]:
    folded = unicodedata.normalize("NFKD", text.lower())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    words = [w for w in re.findall(r"[a-z0-9]{2,}", folded) if w not in _STOPWORDS]
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:], strict=False)]


class HashEmbedder:
    """Bag-of-words hashing into a fixed space. Lexical only: used to test the pipeline without network."""

    model = "hash-embedder-v1"

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self.dim
            for token in _tokens(text):
                h = int(hashlib.md5(token.encode()).hexdigest(), 16)  # noqa: S324 - not security related
                vec[h % self.dim] += 1.0 if (h >> 8) % 2 else -1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out
