"""RAG engine entry point.

Initialises all infrastructure clients (Milvus, Neo4j, embedding model, Ollama)
and starts the gRPC server on the configured port.

All configuration is read from environment variables (prefix: ``RAG_``).
See :mod:`rag_engine.config` for the full list.
"""

from __future__ import annotations

import asyncio
import logging

import structlog

from rag_engine.config import get_settings
from rag_engine.embeddings import EmbeddingModel
from rag_engine.grpc_server import RagServiceServicer, serve
from rag_engine.ingestion import IngestionPipeline
from rag_engine.llm import OllamaClient
from rag_engine.milvus_client import MilvusComponentStore
from rag_engine.neo4j_client import Neo4jComponentGraph
from rag_engine.pipeline import RagPipeline


def main() -> None:
    """Initialise all components and start the gRPC server."""
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
    )
    log = structlog.get_logger(__name__)

    cfg = get_settings()
    log.info(
        "Starting rag-engine",
        grpc_port=cfg.grpc_port,
        llm_model=cfg.ollama_model,
        embedding_model=cfg.embedding_model,
    )

    embedder = EmbeddingModel(model_name=cfg.embedding_model)

    milvus = MilvusComponentStore(
        host=cfg.milvus_host,
        port=cfg.milvus_port,
        collection_name=cfg.milvus_collection,
        embedding_dim=cfg.embedding_dim,
    )
    milvus.connect()

    neo4j = Neo4jComponentGraph(
        uri=cfg.neo4j_uri,
        user=cfg.neo4j_user,
        password=cfg.neo4j_password,
    )
    asyncio.get_event_loop().run_until_complete(neo4j.connect())

    llm = OllamaClient(
        base_url=cfg.ollama_base_url,
        model=cfg.ollama_model,
        timeout_s=cfg.ollama_timeout_s,
    )

    ingestion = IngestionPipeline(embedder=embedder, milvus=milvus, neo4j=neo4j)
    pipeline = RagPipeline(
        embedder=embedder,
        milvus=milvus,
        neo4j=neo4j,
        llm=llm,
        context_chunks=cfg.context_chunks,
    )

    servicer = RagServiceServicer(ingestion=ingestion, pipeline=pipeline)
    serve(servicer, port=cfg.grpc_port, max_workers=cfg.grpc_max_workers)


if __name__ == "__main__":
    main()
