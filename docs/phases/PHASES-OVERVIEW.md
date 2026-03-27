# polyarchos — Build Phases Overview

**Project:** AUTOSAR Component Intelligence Platform
**Target Role:** Qorix QD Architect
**Stack:** Rust · TypeScript · Python · WASM · Neo4j · Milvus · Kubernetes

---

## Phase Status

| Phase | Title | Status | Detail |
|---|---|---|---|
| 0 | Foundation Scaffold | ✅ Complete | [Root README](../../README.md) |
| 1 | Proto Contracts | ✅ Complete | [proto/README.md](../../proto/README.md) |
| 2 | Core API (Rust gRPC + REST) | ✅ Complete | [core-api/README.md](../../services/core-api/README.md) · [PHASE-2-core-api.md](PHASE-2-core-api.md) |
| 3 | WASM Bindings | ✅ Complete | [wasm/README.md](../../wasm/README.md) · [PHASE-3-wasm-bindings.md](PHASE-3-wasm-bindings.md) |
| 4 | AI/ML Layer (Python RAG) | ✅ Complete | [rag-engine/README.md](../../services/rag-engine/README.md) · [PHASE-4-rag-engine.md](PHASE-4-rag-engine.md) |
| 5 | Frontend (React + TypeScript) | ✅ Complete | [frontend/README.md](../../frontend/README.md) · [PHASE-5-frontend.md](PHASE-5-frontend.md) |
| 6 | Infrastructure + GitOps | 🔜 Planned | [infra/README.md](../../infra/README.md) |
| 7 | CI/CD Hardening | 🔜 Planned | — |
| 8 | Documentation + Portfolio Polish | 🔜 Planned | — |

---

## Phase 3 — WASM Bindings

**Goal:** Compile AUTOSAR domain logic from `crates/domain` into a WASM module callable from TypeScript in the browser. Demonstrates multi-surface API ownership — the JD differentiator most candidates miss.

### What to build

- Move core ARXML parsing and component validation logic into `wasm/src/`
- Expose functions via `#[wasm_bindgen]`:
  - `parse_arxml(xml: &str) -> JsValue` — parses a raw ARXML string, returns a typed JS object
  - `validate_component(json: &str) -> ValidationResult` — validates a component against domain rules
  - `resolve_port_interfaces(json: &str) -> JsValue` — resolves port-interface relationships
  - `version() -> String` — already present, used by frontend to verify module load
- Auto-generate TypeScript type declarations via `wasm-bindgen`
- Publish `wasm/pkg/` as a local npm package consumed by `frontend/`
- Tests via `wasm-pack test --headless --chrome`

### Files to create

| File | Purpose |
|---|---|
| `wasm/src/lib.rs` | Update with all `#[wasm_bindgen]` exports |
| `wasm/src/arxml.rs` | ARXML parsing logic (no network, no filesystem — pure WASM-safe) |
| `wasm/src/validation.rs` | Component validation rules |
| `wasm/src/types.rs` | JS-serialisable result types with `serde-wasm-bindgen` |
| `wasm/tests/` | wasm-pack browser tests |

### ADR to write

- **ADR-005:** WASM target selection — why `--target web` over `--target bundler`

### Verified when

```
wasm-pack build wasm/ --target web    ✓
wasm/pkg/polyarchos_wasm.js exists    ✓
wasm/pkg/polyarchos_wasm.d.ts exists  ✓ (TypeScript declarations)
wasm-pack test --headless --chrome    ✓
```

---

## Phase 4 — AI/ML Layer (Python RAG)

**Goal:** Build the RAG pipeline — ingest ARXML documents into Milvus (vector embeddings) and Neo4j (component graph), then answer natural-language questions about the AUTOSAR component landscape using a local LLM. No external AI API calls.

### What to build

#### 4a — Ingestion pipeline
- `scripts/ingest.py` CLI: parses ARXML → extracts SWCs, Ports, Interfaces → chunks text
- Embeds chunks using `fastembed` (local model: `BAAI/bge-small-en-v1.5`)
- Upserts vectors into Milvus collection `autosar_components`
- Creates nodes + edges in Neo4j:
  - Nodes: `SoftwareComponent`, `Port`, `Interface`
  - Edges: `HAS_PORT`, `IMPLEMENTS`, `REQUIRES`
- Idempotent on ARXML ref path (re-ingestion is safe)

#### 4b — RAG query pipeline
- `services/rag-engine/` gRPC server implementing `polyarchos.rag.v1.RagService`
- Query flow: embed question → Milvus similarity search → fetch graph context from Neo4j → build prompt → call Ollama local LLM → return grounded answer with source citations
- MCP tool definitions for `IngestDocument` and `Query` — enables LLM agent orchestration

#### 4c — Wire to core-api
- Replace stub `SearchComponents` handler in `core-api` with a real gRPC call to `rag-engine`
- Replace in-memory `ComponentStore` with Neo4j-backed store using `neo4rs`

### Files to create

| File | Purpose |
|---|---|
| `services/rag-engine/src/rag_engine/pipeline.py` | End-to-end RAG query pipeline |
| `services/rag-engine/src/rag_engine/ingestion.py` | ARXML ingestion: parse → embed → store |
| `services/rag-engine/src/rag_engine/milvus_client.py` | Milvus collection management + upsert |
| `services/rag-engine/src/rag_engine/neo4j_client.py` | Neo4j graph write + query |
| `services/rag-engine/src/rag_engine/llm.py` | Ollama local LLM interface |
| `services/rag-engine/src/rag_engine/embeddings.py` | fastembed model wrapper |
| `services/rag-engine/src/rag_engine/grpc_server.py` | tonic-compatible gRPC server via grpcio |
| `services/rag-engine/src/rag_engine/mcp_tools.py` | MCP tool definitions for agent use |
| `scripts/ingest.py` | CLI: `uv run python scripts/ingest.py --input data/sample.arxml` |
| `tests/fixtures/sample.arxml` | Synthetic ARXML fixture (no real OEM data) |
| `infra/docker-compose.dev.yml` | Neo4j + Milvus + Ollama containers for local dev |
| `services/core-api/src/store/neo4j.rs` | Neo4j-backed ComponentStore (replaces in-memory) |

### ADRs to write

- **ADR-006:** RAG orchestration library — LangChain vs. LlamaIndex
- **ADR-007:** Local LLM selection and model pinning (Ollama + mistral / llama3)
- **ADR-008:** Offline inference architecture — how models are loaded in air-gapped deployments

### Verified when

```
docker compose -f infra/docker-compose.dev.yml up -d   ✓
uv run python scripts/ingest.py --input tests/fixtures/sample.arxml  ✓
Milvus: vectors upserted for all SWCs in fixture        ✓
Neo4j: SWC nodes + Port/Interface edges created         ✓
rag-engine gRPC server responds to QueryRequest         ✓
core-api SearchComponents returns real vector results   ✓
```

---

## Phase 5 — Frontend (React + TypeScript)

**Goal:** A React dashboard that uses the WASM module for in-browser ARXML validation and calls the core-api REST/gRPC endpoints for data. Demonstrates TypeScript strict-mode governance — not just review.

### What to build

#### Pages

| Page | Route | Description |
|---|---|---|
| Component Graph Explorer | `/graph` | Interactive force-directed graph of SWC relationships from Neo4j. Nodes = SWCs, edges = Port connections. Powered by `react-force-graph`. |
| Semantic Search | `/search` | Natural-language Q&A interface backed by the RAG pipeline. Shows the answer + source citations. |
| Component Browser | `/components` | Paginated table of all SWCs. Filter by Classic/Adaptive. Click to view detail with port list. |
| ARXML Validator | `/validate` | Drag-and-drop ARXML file → validated in-browser using the WASM module. Zero server round-trip. |
| API Playground | `/playground` | Embedded Swagger UI for the core-api REST surface. |

#### Technical requirements

- **TypeScript strict:** `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`
- **API types** generated from `docs/api/v1/openapi.json` via `openapi-typescript` — never hand-written
- **WASM module** loaded via dynamic `import()` from `wasm/pkg/`
- **TanStack Query** for all server state — no `useEffect` + `useState` fetching
- **Zustand** for client state (selected component, search history)
- **React Router v6** for navigation
- **Error boundaries** on every route-level component
- **Vitest + React Testing Library** for tests

### Files to create

| File | Purpose |
|---|---|
| `frontend/index.html` | Vite entry point |
| `frontend/vite.config.ts` | Vite config with WASM support |
| `frontend/tsconfig.json` | Strict TypeScript config |
| `frontend/src/main.tsx` | React 18 root |
| `frontend/src/App.tsx` | Router + error boundary shell |
| `frontend/src/pages/GraphExplorer.tsx` | Neo4j graph visualisation |
| `frontend/src/pages/SemanticSearch.tsx` | RAG Q&A interface |
| `frontend/src/pages/ComponentBrowser.tsx` | Paginated SWC list |
| `frontend/src/pages/ArxmlValidator.tsx` | In-browser WASM validation |
| `frontend/src/pages/ApiPlayground.tsx` | SwaggerUI embed |
| `frontend/src/api/client.ts` | Type-safe API client from OpenAPI spec |
| `frontend/src/store/ui.ts` | Zustand UI state |
| `frontend/src/components/` | Shared UI components |
| `package.json` (frontend) | React 18, Vite, TanStack Query, Zustand, Router |

### ADR to write

- **ADR-009:** Frontend state management — TanStack Query + Zustand split

### Verified when

```
npm run typecheck -w frontend   ✓  (0 type errors)
npm run lint -w frontend        ✓  (0 lint errors)
npm run test -w frontend        ✓  (all tests pass)
npm run build -w frontend       ✓  (production bundle)
WASM validator works in browser ✓  (parses sample.arxml client-side)
Graph explorer renders SWCs     ✓  (from live core-api)
```

---

## Phase 6 — Infrastructure + GitOps

**Goal:** Define the full Kubernetes topology and wire GitOps delivery. Demonstrates multi-node cluster design, storage planning, namespace isolation, and GitOps maturity — all explicitly in the JD.

### What to build

#### Kubernetes manifests (`infra/k8s/`)

**Namespace: `platform`**
| Resource | Description |
|---|---|
| `Deployment/core-api` | 2 replicas, resource limits, liveness + readiness probes on both ports |
| `Service/core-api-grpc` | ClusterIP, port 50051 |
| `Service/core-api-rest` | ClusterIP, port 8080 |
| `Deployment/rag-engine` | 1 replica (GPU-bound in prod), resource requests for memory |
| `Service/rag-engine` | ClusterIP, port 50052 |
| `NetworkPolicy/platform` | Allow only intra-namespace + ingress from `frontend` namespace |

**Namespace: `data`**
| Resource | Description |
|---|---|
| `StatefulSet/neo4j` | Single node (dev), SHA-pinned image, PVC for data |
| `PersistentVolumeClaim/neo4j-data` | 10Gi, ReadWriteOnce |
| `Service/neo4j` | ClusterIP, bolt 7687 + http 7474 |
| `StatefulSet/milvus` | etcd + minio + milvus standalone, SHA-pinned |
| `PersistentVolumeClaim/milvus-data` | 20Gi, ReadWriteOnce |
| `Service/milvus` | ClusterIP, port 19530 |
| `SealedSecret/db-credentials` | Neo4j + Milvus credentials (never plaintext) |

**Namespace: `frontend`**
| Resource | Description |
|---|---|
| `Deployment/frontend` | Nginx serving the built React app, SHA-pinned |
| `Service/frontend` | ClusterIP, port 80 |
| `Ingress/frontend` | Routes `/api/` to core-api-rest, `/` to frontend |

**Namespace: `observability`**
| Resource | Description |
|---|---|
| `Deployment/prometheus` | Scrapes core-api metrics endpoint |
| `Deployment/grafana` | Dashboard for API latency + error rates |

#### GitOps (`infra/gitops/`)

- Flux `Kustomization` resources pointing to `infra/k8s/` per namespace
- `HelmRelease` for Prometheus stack (if using Flux)
- Image update automation: Flux `ImageRepository` + `ImagePolicy` watches the registry and opens a PR when a new SHA is pushed

#### Config (`config/`)

- `config/image-pins.yaml` — audit registry for all pinned image SHAs
- `config/schemas/image-pins.schema.json` — JSON Schema for the above
- `config/schemas/core-api.schema.json` — JSON Schema for core-api YAML config

### ADRs to write

- **ADR-010:** GitOps controller selection — Flux vs. ArgoCD
- **ADR-011:** Secret management — Sealed Secrets vs. External Secrets Operator
- **ADR-012:** Neo4j topology — single node dev vs. Causal Cluster prod

### Verified when

```
kubectl apply -k infra/k8s/          ✓  (kind local cluster)
All pods reach Running state          ✓
core-api REST accessible via Ingress  ✓
Neo4j + Milvus PVCs bound             ✓
GitOps controller reconciles on push  ✓
No :latest image references anywhere  ✓
```

---

## Phase 7 — CI/CD Hardening

**Goal:** Make the full 11-step CI pipeline green and implement the release automation. Every PR must pass all checks before merge.

### What to build

#### CI pipeline (`.github/workflows/ci.yml`) — complete all 11 steps

Currently the workflow file exists but several jobs have stub steps. Complete:

| Step | Tool | Current state |
|---|---|---|
| 1. buf lint + breaking | buf | ✅ Done |
| 2. cargo fmt | rustfmt | ✅ Done |
| 3. cargo clippy | clippy `-D warnings` | ✅ Done |
| 4. cargo test | cargo | ⚠️ No tests yet |
| 5. wasm-pack build + test | wasm-pack | ⚠️ Phase 3 prerequisite |
| 6. mypy --strict | mypy | ⚠️ No Python code yet |
| 7. ruff check + format | ruff | ⚠️ No Python code yet |
| 8. pytest | pytest | ⚠️ No tests yet |
| 9. npm typecheck + lint + test | vite/vitest | ⚠️ Phase 5 prerequisite |
| 10. Docker build | docker | ⚠️ No Dockerfile yet |
| 11. Image SHA lint | grep | ✅ Done |

#### Release pipeline (`.github/workflows/release.yml`)

- Triggered on `v*` tag push
- Builds Docker images for `core-api` and `rag-engine`
- Tags with semver + SHA256 digest
- Pushes to GitHub Container Registry (`ghcr.io`)
- Opens an automated PR to `infra/gitops/` updating the image digests

#### Dockerfiles

| File | Base image (SHA-pinned) |
|---|---|
| `services/core-api/Dockerfile` | `rust:1.78-slim@sha256:<digest>` → multi-stage → `debian:bookworm-slim@sha256:<digest>` |
| `services/rag-engine/Dockerfile` | `python:3.12-slim@sha256:<digest>` |
| `frontend/Dockerfile` | `node:20-alpine@sha256:<digest>` → `nginx:alpine@sha256:<digest>` |

#### Tests to write

| Location | What to test |
|---|---|
| `services/core-api/src/store/mod.rs` | Unit tests for CRUD + pagination |
| `services/core-api/src/rest/` | Integration tests with `axum::test` |
| `services/core-api/src/grpc/` | Integration tests with tonic test client |
| `services/rag-engine/tests/` | Pipeline unit tests with mocked Milvus/Neo4j |
| `wasm/tests/` | wasm-pack browser tests |
| `frontend/src/` | Component tests via Vitest + RTL |

### Verified when

```
All 11 CI steps green on a feature branch PR   ✓
cargo test --workspace passes                  ✓
Release tag v0.1.0 triggers release pipeline   ✓
Docker images pushed to ghcr.io with SHA tag   ✓
GitOps PR opened with updated image digest     ✓
```

---

## Phase 8 — Documentation + Portfolio Polish

**Goal:** Produce the documentation artefacts that will be read before the interview. ADRs and C4 diagrams are explicitly named in the JD. This phase turns a working codebase into a visible portfolio piece.

### What to build

#### C4 Architecture Diagrams (`docs/architecture/`)

Using Structurizr DSL or C4-PlantUML:

| Diagram | Level | Description |
|---|---|---|
| `context.puml` | L1 — Context | polyarchos in relation to OEM toolchains, ECU flash tools, and automotive engineers |
| `containers.puml` | L2 — Container | All deployable units: core-api, rag-engine, graph-service, frontend, Neo4j, Milvus, Ollama |
| `components-core-api.puml` | L3 — Component | Internal structure of core-api: gRPC layer, REST layer, store, config |
| `components-rag-engine.puml` | L3 — Component | Internal structure of rag-engine: ingestion pipeline, vector search, graph enrichment, LLM |

#### ADRs (complete set)

| ADR | Topic | Phase written |
|---|---|---|
| ADR-001 | Monorepo structure | Phase 0 ✅ |
| ADR-002 | Language selection per service | Phase 0 ✅ |
| ADR-003 | Proto-first API design | Phase 1 ✅ |
| ADR-004 | Dual-server gRPC + REST | Phase 2 ✅ |
| ADR-005 | WASM target selection | Phase 3 |
| ADR-006 | RAG orchestration library | Phase 4 |
| ADR-007 | Local LLM selection | Phase 4 |
| ADR-008 | Offline inference architecture | Phase 4 |
| ADR-009 | Frontend state management | Phase 5 |
| ADR-010 | GitOps controller selection | Phase 6 |
| ADR-011 | Secret management | Phase 6 |
| ADR-012 | Neo4j topology | Phase 6 |

#### RFC Document (`docs/rfc/`)

- **RFC-001: Offline Inference Strategy** — Proposes the model registry design, checksum verification, and air-gapped deployment model. This is the document that most directly addresses the OEM data privacy requirement from the JD.

#### Supporting docs

| File | Purpose |
|---|---|
| `README.md` | Project overview, architecture diagram embed, quick-start |
| `docs/onboarding.md` | Full local setup walkthrough: prerequisites, clone, `dev-up.sh`, populate DB |
| `CHANGELOG.md` | Keep a Changelog format, entries for each phase |
| `docs/api/v1/openapi.json` | Committed OpenAPI spec (generated by utoipa, diffable) |

### Verified when

```
README renders correctly on GitHub               ✓
C4 diagrams match actual deployed topology       ✓
All 12 ADRs written and cross-referenced         ✓
RFC-001 accepted status                          ✓
CHANGELOG.md has entries for all 8 phases        ✓
docs/onboarding.md: someone else can clone+run  ✓
```

---

## Dependency Map Between Phases

```
Phase 3 (WASM)
  └── required by Phase 5 (Frontend — WASM module import)

Phase 4 (RAG/AI)
  ├── required by Phase 2 stub replacement (SearchComponents → Milvus)
  ├── required by Phase 5 (Semantic Search page)
  └── required by Phase 6 (Neo4j + Milvus k8s manifests)

Phase 5 (Frontend)
  ├── requires Phase 3 (WASM)
  └── requires Phase 4 (RAG Q&A page, live search)

Phase 6 (Infra)
  └── required by Phase 7 (Dockerfiles + release pipeline)

Phase 7 (CI/CD)
  ├── requires Phase 3 (wasm-pack test step)
  ├── requires Phase 4 (pytest step)
  └── requires Phase 5 (npm test step)

Phase 8 (Docs)
  └── requires all phases complete (C4 diagrams reflect real topology)
```

---

## Key JD Signal per Phase

| Phase | Primary JD requirement demonstrated |
|---|---|
| 3 — WASM | Multi-API-surface platforms (WASM target), cross-compilation |
| 4 — RAG/AI | RAG pipeline design, Milvus, Neo4j, offline inference, MCP |
| 5 — Frontend | TypeScript strict governance, React architectural decisions |
| 6 — Infra | Kubernetes topology, storage class/PV planning, GitOps |
| 7 — CI/CD | Trunk-based dev, SHA-pinned artifacts, Docker lifecycle |
| 8 — Docs | ADRs, RFCs, C4 modelling, published technical writing |
