# CLAUDE.md — polyarchos

This file is read by Claude Code at the start of every session. Read it fully before making
architectural or code decisions.

---

## 1. Project Overview

**polyarchos** is an AUTOSAR Component Intelligence Platform. It ingests automotive ECU configurations
and specification documents, stores component relationships in a graph database (Neo4j), stores
semantic embeddings in a vector database (Milvus), and exposes a RAG-backed Q&A interface over both
gRPC and REST APIs.

**Why it exists:** Portfolio/demo project targeting the Qorix QD Architect role. It demonstrates
production-grade polyglot engineering across Rust, TypeScript, Python, and WASM, with a full MLOps
and infrastructure stack grounded in automotive domain knowledge.

**Domain context:**
- AUTOSAR Classic: static ECU software architecture. Components (SWCs) communicate via Ports and
  Interfaces defined in ARXML. Think tightly resource-constrained, MISRA-adjacent embedded systems.
- AUTOSAR Adaptive: POSIX-based, service-oriented (SOME/IP), used in high-compute ECUs (ADAS, IVI).
- The system must support **offline inference**. No production code may call external AI APIs
  (OpenAI, Anthropic, etc.). All inference is local (Ollama, vLLM, or similar).
- OEM data is considered confidential. No telemetry, no remote logging, no data exfiltration paths.

---

## 2. Monorepo Structure

```
polyarchos/
├── services/
│   ├── core-api/          # Rust: tonic (gRPC) + axum (REST), utoipa (OpenAPI codegen)
│   ├── rag-engine/        # Python: RAG pipeline, Milvus ingestion, local LLM interface
│   └── graph-service/     # Rust or Python TBD (see ADR-003): Neo4j queries, graph traversal
├── frontend/              # TypeScript strict + React + Vite
├── wasm/                  # Rust → WASM via wasm-bindgen; AUTOSAR domain logic for browser use
├── proto/                 # Protobuf definitions managed by buf; source of truth for all gRPC APIs
├── infra/
│   ├── k8s/               # Kubernetes manifests (multi-node); grouped by namespace
│   └── gitops/            # Flux or ArgoCD configs (see ADR-005); reconciles infra/ to cluster
├── config/                # YAML config-as-code; JSON Schema registry for all config shapes
├── scripts/               # Python tooling: data ingestion, ARXML parsing, local dev helpers
├── docs/
│   ├── adr/               # Architecture Decision Records (see §8)
│   └── rfc/               # RFC documents for significant design proposals (see §8)
├── .github/workflows/     # CI/CD pipelines
├── buf.yaml               # buf workspace configuration
├── Cargo.toml             # Rust workspace root (members: services/core-api, wasm)
├── package.json           # Node workspace root (workspaces: frontend)
└── pyproject.toml         # Python workspace root (uv; members: services/rag-engine, scripts)
```

When adding a new service or library, place it under the appropriate workspace root and register it
in the relevant workspace manifest (Cargo.toml, package.json, or pyproject.toml).

---

## 3. Tech Stack

### Rust (services/core-api, services/graph-service TBD, wasm/)
- **tonic** — gRPC server/client, generated from proto/ via tonic-build
- **axum** — REST HTTP server
- **utoipa** + **utoipa-swagger-ui** — OpenAPI 3 spec generation from axum handlers
- **serde** / **serde_json** — serialisation
- **tokio** — async runtime (multi-threaded)
- **tracing** + **tracing-subscriber** — structured logging
- **anyhow** / **thiserror** — error handling (thiserror for library crates, anyhow for binaries)
- **wasm-bindgen** — WASM bindings (wasm/ crate only)
- **neo4rs** — Neo4j Bolt driver (if graph-service is Rust)
- Rust edition: **2021**. MSRV: document in each crate's Cargo.toml.

### TypeScript / React (frontend/)
- **React 18+** with functional components and hooks only (no class components)
- **Vite** — bundler
- **TanStack Query** — server state management
- **Zustand** — client state
- **React Router v6** — routing
- **zod** — runtime schema validation (especially for API responses)
- tsconfig: `"strict": true`, `"noUncheckedIndexedAccess": true`, `"exactOptionalPropertyTypes": true`
- No `any`. No `as unknown as T` escape hatches without a block comment explaining the invariant.
- All API types must be derived from the OpenAPI spec (via openapi-typescript or similar) or from
  generated protobuf types — never hand-written duplicates.

### Python (services/rag-engine/, scripts/)
- **Python 3.12+**
- Type annotations required on all function signatures. Use `from __future__ import annotations`.
- **mypy** strict mode (`--strict`) must pass.
- **pymilvus** — Milvus vector DB client
- **neo4j** (official driver) — Neo4j client
- **sentence-transformers** or **fastembed** — local embedding models
- **langchain** or **llama-index** — RAG orchestration (document choice in an ADR)
- **pydantic v2** — data validation and settings management
- **pytest** — testing; no unittest
- Package management: **uv**; pyproject.toml is the source of truth.

### Protobuf / gRPC (proto/)
- **buf** manages linting, formatting, and breaking-change detection.
- Generated stubs land in each service's src directory (never committed — generated at build time).
- All .proto files follow buf lint defaults (BASIC ruleset + FIELD_NAMES_LOWER_SNAKE_CASE).
- API versioning via package namespaces: `polyarchos.core.v1`, `polyarchos.rag.v1`, etc.

### Infrastructure
- **Docker**: all images are SHA-pinned in manifests (no `:latest` tags anywhere).
- **Kubernetes**: manifests live in infra/k8s/, grouped by namespace subdirectory.
- **GitOps**: Flux or ArgoCD reconciles infra/ to the cluster (decision in ADR-005).

---

## 4. Build & Run Commands

### Rust workspace

```bash
cargo build --workspace
cargo test --workspace
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo fmt --check
cargo run -p core-api
```

### Proto / buf

```bash
buf lint
buf breaking --against '.git#branch=main'
buf generate
```

Always run `buf lint` and `buf breaking` before pushing any change to proto/.

### Python workspace

```bash
uv sync
uv run mypy services/rag-engine scripts --strict
uv run ruff check .
uv run ruff format --check .
uv run pytest services/rag-engine scripts -v
uv run python -m rag_engine.main
```

### Node / Frontend workspace

```bash
npm install
npm run dev -w frontend
npm run typecheck -w frontend
npm run lint -w frontend
npm run build -w frontend
npm run test -w frontend
```

### WASM crate

```bash
wasm-pack build wasm/ --target web
wasm-pack test wasm/ --headless --chrome
```

### Local dev stack

```bash
# Start Neo4j + Milvus via Docker Compose
docker compose -f infra/docker-compose.dev.yml up -d

# Ingest a sample ARXML file
uv run python scripts/ingest.py --input data/sample.arxml
```

---

## 5. Coding Conventions

### Rust

Enable these lints at the crate root (lib.rs or main.rs):

```rust
#![deny(clippy::all)]
#![deny(clippy::pedantic)]
#![deny(clippy::nursery)]
#![warn(clippy::cargo)]
#![deny(missing_docs)]  // for library crates
```

- No `unwrap()` or `expect()` in non-test code unless the invariant is locally proved; prefer `?`.
- Errors: `thiserror` in library crates; `anyhow` in binary entry points.
- All public API items must have doc comments (`///`).
- Async: all async functions must be cancel-safe or documented as not cancel-safe.
- Proto-generated types must not leak past the service boundary; define domain types and map them.
- WASM crate: all exported functions must be documented; no panics in WASM-exported paths.

### TypeScript

- `strict: true` in tsconfig — no exceptions.
- `noUncheckedIndexedAccess: true` — array/map accesses must handle undefined.
- `exactOptionalPropertyTypes: true` — distinguish `{a?: string}` from `{a: string | undefined}`.
- Prefer `type` over `interface` for data shapes; use `interface` for extension/augmentation.
- No barrel re-exports (`index.ts` re-exporting everything) — they slow down the TS language server.
- Components: one component per file, named export, colocate tests and styles.
- Async data: TanStack Query for all server state. Never `useEffect` + `useState` for fetching.
- Error boundaries: every route-level component must be wrapped.

### Python

- All function and method signatures must be fully annotated.
- `from __future__ import annotations` at the top of every module.
- Use `pydantic.BaseModel` for all I/O data structures.
- No mutable default arguments.
- Prefer `pathlib.Path` over `os.path` string manipulation.
- Logging: use `structlog` or stdlib `logging` with structured formatters — no bare `print()`.
- Tests: each test module mirrors the source module path.

### Protobuf

- Package name: `polyarchos.<domain>.<vN>` (e.g., `polyarchos.core.v1`).
- Service names: PascalCase. Method names: PascalCase. Message fields: snake_case.
- Every RPC must have a comment explaining its contract.
- Use `google.protobuf.Timestamp` for all timestamps; never raw int64 epoch fields.
- Enums: always include a `_UNSPECIFIED = 0` value.

### General

- All configuration (ports, hosts, model names, credentials) comes from environment variables or
  mounted config files — never hardcoded.
- Secrets are never committed. Use `.env.example` to document required variables.
- All config files in config/ must have a corresponding JSON Schema. Validate on load.

---

## 6. Architecture Principles

### C4 Modelling

docs/architecture/ contains C4 diagrams at each level:
- **Context (L1):** polyarchos in relation to OEM toolchains and engineers.
- **Container (L2):** each deployable unit (core-api, rag-engine, graph-service, frontend, DBs).
- **Component (L3):** internal structure of core-api and rag-engine.
- **Code (L4):** generated from code; do not maintain manually.

Use Structurizr DSL or C4-PlantUML. Keep diagrams in sync with major structural changes.

### Event-Driven Patterns

- Services communicate asynchronously where latency tolerance allows.
- Define event schemas in proto/ alongside RPC definitions.
- If a message broker is added, document in an ADR and define consumer group semantics explicitly.
- All event consumers must be idempotent. Document the idempotency key for each event type.

### API Versioning

- gRPC: version the package (`v1`, `v2`). Old versions are not removed until all consumers migrate.
- REST: version the URL path (`/api/v1/...`). Do not use headers for versioning.
- OpenAPI spec is generated by utoipa at build time and committed to docs/api/ for diff tracking.
- Never make unversioned breaking changes. Every breaking change requires a new version.

### Breaking-Change Policy

- `buf breaking` runs in CI against `main`. Any breaking change not paired with a version bump fails CI.
- Breaking REST changes require an updated OpenAPI spec and a migration note in the relevant ADR.

### Service Topology

- **core-api** is the single external-facing gateway. Frontend and external clients talk only to it.
- core-api calls rag-engine and graph-service internally (gRPC preferred).
- rag-engine and graph-service do not call each other directly.
- WASM crate is a pure library — no network calls, no side effects.

---

## 7. Key Constraints

**Offline inference (non-negotiable)**
Production deployments run fully air-gapped. No service may make outbound HTTP calls to public AI
APIs. Embedding models and LLMs must be loaded from a local model registry. Document model versions
and checksums in a dedicated config file.

**AUTOSAR domain accuracy**
- Use correct AUTOSAR terminology: SWC, Port, Interface, ComStack, BSW, RTE, ARXML.
- Classic vs. Adaptive distinctions matter. Do not conflate them.
- ARXML is XML-based. Parsing must use schema-aware tools; do not string-match ARXML.
- If unsure about a domain concept, add a TODO and flag it rather than guessing.

**OEM data privacy**
- No real OEM ARXML or ECU config data may be committed. Use synthetic test fixtures only
  (tests/fixtures/).
- The ingestion pipeline must support data-at-rest encryption (document the mechanism in an ADR).

**No `:latest` container images**
Every FROM line in a Dockerfile and every image reference in a Kubernetes manifest must use a
SHA256 digest or a pinned semver tag. CI enforces this via linting.

**No blanket test-skipping in CI**
`#[ignore]` or `pytest.mark.skip` are allowed only when paired with a tracking issue reference in
the annotation. Blanket skip flags in CI workflow files are prohibited.

---

## 8. Documentation Standards

### ADR Format

ADRs live in `docs/adr/`. Naming: `ADR-NNN-short-title.md`.

```markdown
# ADR-NNN: <Title>

**Date:** YYYY-MM-DD
**Status:** Proposed | Accepted | Superseded by ADR-XXX | Deprecated

## Context
## Decision
## Rationale
## Consequences
## References
```

ADRs are append-only. To reverse a decision, write a new ADR that supersedes the old one.

### RFC Format

RFCs live in `docs/rfc/`. Naming: `RFC-NNN-short-title.md`. Use for proposals requiring discussion
before a decision. RFCs precede ADRs on significant architectural questions.

```markdown
# RFC-NNN: <Title>

**Author:** <name>
**Date:** YYYY-MM-DD
**Status:** Draft | Under Review | Accepted | Rejected | Superseded

## Summary
## Motivation
## Detailed Design
## Drawbacks
## Alternatives Considered
## Open Questions
```

### Changelog

Maintain `CHANGELOG.md` at repo root following Keep a Changelog conventions. Every user-facing PR
adds an entry under `[Unreleased]`. Releases move the unreleased block to a versioned heading.

---

## 9. CI/CD Rules

### Branching Strategy

Trunk-based development. Only long-lived branch is `main`. All work on short-lived feature branches
(`feat/`, `fix/`, `chore/`, `docs/`, `infra/`). Feature flags gate incomplete work.

### CI Pipeline (per PR)

```
1.  buf lint + buf breaking (proto/)
2.  cargo fmt --check
3.  cargo clippy --workspace -- -D warnings
4.  cargo test --workspace
5.  wasm-pack build + wasm-pack test
6.  uv run mypy --strict
7.  uv run ruff check + ruff format --check
8.  uv run pytest
9.  npm run typecheck + npm run lint + npm run test (frontend/)
10. Docker image build (no push on PR)
11. Image SHA pinning lint (reject :latest references)
```

### Release Process

- Releases are tagged on `main`: `vMAJOR.MINOR.PATCH`.
- Tagging triggers the release pipeline: builds all Docker images, pushes to registry with the
  semver tag AND SHA256 digest, updates GitOps manifests via automated PR to infra/gitops/.
- Never push directly to the registry from a developer machine.
- Kubernetes manifests always reference the SHA256 digest, not the semver tag.

### GitOps

- The GitOps controller reconciles infra/gitops/ to the cluster.
- Manual `kubectl apply` to the production cluster is prohibited. All changes go through git.
- Secrets are managed via Sealed Secrets or External Secrets Operator — never plaintext in git.

---

## 10. Local Development Setup

Prerequisites: Rust (rustup), Node 20+, Python 3.12+, uv, buf, wasm-pack, Docker, kubectl.

```bash
git clone <repo-url> polyarchos && cd polyarchos
cargo fetch && uv sync && npm install
docker compose -f infra/docker-compose.dev.yml up -d
buf generate
cargo test --workspace && uv run pytest && npm run test -w frontend
```

See `docs/onboarding.md` for a detailed walkthrough including populating databases with synthetic
fixtures.

---

## Quick Reference: Where Does X Go?

| Thing | Location |
|---|---|
| New gRPC API | proto/ + ADR if it's a new service |
| New REST endpoint | services/core-api/src/routes/ |
| New RAG capability | services/rag-engine/ |
| Graph query / traversal | services/graph-service/ |
| New React page | frontend/src/pages/ |
| AUTOSAR domain logic (browser) | wasm/src/ |
| Kubernetes resource | infra/k8s/\<namespace\>/ |
| GitOps reconciliation config | infra/gitops/ |
| New config shape | config/ + JSON Schema in config/schemas/ |
| Architectural decision | docs/adr/ |
| Significant proposal | docs/rfc/ |
| Dev utility / ingestion script | scripts/ |
| Test fixtures (synthetic ARXML) | tests/fixtures/ |
