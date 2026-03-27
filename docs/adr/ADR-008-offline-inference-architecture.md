# ADR-008: Offline Inference Architecture

**Date:** 2026-03-27
**Status:** Accepted

## Context

polyarchos targets OEM automotive environments where:

1. **Air-gapped networks**: ECU development workstations and CI/CD clusters have no outbound
   internet access.
2. **OEM data confidentiality**: ARXML files and ECU configurations may contain IP-sensitive
   signal names, component identifiers, and system topology. No data may leave the OEM network.
3. **Regulatory risk**: Sending automotive ECU data to a public AI API could violate NDAs,
   ITAR, or EAR export regulations in some jurisdictions.

These constraints are non-negotiable. Any architecture that requires an outbound HTTP call to an
AI API (OpenAI, Anthropic, Google, Cohere, etc.) is disqualified.

## Decision

All inference in polyarchos runs locally on the deployment host or cluster. The architecture has
two offline inference components:

### 1. Embedding model (fastembed)

- Model: `BAAI/bge-small-en-v1.5` (384-dim, ~130 MB)
- Runtime: fastembed downloads the model to `~/.cache/fastembed/` on first use.
- **Air-gap deployment**: pre-populate the fastembed cache directory from a trusted artifact
  store and set `FASTEMBED_CACHE_PATH` to the mounted volume path.
- No network call is made at inference time — only at initial model download.

### 2. Language model (Ollama)

- Model: `mistral:7b-instruct` (4-bit quantized, ~4 GB)
- Runtime: Ollama serves the model as a local HTTP server at `http://localhost:11434`.
- **Air-gap deployment**: pre-pull the model into a Docker image layer:
  ```dockerfile
  FROM ollama/ollama:0.3.12 AS model-seed
  RUN ollama pull mistral:7b-instruct
  ```
  Volume-mount `/root/.ollama` from this pre-built image in k8s (see Phase 6).
- No network call is made at inference time.

### Enforcement

The code enforces this at the module level:

- `rag_engine/llm.py`: Uses only `urllib` (stdlib). No `openai`, `anthropic`, or similar imports
  are permitted. Any PR adding such an import will fail a `ruff` rule (`banned-api`, Phase 7).
- `rag_engine/embeddings.py`: Uses only `fastembed`. No API-backed embedding providers.
- CI (Phase 7) will add a `grep`-based check that rejects any import of `openai`, `anthropic`,
  `cohere`, `vertexai`, or similar in the `services/` directory.

## Model Version Registry

All production model versions and checksums must be documented in `config/model-registry.yaml`
(to be created in Phase 6). Fields:

```yaml
models:
  - name: <model-identifier>
    provider: fastembed | ollama
    digest: sha256:<hash>          # blake2b for ollama, sha256 for fastembed ONNX
    size_gb: <float>
    use_case: embedding | rag_generation
    validated_on: <YYYY-MM-DD>     # date last validated on reference hardware
```

CI must validate that every model referenced in the codebase has an entry in the registry
(Phase 7 enforcement).

## Consequences

- **Positive**: Complete data isolation. No ARXML content ever leaves the OEM network.
- **Positive**: Offline operation — air-gapped cluster can run indefinitely without internet.
- **Positive**: No API cost, no rate-limiting, no vendor dependency for inference.
- **Negative**: Initial setup requires pulling model artifacts (~4 GB LLM + ~130 MB embedder).
  This is a one-time cost, handled by the infra bootstrapping process.
- **Negative**: Hardware requirements: minimum 8 GB RAM for CPU-only Mistral inference.
  GPU acceleration is opt-in (add `nvidia` runtime to Ollama deploy in k8s).
- **Negative**: Model update process is manual — no automatic fine-tuning or RLHF loop.
  This is acceptable for a read-only Q&A use case over static ARXML documents.

## References

- CLAUDE.md §7 — Key Constraints (Offline inference, OEM data privacy)
- ADR-007 — Local LLM selection (Ollama + Mistral)
- [fastembed air-gap docs](https://qdrant.github.io/fastembed/examples/cache/)
- [Ollama model file docs](https://github.com/ollama/ollama/blob/main/docs/modelfile.md)
