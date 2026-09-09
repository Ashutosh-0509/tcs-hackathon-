"""EmbeddingService — hides the embedding implementation behind one interface.

Primary: sentence-transformers (all-MiniLM-L6-v2).
Fallback: a deterministic hashed bag-of-words vector, used only when the model
cannot be loaded (offline CI). The fallback is ALWAYS logged — never silent — and
is clearly not a real semantic model.
"""
from __future__ import annotations

import hashlib
import logging
import re

import numpy as np

from app.core.config import get_settings

logger = logging.getLogger("trustlens.embeddings")

_TOKEN = re.compile(r"[a-z0-9]+")
_FALLBACK_DIM = 256


class EmbeddingService:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or get_settings().embedding_model
        self._model = None
        self._backend = "uninitialized"

    def _ensure_model(self) -> None:
        if self._backend != "uninitialized":
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            self._backend = "sentence-transformers"
            logger.info("embeddings: using sentence-transformers/%s", self.model_name)
        except Exception as exc:  # noqa: BLE001 - want any failure to degrade gracefully
            self._backend = "hashed-fallback"
            logger.warning(
                "embeddings: could not load '%s' (%s); using deterministic hashed fallback. "
                "Semantic scores will be approximate.",
                self.model_name,
                exc,
            )

    @property
    def backend(self) -> str:
        self._ensure_model()
        return self._backend

    def embed(self, texts: list[str]) -> np.ndarray:
        self._ensure_model()
        if not texts:
            return np.zeros((0, _FALLBACK_DIM), dtype=np.float32)
        if self._backend == "sentence-transformers":
            vecs = self._model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
            return vecs.astype(np.float32)
        return np.vstack([self._hashed(t) for t in texts])

    @staticmethod
    def _hashed(text: str) -> np.ndarray:
        vec = np.zeros(_FALLBACK_DIM, dtype=np.float32)
        for tok in _TOKEN.findall(text.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % _FALLBACK_DIM] += 1.0
        norm = np.linalg.norm(vec)
        return vec / norm if norm else vec

    def similarity_matrix(self, a: list[str], b: list[str]) -> np.ndarray:
        """Cosine similarity of every a-row against every b-row. Shape (len(a), len(b))."""
        if not a or not b:
            return np.zeros((len(a), len(b)), dtype=np.float32)
        va = self.embed(a)
        vb = self.embed(b)
        # rows are already L2-normalized in both backends
        return np.clip(va @ vb.T, -1.0, 1.0)


_default_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _default_service
    if _default_service is None:
        _default_service = EmbeddingService()
    return _default_service
