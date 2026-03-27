"""Settings loaded from environment variables or a .env file.

All configuration is externalised — no hardcoded hosts, credentials, or model names.
Prefix all env vars with ``RAG_`` (e.g. ``RAG_NEO4J_PASSWORD=secret``).
"""

from __future__ import annotations

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

    # ── Ollama (local LLM — never calls external APIs) ────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral:7b-instruct"
    ollama_timeout_s: int = 120

    # ── Embeddings ────────────────────────────────────────────────────────────
    # BAAI/bge-small-en-v1.5: 384-dim, ~130 MB, CPU-friendly, no GPU required.
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    # ── gRPC server ───────────────────────────────────────────────────────────
    grpc_port: int = 50052
    grpc_max_workers: int = 4

    # ── Ingestion ─────────────────────────────────────────────────────────────
    # Maximum characters per text chunk stored in Milvus.
    chunk_max_chars: int = 1024
    # Default number of context chunks retrieved per RAG query.
    context_chunks: int = 5


def get_settings() -> Settings:
    """Return a Settings instance populated from the environment."""
    return Settings()
