# ADR-003: Proto-First API Design

**Date:** 2026-03-26
**Status:** Accepted

## Context

polyarchos exposes APIs over both gRPC and REST. The question is whether to define the API contract
in Protobuf first (with REST derived from it) or to define REST handlers first and generate gRPC
from annotations.

## Decision

**Proto-first.** All API contracts are defined in `.proto` files under `proto/` and managed by
`buf`. Generated stubs (Rust via tonic-build, Python via grpcio-tools) are produced at build time
and never committed.

The two proto packages defined in Phase 1:
- `polyarchos.core.v1` — ComponentService: CRUD + semantic search over SWCs
- `polyarchos.rag.v1` — RagService: ARXML ingestion + RAG Q&A

REST endpoints in core-api mirror the gRPC surface but are defined separately in axum handlers,
with utoipa annotations generating the OpenAPI 3 spec. Proto types are mapped to domain types at
the service boundary — generated types do not leak into business logic.

## Rationale

- `buf lint` and `buf breaking` give us schema evolution guarantees in CI
- Proto is language-agnostic: Rust (core-api) and Python (rag-engine) share the same contract
- Breaking-change detection is automatic — any field removal or renaming fails `buf breaking`
- The JD explicitly lists `buf` as a preferred qualification; using it correctly demonstrates that

**Why not gRPC-gateway (proto → REST transcoding):**
- utoipa produces richer OpenAPI docs with less boilerplate
- Separate REST handlers allow REST-specific behaviour (pagination tokens, HTTP caching headers)
- Avoids a runtime transcoding proxy dependency

## Consequences

- All API changes start in `proto/` — no service code changes until proto is updated and regenerated
- `buf generate` must be run after any `.proto` change before `cargo build`
- `buf breaking --against '.git#branch=main'` runs in CI to block unversioned breaking changes
- Adding a new service requires a new proto package (`polyarchos.<service>.v1`) and a new buf plugin entry

## References

- [buf documentation](https://buf.build/docs)
- ADR-002: Language selection per service
