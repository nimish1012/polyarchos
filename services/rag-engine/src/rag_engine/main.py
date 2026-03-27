"""RAG engine entry point."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def main() -> None:
    """Start the RAG engine service."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("rag-engine starting", extra={"version": "0.1.0"})
    # TODO Phase 4: start gRPC server, initialise Milvus + Neo4j connections


if __name__ == "__main__":
    main()
