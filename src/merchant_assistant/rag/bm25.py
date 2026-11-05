"""Lexical retrieval (BM25) over the chunks of a dense collection, persisted by corpus hash (task 80, spec v0.9.0 D7).

The index is built from the same chunk payloads stored in the Qdrant collection, so the hybrid search fuses two
rankings of one corpus. It is pickled to `<runtime>/bm25-<hash>.pkl`, where `<hash>` is the sha256 of the sorted
(chunk id, text) pairs: the same corpus loads the file, a different corpus builds a new one.
"""

from __future__ import annotations

import hashlib
import os
import pickle
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from rank_bm25 import BM25Okapi

# Short pt/en function words. Codes and acronyms (MDR, E-1023) are never stopwords.
STOPWORDS = frozenset(
    (
        "a o e de da do das dos em no na nos nas um uma uns umas para pra por com sem que se ao aos os as eu "
        "meu minha meus minhas seu sua seus suas ou mas como qual quais quando onde ja nao sim mais muito "
        "isso esse essa este esta isto ele ela eles elas voce voces me te lhe nem so pelo pela pelos pelas "
        "the of and to in on for is are was be been my can i what how do does did with an or it its at you your "
        "this that these those from by as if not no yes me we our they their there which when where who why"
    ).split()
)

_WORD = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def fold(text: str) -> str:
    """Lowercase without accents."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def tokenize(text: str) -> list[str]:
    """Words split on non-alphanumerics, minus stopwords; a hyphenated code with a digit stays whole (`e-1023`)."""
    tokens: list[str] = []
    for word in _WORD.findall(fold(text)):
        if "-" in word and any(c.isdigit() for c in word):
            tokens.append(word)
            continue
        tokens.extend(part for part in word.split("-") if part not in STOPWORDS)
    return tokens


def corpus_hash(records: list[dict]) -> str:
    """sha256 of the (chunk id, text) pairs ordered by chunk id: independent of storage order."""
    h = hashlib.sha256()
    for chunk_id, text in sorted((str(r["chunk_id"]), str(r.get("text") or "")) for r in records):
        h.update(chunk_id.encode())
        h.update(b"\0")
        h.update(text.encode())
        h.update(b"\n")
    return h.hexdigest()


@dataclass
class Bm25Index:
    corpus_hash: str
    payloads: list[dict]
    _bm25: BM25Okapi | None = field(default=None, repr=False)

    @classmethod
    def build(cls, records: list[dict]) -> Bm25Index:
        payloads = sorted((dict(r) for r in records), key=lambda r: str(r["chunk_id"]))
        tokenized = [tokenize(str(p.get("text") or "")) for p in payloads]
        bm25 = BM25Okapi(tokenized) if any(tokenized) else None
        return cls(corpus_hash(payloads), payloads, bm25)

    def search(self, query: str, *, k: int, source_kinds: list[str] | None = None) -> list[tuple[float, dict]]:
        """Top `k` chunks with at least one query term, best first; ties ordered by chunk id."""
        tokens = tokenize(query)
        if not tokens or self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokens)
        terms = self._bm25.doc_freqs  # per chunk: {token: frequency}
        candidates = [
            i
            for i, payload in enumerate(self.payloads)
            if any(t in terms[i] for t in tokens) and (not source_kinds or payload.get("source_kind") in source_kinds)
        ]
        candidates.sort(key=lambda i: (-float(scores[i]), str(self.payloads[i]["chunk_id"])))
        return [(float(scores[i]), self.payloads[i]) for i in candidates[:k]]


def bm25_path(directory: Path, digest: str) -> Path:
    return directory / f"bm25-{digest}.pkl"


def load_or_build(records: list[dict], directory: Path | None) -> tuple[Bm25Index, bool]:
    """Load the persisted index for this corpus or build (and persist) it; also says whether it was built."""
    digest = corpus_hash(records)
    if directory is not None:
        path = bm25_path(directory, digest)
        if path.exists():
            try:
                with path.open("rb") as handle:
                    loaded = pickle.load(handle)  # written only by this function, under the runtime directory
                if isinstance(loaded, Bm25Index) and loaded.corpus_hash == digest:
                    return loaded, False
            except Exception:  # unreadable or stale file: rebuild it below
                pass
    index = Bm25Index.build(records)
    if directory is not None:
        directory.mkdir(parents=True, exist_ok=True)
        path = bm25_path(directory, digest)
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        with tmp.open("wb") as handle:
            pickle.dump(index, handle, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, path)
    return index, True
