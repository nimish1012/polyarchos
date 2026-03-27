"""Settings loaded from environment variables or a .env file.

All configuration is externalised — no hardcoded hosts, credentials, or model names.
Prefix all env vars with ``RAG_`` (e.g. ``RAG_NEO4J_PASSWORD=secret``).

LLM provider selection
-----------------------
Set ``RAG_LLM_PROVIDER`` to one of:

``ollama`` (default)
    Local Ollama server. Fully offline. Requires ``RAG_OLLAMA_MODEL`` to be pulled.

``openai``
    OpenAI Chat Completions. Requires ``RAG_OPENAI_API_KEY``.
    Default model: ``gpt-4o-mini``.

``google``
    Google Generative AI (Gemini). Requires ``RAG_GOOGLE_API_KEY``.
    Default model: ``gemini-1.5-flash``.

``anthropic``
    Anthropic Messages API (Claude). Requires ``RAG_ANTHROPIC_API_KEY``.
    Default model: ``claude-sonnet-4-6``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the RAG engine service."""

    model_config = SettingsConfigDict(
        env_prefix="RAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Milvus ────────────────────────────────────────────────────────────────
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection: str = "autosar_components"

    # ── Neo4j ─────────────────────────────────────────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = Field(default="polyarchos")

    # ── LLM provider selection ────────────────────────────────────────────────
    llm_provider: Literal["ollama", "openai", "google", "anthropic"] = "ollama"

    # ── Ollama (local — offline-safe default) ─────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral:7b-instruct"
    ollama_timeout_s: int = 120

    # ── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_timeout_s: int = 60

    # ── Google Generative AI (Gemini) ─────────────────────────────────────────
    google_api_key: str = ""
    google_model: str = "gemini-2.0-flash"

    # ── Anthropic (Claude) ────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_max_tokens: int = 2048
    anthropic_timeout_s: int = 60

    # ── Embeddings ────────────────────────────────────────────────────────────
    # BAAI/bge-small-en-v1.5: 384-dim, ~130 MB, CPU-friendly, no GPU required.
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    # ── gRPC server ───────────────────────────────────────────────────────────
    grpc_port: int = 50052
    grpc_max_workers: int = 4

    # ── Ingestion ─────────────────────────────────────────────────────────────
    chunk_max_chars: int = 1024
    context_chunks: int = 5


def get_settings() -> Settings:
    """Return a Settings instance populated from the environment."""
    return Settings()
