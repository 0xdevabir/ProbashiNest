"""Retrieval over the rules and fraud patterns (the "RAG" half of the engine).

Retrieval never decides the level. It finds the knowledge-base passages that
support a reason, so the reason can carry a source and the optional LLM
rephrase has the facts in front of it.

Backends (env KNOWLEDGE_RETRIEVER):
  lexical    (default) character n-gram TF-IDF, pure Python, works for Bangla and English
  embedding  sentence-transformers multilingual model; falls back to lexical if
             the package or the model is not available
"""

from __future__ import annotations

import logging
import math
import os
from collections import Counter
from dataclasses import dataclass

from probashi.schemas import Source

from .kb import KnowledgeBase, source_of

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
SAME_CODE_BOOST = 0.3
SAME_COUNTRY_BOOST = 0.1


@dataclass(frozen=True)
class Passage:
    id: str
    kind: str  # "rule" or "pattern"
    country: str | None  # None = applies to every destination
    code: str | None  # reason code a fraud pattern belongs to
    text_en: str
    text_bn: str
    source: Source | None
    verified: bool

    @property
    def text(self) -> str:
        return f"{self.text_en}\n{self.text_bn}"


@dataclass(frozen=True)
class Hit:
    passage: Passage
    score: float


def build_passages(kb: KnowledgeBase) -> list[Passage]:
    passages = [
        Passage(rec["id"], "rule", country, None, rec["text_en"], rec["text_bn"], source_of(rec), rec["verified"])
        for country, doc in kb.rules.items()
        for rec in doc["records"]
    ]
    passages += [
        Passage(
            p["id"], "pattern", None, p.get("code"),
            f"{p.get('title_en', '')}. {p['text_en']}", p["text_bn"], source_of(p), p["verified"],
        )
        for p in kb.patterns
    ]
    return passages


def _ngrams(text: str) -> Counter:
    text = " ".join(text.lower().split())
    return Counter(text[i : i + n] for n in (3, 4) for i in range(len(text) - n + 1))


class LexicalIndex:
    def __init__(self, texts: list[str]) -> None:
        counts = [_ngrams(t) for t in texts]
        df = Counter(g for c in counts for g in c)
        self._idf = {g: math.log((1 + len(texts)) / (1 + n)) + 1 for g, n in df.items()}
        self._vectors = [self._weigh(c) for c in counts]

    def _weigh(self, counts: Counter) -> dict[str, float]:
        vec = {g: (1 + math.log(n)) * self._idf[g] for g, n in counts.items() if g in self._idf}
        norm = math.sqrt(sum(w * w for w in vec.values())) or 1.0
        return {g: w / norm for g, w in vec.items()}

    def scores(self, query: str) -> list[float]:
        q = self._weigh(_ngrams(query))
        return [sum(w * vec.get(g, 0.0) for g, w in q.items()) for vec in self._vectors]


class EmbeddingIndex:
    def __init__(self, texts: list[str]) -> None:
        from sentence_transformers import SentenceTransformer  # optional dependency

        self._model = SentenceTransformer(EMBEDDING_MODEL)
        self._matrix = self._model.encode(texts, normalize_embeddings=True)

    def scores(self, query: str) -> list[float]:
        q = self._model.encode([query], normalize_embeddings=True)[0]
        return [float(s) for s in self._matrix @ q]


class Retriever:
    def __init__(self, kb: KnowledgeBase, backend: str | None = None) -> None:
        self.passages = build_passages(kb)
        texts = [p.text for p in self.passages]
        backend = (backend or os.environ.get("KNOWLEDGE_RETRIEVER") or "lexical").strip().lower()
        if backend not in ("lexical", "embedding"):
            logger.warning("unknown KNOWLEDGE_RETRIEVER %r; using lexical", backend)
            backend = "lexical"
        self.backend = backend
        if backend == "embedding":
            try:
                self._index = EmbeddingIndex(texts)
            except Exception as exc:  # missing package, no model download, ...
                logger.warning("embedding retriever unavailable (%s); using lexical", exc)
                self.backend = "lexical"
        if self.backend == "lexical":
            self._index = LexicalIndex(texts)

    def search(self, query: str, *, country: str | None = None, code: str | None = None, k: int = 3) -> list[Hit]:
        """Top-k passages for a query. Passages about other destinations are left
        out; passages tied to the same reason code or destination rank higher."""
        hits = []
        for passage, score in zip(self.passages, self._index.scores(query)):
            if passage.country and passage.country != country:
                continue
            if code and passage.code == code:
                score += SAME_CODE_BOOST
            if country and passage.country == country:
                score += SAME_COUNTRY_BOOST
            hits.append(Hit(passage, score))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k]

    def by_id(self, passage_id: str | None) -> Passage | None:
        return next((p for p in self.passages if p.id == passage_id), None)


_retrievers: dict[tuple[int, str], Retriever] = {}


def get_retriever(kb: KnowledgeBase) -> Retriever:
    """One retriever per loaded knowledge base and backend setting."""
    key = (id(kb), os.environ.get("KNOWLEDGE_RETRIEVER", "lexical"))
    if key not in _retrievers:
        _retrievers[key] = Retriever(kb)
    return _retrievers[key]
