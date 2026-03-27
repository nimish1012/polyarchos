# ADR-002: Language Selection Per Service

**Date:** 2026-03-26
**Status:** Accepted

## Context

Four services need language assignments. The choices must be justified against the target role's
requirements, not just personal preference.

## Decision

| Service / Layer     | Language   | Rationale |
|---------------------|------------|-----------|
| `services/core-api` | Rust        | gRPC (tonic) + REST (axum) with zero-cost abstractions; WASM cross-compilation story |
| `services/rag-engine` | Python    | ML ecosystem (fastembed, langchain, pymilvus) has no viable Rust equivalent today |
| `services/graph-service` | Rust or Python | TBD in ADR-003 once graph query complexity is understood |
| `frontend/`         | TypeScript | React ecosystem; strict-mode TS demonstrates governance-level depth |
| `wasm/`             | Rust → WASM | Domain logic reusable in browser without a separate JS implementation |
| `crates/domain/`   | Rust        | Shared domain types; compiles to both native (core-api) and WASM targets |
| `scripts/`          | Python      | Ingestion tooling; best ergonomics for XML parsing (lxml) and data wrangling |
| `proto/`            | Protobuf    | Language-agnostic contract; stubs generated for Rust and Python at build time |

## Rationale

**Rust for core-api:**
- tonic and axum are production-grade and actively maintained
- utoipa provides OpenAPI 3 spec generation from handler annotations (explicit JD preference)
- The same codebase compiles to WASM (via `crates/domain/`), demonstrating cross-target capability
- Memory safety without a GC is relevant for long-lived gRPC connections

**Python for rag-engine:**
- fastembed, langchain, and pymilvus are Python-first libraries with no stable Rust equivalents
- mypy strict mode + pydantic v2 provides the type-safety story the JD requires
- The ML ecosystem expectation in the JD is Python; fighting it adds no signal

**TypeScript for frontend:**
- React 18 + strict TS (noUncheckedIndexedAccess, exactOptionalPropertyTypes) is the combination
  explicitly named in the JD
- API types generated from the utoipa-produced OpenAPI spec, not hand-written

## Consequences

- Developers need fluency in all four languages; this is intentional and matches the JD
- `crates/domain/` must remain `no_std`-compatible to compile to WASM (no network I/O, no filesystem)
- Python service must never be used for latency-sensitive synchronous paths; keep it async

## References

- ADR-003: graph-service language selection (pending)
