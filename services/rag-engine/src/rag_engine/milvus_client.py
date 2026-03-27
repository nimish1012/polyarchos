"""Milvus vector store client for AUTOSAR component embeddings.

Collection schema ``autosar_components``:
- id            INT64  (PK, auto-id)
- arxml_ref     VARCHAR(512)   — used as idempotency key
- document_name VARCHAR(256)
- component_name VARCHAR(256)
- variant       VARCHAR(16)    — "classic" | "adaptive"
- text_chunk    VARCHAR(4096)
- embedding     FLOAT_VECTOR(384)

Index: IVF_FLAT with inner-product metric (IP).
For L2-normalised vectors, IP == cosine similarity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pymilvus import (  # type: ignore[import-untyped]
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

logger = logging.getLogger(__name__)

_DEFAULT_COLLECTION = "autosar_components"
_DEFAULT_DIM = 384
_CHUNK_MAX_LEN = 4096


@dataclass
class ComponentChunk:
    """A single text chunk + embedding ready for Milvus insertion."""

    arxml_ref: str
    document_name: str
    component_name: str
    variant: str
    text_chunk: str
    embedding: list[float]


@dataclass
class SearchResult:
    """A single Milvus similarity search hit."""

    arxml_ref: str
    document_name: str
    component_name: str
    text_chunk: str
    score: float


class MilvusComponentStore:
    """Manages the ``autosar_components`` Milvus collection."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 19530,
        collection_name: str = _DEFAULT_COLLECTION,
        embedding_dim: int = _DEFAULT_DIM,
    ) -> None:
        self._host = host
        self._port = port
        self._collection_name = collection_name
        self._embedding_dim = embedding_dim
        self._collection: Collection | None = None

    def connect(self) -> None:
        """Connect to Milvus and ensure the collection + index exist."""
        connections.connect("default", host=self._host, port=self._port)
        logger.info("Connected to Milvus", extra={"host": self._host, "port": self._port})
        self._ensure_collection()

    def disconnect(self) -> None:
        """Disconnect from Milvus."""
        connections.disconnect("default")

    def _ensure_collection(self) -> None:
        if utility.has_collection(self._collection_name):
            self._collection = Collection(self._collection_name)
            self._collection.load()
            logger.info("Loaded Milvus collection", extra={"name": self._collection_name})
            return

        schema = CollectionSchema(
            fields=[
                FieldSchema("id", DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema("arxml_ref", DataType.VARCHAR, max_length=512),
                FieldSchema("document_name", DataType.VARCHAR, max_length=256),
                FieldSchema("component_name", DataType.VARCHAR, max_length=256),
                FieldSchema("variant", DataType.VARCHAR, max_length=16),
                FieldSchema("text_chunk", DataType.VARCHAR, max_length=_CHUNK_MAX_LEN),
                FieldSchema(
                    "embedding", DataType.FLOAT_VECTOR, dim=self._embedding_dim
                ),
            ],
            description="AUTOSAR component text chunks with semantic embeddings",
        )
        self._collection = Collection(self._collection_name, schema)

        # IVF_FLAT with inner-product: for L2-normalised vectors this is cosine sim.
        index_params = {
            "metric_type": "IP",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128},
        }
        self._collection.create_index("embedding", index_params)
        self._collection.load()
        logger.info("Created Milvus collection", extra={"name": self._collection_name})

    def upsert_chunks(self, chunks: list[ComponentChunk]) -> int:
        """Insert chunks, removing existing records with the same arxml_ref first.

        This makes ingestion idempotent: re-running with the same ARXML file
        updates the vectors rather than duplicating them.

        Returns:
            Number of chunks inserted.
        """
        if not chunks or self._collection is None:
            return 0

        refs = list({c.arxml_ref for c in chunks})
        # Build a Milvus boolean expression to delete stale records.
        expr = " || ".join(f'arxml_ref == "{r}"' for r in refs)
        self._collection.delete(expr)

        data: list[list[object]] = [
            [c.arxml_ref for c in chunks],
            [c.document_name for c in chunks],
            [c.component_name for c in chunks],
            [c.variant for c in chunks],
            [c.text_chunk[:_CHUNK_MAX_LEN] for c in chunks],
            [c.embedding for c in chunks],
        ]
        self._collection.insert(data)
        self._collection.flush()
        logger.info("Milvus upsert complete", extra={"count": len(chunks)})
        return len(chunks)

    def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[SearchResult]:
        """Run an approximate nearest-neighbour search.

        Args:
            query_embedding: L2-normalised query vector (384-dim).
            top_k: Maximum number of results to return.

        Returns:
            List of :class:`SearchResult`, ordered by descending similarity.
        """
        if self._collection is None:
            return []

        results = self._collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "IP", "params": {"nprobe": 16}},
            limit=top_k,
            output_fields=["arxml_ref", "document_name", "component_name", "text_chunk"],
        )
        return [
            SearchResult(
                arxml_ref=hit.entity.get("arxml_ref", ""),
                document_name=hit.entity.get("document_name", ""),
                component_name=hit.entity.get("component_name", ""),
                text_chunk=hit.entity.get("text_chunk", ""),
                score=float(hit.score),
            )
            for hit in results[0]
        ]
