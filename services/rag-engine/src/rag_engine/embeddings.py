"""Local embedding model wrapper using fastembed.

Uses BAAI/bge-small-en-v1.5 by default:
- 384-dimensional output vectors (compatible with Milvus FLOAT_VECTOR(384))
- ~130 MB model size
- CPU-only inference — no GPU required
- L2-normalised output → inner-product search == cosine similarity in Milvus

All inference is local. This module never makes outbound HTTP calls.
"""

from __future__ import annotations

import logging

from fastembed import TextEmbedding  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Thin wrapper around a fastembed ``TextEmbedding`` model.

    Downloads the model on first use and caches it in the fastembed cache
    directory (~/.cache/fastembed/ by default).
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        logger.info("Loading embedding model", extra={"model": model_name})
        self._model: TextEmbedding = TextEmbedding(model_name=model_name)
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        """Identifier of the loaded model."""
        return self._model_name

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts.

        Returns L2-normalised float vectors as plain Python lists
        (required by the pymilvus insert API).

        Args:
            texts: Non-empty list of text strings to embed.

        Returns:
            List of float vectors, one per input text.
        """
        if not texts:
            return []
        return [v.tolist() for v in self._model.embed(texts)]

    def embed_one(self, text: str) -> list[float]:
        """Embed a single text string."""
        return self.embed([text])[0]
