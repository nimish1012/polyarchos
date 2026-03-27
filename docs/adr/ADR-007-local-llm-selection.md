# ADR-007: Local LLM Selection and Model Pinning

**Date:** 2026-03-27
**Status:** Accepted

## Context

The RAG pipeline requires a language model to generate grounded answers from retrieved context.
The offline inference constraint (see CLAUDE.md §7 and ADR-008) prohibits any outbound calls to
public AI APIs. The model must run on the deployment host, CPU-only in the base case.

Options evaluated:

| Option | Pros | Cons |
|---|---|---|
| **Ollama** (local server) | Single binary, model management built-in, OpenAI-compatible API, active community | External process required |
| **vLLM** | High-throughput GPU inference | GPU required; high memory footprint |
| **llama.cpp** (direct) | CPU-optimised GGUF, no extra process | Python binding complexity; manual model management |
| **HuggingFace Transformers** | Most model choice | Large dependency tree; no built-in serving layer |

## Decision

Use **Ollama** as the local inference runtime with **`mistral:7b-instruct`** as the default model.

- Ollama is started as a sidecar container in the dev compose stack (`infra/docker-compose.dev.yml`).
- In Kubernetes, Ollama runs as a `Deployment` in the `platform` namespace (Phase 6).
- The `OllamaClient` in `llm.py` calls `POST /api/generate` with `stream=false` over HTTP.
  Uses only stdlib `urllib` — no extra Python dependencies.

Model pin:

```
ollama/ollama:0.3.12   (Docker image, dev compose)
mistral:7b-instruct    (model pulled on first start)
```

## Rationale

- **Simplicity**: Ollama's REST API (`/api/generate`) is trivial to call from Python without
  any SDKs. The entire client is ~50 lines of stdlib code.
- **Model management**: `ollama pull <model>` handles quantization, download, and caching.
  No manual GGUF download or model registry setup required for development.
- **Air-gap readiness**: For production deployments, pre-pull the model and volume-mount
  `/root/.ollama` from a pre-populated image. The Ollama server has no outbound dependency
  at inference time.
- **mistral:7b-instruct**: Strong instruction-following at 7B parameters, 4-bit quantized
  (~4 GB RAM). Runs on CPU with acceptable latency for a developer tool (not a latency-critical
  system).

## Model Registry and Checksums

Production deployments must pin the model digest, not just the tag. Document in
`config/model-registry.yaml` (to be created in Phase 6):

```yaml
models:
  - name: mistral:7b-instruct
    digest: sha256:<blake2b-digest-from-ollama-manifest>
    size_gb: 4.1
    use_case: rag_generation
```

CI validation of this file is deferred to Phase 7.

## Consequences

- **Positive**: Fully offline inference after initial model pull.
- **Positive**: No Python SDK dependency for LLM calls.
- **Positive**: Ollama supports many open-source models — easy to swap in Llama 3, Phi-3, etc.
  by changing `RAG_OLLAMA_MODEL` env var.
- **Negative**: Requires Ollama to be running as a separate process/container. The `OllamaClient`
  throws `RuntimeError` with a helpful message if Ollama is unreachable.
- **Negative**: CPU-only inference with mistral:7b is slow (~5–30 s/response depending on hardware).
  Production should use GPU-enabled Ollama or switch to vLLM (write a new ADR).

## References

- [Ollama project](https://github.com/ollama/ollama)
- [Mistral 7B Instruct](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2)
- [Ollama API docs](https://github.com/ollama/ollama/blob/main/docs/api.md)
