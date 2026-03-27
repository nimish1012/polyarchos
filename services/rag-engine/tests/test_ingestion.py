"""Tests for rag_engine.ingestion — mirrors src/rag_engine/ingestion.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_engine.ingestion import IngestionPipeline, IngestionResult

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "tests" / "fixtures"

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_pipeline(
    embed_return: list[list[float]] | None = None,
    upsert_return: int = 4,
    neo4j_edges: int = 2,
) -> tuple[IngestionPipeline, MagicMock, MagicMock, MagicMock]:
    """Build an IngestionPipeline with all dependencies mocked."""
    embedder = MagicMock()
    embedder.embed.return_value = embed_return or [[0.1] * 384, [0.2] * 384, [0.3] * 384, [0.4] * 384]

    milvus = MagicMock()
    milvus.upsert_chunks.return_value = upsert_return

    neo4j = MagicMock()
    neo4j.upsert_component = AsyncMock(return_value=neo4j_edges)

    pipeline = IngestionPipeline(embedder=embedder, milvus=milvus, neo4j=neo4j)
    return pipeline, embedder, milvus, neo4j


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ingest_sample_fixture() -> None:
    """Full ingest of the sample fixture should index 4 components."""
    pipeline, embedder, milvus, neo4j = _make_pipeline(
        embed_return=[[float(i)] * 384 for i in range(4)],
        upsert_return=4,
        neo4j_edges=2,
    )
    arxml = (FIXTURES_DIR / "sample.arxml").read_bytes()
    result = await pipeline.ingest(arxml, "sample.arxml")

    assert isinstance(result, IngestionResult)
    assert result.components_indexed == 4
    assert result.graph_edges_created == 8  # 4 components × 2 edges each
    assert result.document_name == "sample.arxml"
    assert result.job_id  # non-empty UUID string


@pytest.mark.asyncio
async def test_ingest_calls_embedder_with_text_chunks() -> None:
    pipeline, embedder, milvus, _ = _make_pipeline(
        embed_return=[[0.1] * 384] * 4,
    )
    arxml = (FIXTURES_DIR / "sample.arxml").read_bytes()
    await pipeline.ingest(arxml, "sample.arxml")

    embedder.embed.assert_called_once()
    texts: list[str] = embedder.embed.call_args[0][0]
    # Each text chunk should mention the component name
    assert any("EngineControlSWC" in t for t in texts)
    assert any("PerceptionServiceSWC" in t for t in texts)


@pytest.mark.asyncio
async def test_ingest_calls_milvus_upsert() -> None:
    pipeline, _, milvus, _ = _make_pipeline(
        embed_return=[[0.1] * 384] * 4,
    )
    arxml = (FIXTURES_DIR / "sample.arxml").read_bytes()
    await pipeline.ingest(arxml, "sample.arxml")

    milvus.upsert_chunks.assert_called_once()
    chunks = milvus.upsert_chunks.call_args[0][0]
    assert len(chunks) == 4
    assert all(c.document_name == "sample.arxml" for c in chunks)


@pytest.mark.asyncio
async def test_ingest_calls_neo4j_for_each_component() -> None:
    pipeline, _, _, neo4j = _make_pipeline(
        embed_return=[[0.1] * 384] * 4,
    )
    arxml = (FIXTURES_DIR / "sample.arxml").read_bytes()
    await pipeline.ingest(arxml, "sample.arxml")

    assert neo4j.upsert_component.call_count == 4


@pytest.mark.asyncio
async def test_ingest_empty_arxml_returns_zero_counts() -> None:
    pipeline, embedder, milvus, neo4j = _make_pipeline()
    empty_arxml = b"<AUTOSAR><AR-PACKAGES/></AUTOSAR>"
    result = await pipeline.ingest(empty_arxml, "empty.arxml")

    assert result.components_indexed == 0
    assert result.graph_edges_created == 0
    embedder.embed.assert_not_called()
    milvus.upsert_chunks.assert_not_called()
    neo4j.upsert_component.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_idempotency_key_is_document_name() -> None:
    """Chunks must carry the document_name so Milvus can delete + re-insert."""
    pipeline, _, milvus, _ = _make_pipeline(
        embed_return=[[0.1] * 384] * 4,
    )
    arxml = (FIXTURES_DIR / "sample.arxml").read_bytes()
    await pipeline.ingest(arxml, "my-document-v1")

    chunks = milvus.upsert_chunks.call_args[0][0]
    assert all(c.document_name == "my-document-v1" for c in chunks)


@pytest.mark.asyncio
async def test_ingest_variant_in_chunks() -> None:
    """Milvus chunks must carry the variant string for filtering."""
    pipeline, _, milvus, _ = _make_pipeline(
        embed_return=[[0.1] * 384] * 4,
    )
    arxml = (FIXTURES_DIR / "sample.arxml").read_bytes()
    await pipeline.ingest(arxml, "sample.arxml")

    chunks = milvus.upsert_chunks.call_args[0][0]
    variants = {c.variant for c in chunks}
    assert "classic" in variants
    assert "adaptive" in variants
