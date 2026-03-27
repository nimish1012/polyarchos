# ADR-006: RAG Orchestration Library

**Date:** 2026-03-27
**Status:** Accepted

## Context

The RAG pipeline needs to orchestrate several steps: embed queries, retrieve context chunks,
enrich with graph data, construct prompts, and call the local LLM. Two dominant Python libraries
exist for RAG orchestration: **LangChain** (v0.2+) and **LlamaIndex** (v0.10+).

## Decision

Implement the RAG pipeline **without a framework** — use a thin, hand-rolled pipeline in
`services/rag-engine/src/rag_engine/pipeline.py` that calls the individual clients directly.

LangChain and LlamaIndex are removed from `pyproject.toml`. All orchestration is in ~80 lines
of explicit Python.

## Rationale

| Concern | LangChain | LlamaIndex | Hand-rolled |
|---|---|---|---|
| Dependency weight | ~150 transitive deps | ~80 transitive deps | 0 extra deps |
| Debug transparency | Abstraction layers obscure prompt | Similar | Direct — every step visible |
| Custom Neo4j graph enrichment | Requires custom retriever impl | Similar | Native async call |
| Offline constraint compliance | Needs careful config | Similar | Trivially enforced |
| Code reviewability | Chain DSL unfamiliar to new contributors | Similar | Plain Python |

The pipeline for polyarchos is a fixed four-step sequence (embed → retrieve → enrich → generate)
with no dynamic chaining or agent-style tool selection. Introducing a framework to orchestrate
four sequential function calls would add complexity without benefit.

If agentic behaviour (multi-step tool use, self-refinement loops) is added in a future phase,
re-evaluate LangChain or LlamaIndex at that point.

## Consequences

- **Positive**: Zero framework dependencies; pipeline logic is fully auditable.
- **Positive**: No framework version churn risk in a security-sensitive OEM context.
- **Positive**: Prompt template is a plain Python string — reviewable, diffable, easy to update.
- **Negative**: No built-in document loaders, text splitters, or memory management. These will
  need to be implemented if complexity grows.
- **Negative**: If the pipeline evolves toward multi-step agent reasoning, a framework may need
  to be introduced later (write a new ADR at that time).

## References

- [LangChain](https://python.langchain.com/)
- [LlamaIndex](https://docs.llamaindex.ai/)
