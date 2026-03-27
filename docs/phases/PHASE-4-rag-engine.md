# Phase 4 — Python RAG Engine

**Date completed:** 2026-03-27
**Branch:** master

---

## Goal

Build the AUTOSAR Component Intelligence Platform's AI/ML layer:
- Ingest ARXML documents → extract SWCs → embed → store in Milvus (vectors) + Neo4j (graph)
- Answer natural-language questions about the component landscape using local LLM (Ollama)
- Expose the pipeline over gRPC via `polyarchos.rag.v1.RagService`
- All inference runs locally — zero external AI API calls (OEM air-gap requirement)

---

## Architecture

```
ARXML file
    │
    ▼
arxml_parser.py ── parse XML, extract SWCs + Ports
    │
    ├──▶ embeddings.py ── fastembed (BAAI/bge-small-en-v1.5, local)
    │         │
    │         ▼
    │    milvus_client.py ── upsert FLOAT_VECTOR(384) chunks
    │
    └──▶ neo4j_client.py ── MERGE SoftwareComponent/Port/Interface nodes+edges
```

```
Query question
    │
    ▼
embeddings.py ── embed_one()
    │
    ▼
milvus_client.py ── similarity search (IVF_FLAT, IP metric)
    │
    ├──▶ neo4j_client.py ── get_component_context() (graph enrichment)
    │
    ▼
pipeline.py ── build prompt from chunks + graph context
    │
    ▼
llm.py ── POST /api/generate → Ollama (local)
    │
    ▼
QueryResult { answer, sources, model_id }
```

---

## Files created / modified

### Source modules (`services/rag-engine/src/rag_engine/`)

| File | Purpose |
|---|---|
| `config.py` | Pydantic Settings — all config from env vars (`RAG_*` prefix) |
| `arxml_parser.py` | XML-based ARXML parser — extracts SWCs, ports, ARXML paths |
| `embeddings.py` | fastembed `TextEmbedding` wrapper — batch + single embed |
| `milvus_client.py` | Milvus collection management, idempotent upsert, ANN search |
| `neo4j_client.py` | Async Neo4j client — MERGE nodes/edges, graph context query |
| `llm.py` | Ollama HTTP client — stdlib urllib only, no SDK dependency |
| `ingestion.py` | End-to-end ingest pipeline — parse → embed → Milvus + Neo4j |
| `pipeline.py` | RAG query pipeline — embed → retrieve → enrich → generate |
| `grpc_server.py` | gRPC servicer implementing `polyarchos.rag.v1.RagService` |
| `main.py` | Entry point — init all clients, start gRPC server |

### Tests (`services/rag-engine/tests/`)

| File | Tests |
|---|---|
| `test_arxml_parser.py` | 14 tests — parsing, path building, port extraction, fixture smoke test |
| `test_ingestion.py` | 7 tests — mocked Milvus/Neo4j/embedder, idempotency, variant labelling |
| `test_pipeline.py` | 8 tests — mocked pipeline components, prompt construction, source mapping |

**Total: 29 tests, 29 passed**

### Infrastructure

| File | Purpose |
|---|---|
| `tests/fixtures/sample.arxml` | Synthetic ARXML with 3 Classic + 1 Adaptive SWC (no real OEM data) |
| `infra/docker-compose.dev.yml` | Neo4j 5.20.0, Milvus standalone v2.4.8 (etcd + MinIO), Ollama 0.3.12 |
| `scripts/ingest.py` | CLI: `uv run python scripts/ingest.py --input <file>` |

### Dependency updates

`services/rag-engine/pyproject.toml`:
- Added `pydantic-settings>=2.0`
- Added `[project.scripts]` entry: `rag-engine = "rag_engine.main:main"`
- Added `[tool.mypy]`, `[tool.ruff]`, `[tool.pytest.ini_options]` config sections
- Removed `langchain` and `langchain-community` (see ADR-006)

---

## Key design decisions

### No RAG framework (ADR-006)
The pipeline is implemented as a fixed four-step sequence in ~80 lines of plain Python.
LangChain and LlamaIndex were removed — their abstractions add complexity without benefit
for this fixed pipeline. Every step is directly visible and debuggable.

### Offline inference (ADR-008)
- Embeddings: `fastembed` with `BAAI/bge-small-en-v1.5` — downloaded once to local cache,
  no network calls at inference time.
- LLM: `OllamaClient` calls `http://localhost:11434/api/generate` — only stdlib `urllib`,
  no external AI SDK dependency anywhere in the codebase.

### ARXML parsing
Uses `xml.etree.ElementTree` (stdlib) with namespace-stripping (`_strip_ns()`). Handles
the AUTOSAR 4.x namespace (`http://autosar.org/schema/conf/4.0`) transparently.
Supports: `APPLICATION-SW-COMPONENT-TYPE`, `SENSOR-ACTUATOR-SW-COMPONENT-TYPE`,
`COMPLEX-DEVICE-DRIVER-SW-COMPONENT-TYPE`, `ECU-ABSTRACTION-SW-COMPONENT-TYPE`,
`SERVICE-SW-COMPONENT-TYPE` (Classic) and `ADAPTIVE-APPLICATION-SW-COMPONENT-TYPE` (Adaptive).

### Idempotent ingestion
- Milvus: delete by `arxml_ref` expression before re-insert on every run
- Neo4j: all writes use `MERGE` — safe to re-run with updated ARXML

### Milvus schema
Collection `autosar_components`: id (PK auto), arxml_ref, document_name, component_name,
variant, text_chunk, embedding (FLOAT_VECTOR 384). Index: IVF_FLAT, IP metric
(inner product on L2-normalised vectors = cosine similarity).

---

## Sample fixture content

`tests/fixtures/sample.arxml` contains 4 synthetic SWCs:

| Name | Variant | Ports |
|---|---|---|
| `EngineControlSWC` | Classic | FuelInjectionPort (provided), EngineSpeedPort (required) |
| `BrakeControlSWC` | Classic | BrakePressurePort (provided), WheelSpeedPort (required) |
| `WheelSpeedSensorSWC` | Classic (SENSOR-ACTUATOR) | WheelSpeedOut (provided) |
| `PerceptionServiceSWC` | Adaptive | ObjectDetectionPort (provided), CameraFeedPort (required) |

---

## Local dev quickstart

```bash
# Start infrastructure
docker compose -f infra/docker-compose.dev.yml up -d

# Pull the LLM model (one-time, ~4 GB)
docker exec -it polyarchos-ollama ollama pull mistral:7b-instruct

# Ingest the sample fixture
uv run python scripts/ingest.py --input tests/fixtures/sample.arxml

# Start the gRPC server (requires buf generate first)
buf generate
uv run rag-engine
```

---

## What's stubbed / deferred

- **`grpc_server.py`**: Functional but requires `buf generate` to produce proto stubs before
  the server can start. The stub import uses `# type: ignore[import-not-found]`.
- **core-api wire-up (4c)**: Replacing the in-memory `ComponentStore` with Neo4j-backed reads
  and routing `SearchComponents` to rag-engine is deferred to Phase 5/7 to keep scope bounded.
- **Streaming LLM responses**: `OllamaClient` uses `stream=false` for simplicity. Streaming
  via gRPC server-side streaming is a future enhancement.
- **Text chunking strategy**: Each SWC is a single chunk. Multi-chunk strategy (split by port
  groups, description sections) would improve retrieval quality for large ARXML files.

---

## Architecture decisions written

- `docs/adr/ADR-006-rag-orchestration-library.md` — no framework, hand-rolled pipeline
- `docs/adr/ADR-007-local-llm-selection.md` — Ollama + mistral:7b-instruct
- `docs/adr/ADR-008-offline-inference-architecture.md` — air-gap model deployment strategy

---

## Next phase

**Phase 5 — Frontend (React + TypeScript)**:
- React 18 dashboard with WASM-powered in-browser ARXML validation
- Semantic Search page backed by rag-engine RAG pipeline
- Component Graph Explorer visualising Neo4j relationships
- All API types derived from generated OpenAPI spec (never hand-written)
