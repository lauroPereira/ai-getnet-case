"""Embedding providers: OpenAI for real runs and a deterministic hashing embedder for tests."""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from typing import Protocol


class Embedder(Protocol):
    model: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbedder:
    """Paid embeddings: every provider batch reserves budget first and settles that reservation exactly once."""

    def __init__(self, client, model: str, dim: int = 1536, batch: int = 64, budget=None) -> None:
        self.client, self.model, self.dim, self.batch, self.budget = client, model, dim, batch, budget
        self.tokens_used = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.budget is None:  # never reach the provider without a persistent guard
            raise RuntimeError("Paid embeddings require a persistent budget guard.")
        from merchant_assistant.llm.pricing import PriceUnknown, model_price

        vectors: list[list[float]] = []
        for i in range(0, len(texts), self.batch):
            batch = texts[i : i + self.batch]
            price = model_price(self.model)
            estimated_tokens = sum(max(1, (len(text.encode("utf-8")) + 2) // 3) for text in batch)
            estimate = estimated_tokens * price["input_per_mtok"] / 1_000_000
            if estimate <= 0:
                raise PriceUnknown(f"No usable price registered for embedding model {self.model}")
            reservation = self.budget.reserve(request_id=None, agent="embeddings", model=self.model, amount=estimate)
            try:
                response = self.client.embeddings.create(model=self.model, input=batch)
            except Exception:
                self.budget.settle(reservation, None)  # usage unknown: the reservation stays as spent
                raise
            tokens = getattr(getattr(response, "usage", None), "total_tokens", None)
            if isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0:
                self.budget.settle(reservation, None)  # unusable usage report: keep the conservative reservation
            else:
                self.tokens_used += tokens
                self.budget.settle(reservation, tokens * price["input_per_mtok"] / 1_000_000)
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
