"""Tests for rag_engine.pipeline — mirrors src/rag_engine/pipeline.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_engine.milvus_client import SearchResult
from rag_engine.pipeline import QueryResult, RagPipeline


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_pipeline(
    milvus_hits: list[SearchResult] | None = None,
    graph_context: str = "",
    llm_answer: str = "The EngineControlSWC provides the FuelInjection interface.",
) -> tuple[RagPipeline, MagicMock, MagicMock, MagicMock, MagicMock]:
    embedder = MagicMock()
    embedder.embed_one.return_value = [0.1] * 384

    hits = milvus_hits or [
        SearchResult(
            arxml_ref="/polyarchos/Classic/EngineControlSWC",
            document_name="sample.arxml",
            component_name="EngineControlSWC",
            text_chunk="AUTOSAR Classic SWC: EngineControlSWC\nPorts: FuelInjectionPort (provided)",
            score=0.92,
        )
    ]
    milvus = MagicMock()
    milvus.search.return_value = hits

    neo4j = MagicMock()
    neo4j.get_component_context = AsyncMock(return_value=graph_context)

    llm = MagicMock()
    llm.generate.return_value = llm_answer
    llm.model_id = "mistral:7b-instruct"

    pipeline = RagPipeline(
        embedder=embedder,
        milvus=milvus,
        neo4j=neo4j,
        llm=llm,
        context_chunks=5,
    )
    return pipeline, embedder, milvus, neo4j, llm


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_query_returns_result() -> None:
    pipeline, *_ = _make_pipeline()
    result = await pipeline.query("Which SWC provides FuelInjection?")
    assert isinstance(result, QueryResult)
    assert result.answer
    assert result.model_id == "mistral:7b-instruct"


@pytest.mark.asyncio
async def test_query_embeds_question() -> None:
    pipeline, embedder, *_ = _make_pipeline()
    await pipeline.query("Which SWC provides FuelInjection?")
    embedder.embed_one.assert_called_once_with("Which SWC provides FuelInjection?")


@pytest.mark.asyncio
async def test_query_searches_milvus_with_top_k() -> None:
    pipeline, _, milvus, *_ = _make_pipeline()
    await pipeline.query("test question", top_k=3)
    milvus.search.assert_called_once()
    _, kwargs = milvus.search.call_args
    assert kwargs.get("top_k") == 3 or milvus.search.call_args[0][1] == 3


@pytest.mark.asyncio
async def test_query_fetches_graph_context() -> None:
    pipeline, _, milvus, neo4j, _ = _make_pipeline()
    await pipeline.query("test")
    neo4j.get_component_context.assert_called_once()
    refs: list[str] = neo4j.get_component_context.call_args[0][0]
    assert "/polyarchos/Classic/EngineControlSWC" in refs


@pytest.mark.asyncio
async def test_query_passes_context_to_llm() -> None:
    pipeline, _, _, _, llm = _make_pipeline()
    await pipeline.query("Which SWCs communicate over CAN?")
    llm.generate.assert_called_once()
    prompt: str = llm.generate.call_args[0][0]
    # Prompt must contain the retrieved chunk text and the original question.
    assert "EngineControlSWC" in prompt
    assert "Which SWCs communicate over CAN?" in prompt


@pytest.mark.asyncio
async def test_query_includes_graph_context_in_prompt_when_present() -> None:
    pipeline, _, _, _, llm = _make_pipeline(
        graph_context="SWC: EngineControlSWC (classic) | Ports: FuelInjectionPort (provided)"
    )
    await pipeline.query("test")
    prompt: str = llm.generate.call_args[0][0]
    assert "Graph context" in prompt
    assert "FuelInjectionPort" in prompt


@pytest.mark.asyncio
async def test_query_sources_match_milvus_hits() -> None:
    hits = [
        SearchResult(
            arxml_ref=f"/pkg/Comp{i}",
            document_name="doc",
            component_name=f"Comp{i}",
            text_chunk=f"chunk {i}",
            score=0.9 - i * 0.1,
        )
        for i in range(3)
    ]
    pipeline, *_ = _make_pipeline(milvus_hits=hits)
    result = await pipeline.query("test")
    assert len(result.sources) == 3
    assert result.sources[0].component_name == "Comp0"


@pytest.mark.asyncio
async def test_query_default_top_k() -> None:
    """When top_k is omitted, pipeline should use the default context_chunks value."""
    pipeline, _, milvus, *_ = _make_pipeline()
    await pipeline.query("test")
    # Default context_chunks = 5 in our fixture
    call_vec, call_kwargs = milvus.search.call_args
    actual_k = call_kwargs.get("top_k") or call_vec[1]
    assert actual_k == 5
