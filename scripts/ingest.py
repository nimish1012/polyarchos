"""ARXML ingestion CLI.

Usage:
    uv run python scripts/ingest.py --input tests/fixtures/sample.arxml
    uv run python scripts/ingest.py --input path/to/ecus.arxml --document-name my-ecu-v2

Reads the ARXML file, parses all SWC definitions, embeds them with the local
embedding model (BAAI/bge-small-en-v1.5), and upserts vectors into Milvus and
nodes/edges into Neo4j.

All services (Milvus, Neo4j) must be running before ingestion.
Use ``docker compose -f infra/docker-compose.dev.yml up -d`` to start them locally.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import structlog

# Allow running as `python scripts/ingest.py` from repo root.
_REPO_ROOT = Path(__file__).parent.parent
_RAG_SRC = _REPO_ROOT / "services" / "rag-engine" / "src"
if str(_RAG_SRC) not in sys.path:
    sys.path.insert(0, str(_RAG_SRC))

from rag_engine.config import get_settings
from rag_engine.embeddings import EmbeddingModel
from rag_engine.ingestion import IngestionPipeline
from rag_engine.milvus_client import MilvusComponentStore
from rag_engine.neo4j_client import Neo4jComponentGraph


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest an ARXML document into Milvus + Neo4j.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        metavar="PATH",
        help="Path to the ARXML file to ingest.",
    )
    parser.add_argument(
        "--document-name",
        type=str,
        default=None,
        metavar="NAME",
        help="Logical document name used as the idempotency key. "
        "Defaults to the file name.",
    )
    return parser


async def _run(input_path: Path, document_name: str) -> int:
    log = structlog.get_logger(__name__)

    if not input_path.exists():
        log.error("Input file not found", path=str(input_path))
        return 1

    cfg = get_settings()

    log.info("Initialising embedding model", model=cfg.embedding_model)
    embedder = EmbeddingModel(model_name=cfg.embedding_model)

    log.info("Connecting to Milvus", host=cfg.milvus_host, port=cfg.milvus_port)
    milvus = MilvusComponentStore(
        host=cfg.milvus_host,
        port=cfg.milvus_port,
        collection_name=cfg.milvus_collection,
        embedding_dim=cfg.embedding_dim,
    )
    milvus.connect()

    log.info("Connecting to Neo4j", uri=cfg.neo4j_uri)
    neo4j = Neo4jComponentGraph(
        uri=cfg.neo4j_uri,
        user=cfg.neo4j_user,
        password=cfg.neo4j_password,
    )
    await neo4j.connect()

    pipeline = IngestionPipeline(embedder=embedder, milvus=milvus, neo4j=neo4j)

    log.info("Starting ingestion", file=str(input_path), document=document_name)
    arxml_bytes = input_path.read_bytes()
    result = await pipeline.ingest(arxml_bytes, document_name)

    log.info(
        "Ingestion complete",
        job_id=result.job_id,
        components_indexed=result.components_indexed,
        graph_edges_created=result.graph_edges_created,
    )
    await neo4j.close()
    milvus.disconnect()
    return 0


def main() -> None:
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
    )

    args = _build_arg_parser().parse_args()
    doc_name = args.document_name or args.input.name

    exit_code = asyncio.run(_run(args.input, doc_name))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
