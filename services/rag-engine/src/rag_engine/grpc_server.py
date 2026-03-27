"""gRPC server implementing ``polyarchos.rag.v1.RagService``.

Proto stubs are generated at build time by ``buf generate``.
Run ``buf generate`` from the repo root before starting the server.

The stubs land in ``services/rag-engine/src/generated/`` and are imported
at runtime by inserting that directory into ``sys.path``.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from concurrent import futures
from pathlib import Path
from typing import Any

import grpc  # type: ignore[import-untyped]

# Add generated proto stubs to path.
_GENERATED_DIR = Path(__file__).parent.parent.parent / "generated"
if str(_GENERATED_DIR) not in sys.path:
    sys.path.insert(0, str(_GENERATED_DIR))

# type: ignore[import-not-found] — stubs generated at build time, not committed.
from polyarchos.rag.v1 import service_pb2  # type: ignore[import-not-found]
from polyarchos.rag.v1 import service_pb2_grpc  # type: ignore[import-not-found]
from google.protobuf import timestamp_pb2  # type: ignore[import-not-found]

from rag_engine.ingestion import IngestionPipeline
from rag_engine.pipeline import RagPipeline

logger = logging.getLogger(__name__)

_JobState = dict[str, dict[str, Any]]


def _now_timestamp() -> Any:
    ts = timestamp_pb2.Timestamp()
    ts.GetCurrentTime()
    return ts


class RagServiceServicer(service_pb2_grpc.RagServiceServicer):  # type: ignore[misc]
    """Concrete implementation of the RagService gRPC interface."""

    def __init__(self, ingestion: IngestionPipeline, pipeline: RagPipeline) -> None:
        self._ingestion = ingestion
        self._pipeline = pipeline
        self._jobs: _JobState = {}

    def IngestDocument(
        self,
        request: Any,
        context: grpc.ServicerContext,  # type: ignore[type-arg]
    ) -> Any:
        """Ingest an ARXML document into Milvus + Neo4j."""
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {"status": service_pb2.INGEST_STATUS_RUNNING}

        try:
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    self._ingestion.ingest(
                        request.arxml_content,
                        request.document_name,
                    )
                )
            finally:
                loop.close()

            self._jobs[job_id]["status"] = service_pb2.INGEST_STATUS_COMPLETED
            return service_pb2.IngestDocumentResponse(
                job_id=result.job_id,
                components_indexed=result.components_indexed,
                graph_edges_created=result.graph_edges_created,
                completed_at=_now_timestamp(),
            )
        except Exception as exc:
            self._jobs[job_id]["status"] = service_pb2.INGEST_STATUS_FAILED
            self._jobs[job_id]["error"] = str(exc)
            logger.exception("Ingestion failed", extra={"job_id": job_id})
            context.abort(grpc.StatusCode.INTERNAL, str(exc))
            return service_pb2.IngestDocumentResponse()

    def Query(
        self,
        request: Any,
        context: grpc.ServicerContext,  # type: ignore[type-arg]
    ) -> Any:
        """Answer a natural-language question via the RAG pipeline."""
        try:
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    self._pipeline.query(
                        request.question,
                        top_k=request.context_chunks or None,
                    )
                )
            finally:
                loop.close()

            return service_pb2.QueryResponse(
                answer=result.answer,
                sources=[
                    service_pb2.SourceChunk(
                        document_name=s.document_name,
                        text=s.text_chunk,
                        relevance_score=s.score,
                    )
                    for s in result.sources
                ],
                model_id=result.model_id,
            )
        except Exception as exc:
            logger.exception("Query failed")
            context.abort(grpc.StatusCode.INTERNAL, str(exc))
            return service_pb2.QueryResponse()

    def GetIngestStatus(
        self,
        request: Any,
        context: grpc.ServicerContext,  # type: ignore[type-arg]
    ) -> Any:
        """Return the current status of an ingestion job."""
        state = self._jobs.get(request.job_id)
        if state is None:
            return service_pb2.GetIngestStatusResponse(
                job_id=request.job_id,
                status=service_pb2.INGEST_STATUS_UNSPECIFIED,
            )
        return service_pb2.GetIngestStatusResponse(
            job_id=request.job_id,
            status=state["status"],
            error_message=state.get("error", ""),
        )


def serve(
    servicer: RagServiceServicer,
    port: int,
    max_workers: int = 4,
) -> None:
    """Start the gRPC server. Blocks until interrupted by SIGTERM/KeyboardInterrupt."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    service_pb2_grpc.add_RagServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    logger.info("rag-engine gRPC server started", extra={"port": port})
    server.wait_for_termination()
