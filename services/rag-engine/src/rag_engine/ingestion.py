"""ARXML ingestion pipeline: parse → embed → Milvus + Neo4j.

Ingestion is idempotent: re-running with the same document_name and ARXML
content updates existing records rather than creating duplicates.

Idempotency keys:
- Milvus: ``arxml_ref`` (delete + re-insert on each run)
- Neo4j:  ``arxml_ref`` uniqueness constraint + MERGE on all nodes/edges
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from rag_engine.arxml_parser import ArxmlDocument, parse_arxml
from rag_engine.embeddings import EmbeddingModel
from rag_engine.milvus_client import ComponentChunk, MilvusComponentStore
from rag_engine.neo4j_client import ComponentData, Neo4jComponentGraph, PortData

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Summary of a completed ingestion job."""

    job_id: str
    document_name: str
    components_indexed: int
    graph_edges_created: int


class IngestionPipeline:
    """Orchestrates end-to-end ARXML ingestion.

    Flow:
    1. Parse ARXML XML → :class:`~rag_engine.arxml_parser.ArxmlDocument`
    2. Serialise each SWC to a text chunk via ``to_text_chunk()``
    3. Batch-embed all chunks with the local embedding model
    4. Upsert chunks into Milvus (vector index)
    5. Merge SWC + Port + Interface nodes/edges into Neo4j (graph)
    """

    def __init__(
        self,
        embedder: EmbeddingModel,
        milvus: MilvusComponentStore,
        neo4j: Neo4jComponentGraph,
    ) -> None:
        self._embedder = embedder
        self._milvus = milvus
        self._neo4j = neo4j

    async def ingest(self, arxml_content: bytes, document_name: str) -> IngestionResult:
        """Ingest an ARXML document.

        Args:
            arxml_content: Raw ARXML file bytes.
            document_name: Logical name for this document (idempotency key).

        Returns:
            :class:`IngestionResult` with counts of indexed components and graph edges.
        """
        job_id = str(uuid.uuid4())
        logger.info(
            "Ingestion started",
            extra={"job_id": job_id, "document": document_name},
        )

        doc: ArxmlDocument = parse_arxml(arxml_content, document_name)

        if not doc.components:
            logger.warning(
                "No SWC components found",
                extra={"document": document_name},
            )
            return IngestionResult(
                job_id=job_id,
                document_name=document_name,
                components_indexed=0,
                graph_edges_created=0,
            )

        # ── Milvus: embed + upsert ────────────────────────────────────────────
        texts = [c.to_text_chunk() for c in doc.components]
        embeddings = self._embedder.embed(texts)

        chunks = [
            ComponentChunk(
                arxml_ref=comp.arxml_ref,
                document_name=document_name,
                component_name=comp.name,
                variant=comp.variant.value,
                text_chunk=comp.to_text_chunk(),
                embedding=emb,
            )
            for comp, emb in zip(doc.components, embeddings)
        ]
        upserted = self._milvus.upsert_chunks(chunks)
        logger.info("Milvus upsert complete", extra={"count": upserted})

        # ── Neo4j: upsert graph ───────────────────────────────────────────────
        total_edges = 0
        for comp in doc.components:
            data = ComponentData(
                name=comp.name,
                arxml_ref=comp.arxml_ref,
                variant=comp.variant.value,
                description=comp.description,
                ports=[
                    PortData(
                        name=p.name,
                        arxml_ref=p.arxml_ref,
                        direction=p.direction.value,
                        interface_ref=p.interface_ref,
                    )
                    for p in comp.ports
                ],
            )
            edges = await self._neo4j.upsert_component(data)
            total_edges += edges

        logger.info(
            "Ingestion complete",
            extra={
                "job_id": job_id,
                "components": len(doc.components),
                "edges": total_edges,
            },
        )
        return IngestionResult(
            job_id=job_id,
            document_name=document_name,
            components_indexed=len(doc.components),
            graph_edges_created=total_edges,
        )
