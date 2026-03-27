"""LLM client implementations for the RAG pipeline.

Supported providers:
    - ``ollama``    — local Ollama server (default, offline-safe)
    - ``openai``    — OpenAI Chat Completions API
    - ``google``    — Google Generative AI (Gemini)
    - ``anthropic`` — Anthropic Messages API (Claude)

Select a provider via the ``RAG_LLM_PROVIDER`` environment variable.
Each provider reads its API key and model name from provider-specific env vars.
See :mod:`rag_engine.config` for the full variable reference.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ── Protocol ──────────────────────────────────────────────────────────────────


@runtime_checkable
class LlmClient(Protocol):
    """Structural protocol satisfied by every LLM backend.

    Any class that exposes :attr:`model_id` and :meth:`generate` is a valid
    client — no inheritance required.
    """

    @property
    def model_id(self) -> str:
        """Human-readable model identifier, e.g. ``gpt-4o-mini``."""
        ...

    def generate(self, prompt: str) -> str:
        """Send *prompt* to the LLM and return the complete response text.

        Args:
            prompt: Full prompt string assembled by the RAG pipeline.

        Returns:
            Model response as a plain string.

        Raises:
            RuntimeError: On connection failure, auth error, or API error.
        """
        ...


# ── Ollama (local) ─────────────────────────────────────────────────────────────


class OllamaClient:
    """HTTP client for the Ollama local inference server.

    Uses only stdlib ``urllib`` — no extra dependencies.
    Calls ``POST /api/generate`` with ``stream=false``.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "mistral:7b-instruct",
        timeout_s: int = 120,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s

    @property
    def model_id(self) -> str:
        return self._model

    def generate(self, prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1},
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout_s) as resp:
                body: dict[str, object] = json.loads(resp.read().decode("utf-8"))
                return str(body.get("response", ""))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Ollama is unreachable at {self._base_url}. "
                "Ensure Ollama is running (`ollama serve`) and the model is pulled: "
                f"`ollama pull {self._model}`"
            ) from exc


# ── OpenAI ────────────────────────────────────────────────────────────────────


class OpenAIClient:
    """OpenAI Chat Completions client.

    Requires the ``openai`` package and a valid ``RAG_OPENAI_API_KEY``.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        timeout_s: int = 60,
    ) -> None:
        try:
            from openai import OpenAI  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "The 'openai' package is required for the OpenAI provider. "
                "Install it: uv pip install openai"
            ) from exc

        self._model = model
        self._client = OpenAI(api_key=api_key, timeout=timeout_s)

    @property
    def model_id(self) -> str:
        return self._model

    def generate(self, prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            content = response.choices[0].message.content
            return content if content is not None else ""
        except Exception as exc:
            raise RuntimeError(f"OpenAI API error: {exc}") from exc


# ── Google Generative AI (Gemini) ─────────────────────────────────────────────


class GoogleClient:
    """Google Generative AI (Gemini) client.

    Requires the ``google-genai`` package and a valid ``RAG_GOOGLE_API_KEY``.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
    ) -> None:
        try:
            from google import genai  # type: ignore[import-untyped]
            from google.genai import types as genai_types  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "The 'google-genai' package is required for the Google provider. "
                "Install it: uv pip install google-genai"
            ) from exc

        self._model_name = model
        self._client = genai.Client(api_key=api_key)
        self._config = genai_types.GenerateContentConfig(temperature=0.1)

    @property
    def model_id(self) -> str:
        return self._model_name

    def generate(self, prompt: str) -> str:
        try:
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=prompt,
                config=self._config,
            )
            return str(response.text)
        except Exception as exc:
            raise RuntimeError(f"Google Generative AI error: {exc}") from exc


# ── Anthropic (Claude) ────────────────────────────────────────────────────────


class AnthropicClient:
    """Anthropic Messages API client (Claude).

    Requires the ``anthropic`` package and a valid ``RAG_ANTHROPIC_API_KEY``.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 2048,
        timeout_s: int = 60,
    ) -> None:
        try:
            import anthropic  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "The 'anthropic' package is required for the Anthropic provider. "
                "Install it: uv pip install anthropic"
            ) from exc

        self._model = model
        self._max_tokens = max_tokens
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout_s)

    @property
    def model_id(self) -> str:
        return self._model

    def generate(self, prompt: str) -> str:
        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            block = message.content[0]
            # TextBlock has a .text attribute; guard for safety.
            return str(getattr(block, "text", ""))
        except Exception as exc:
            raise RuntimeError(f"Anthropic API error: {exc}") from exc


# ── Factory ───────────────────────────────────────────────────────────────────


def create_llm_client(
    provider: str,
    *,
    # Ollama
    ollama_base_url: str = "http://localhost:11434",
    ollama_model: str = "mistral:7b-instruct",
    ollama_timeout_s: int = 120,
    # OpenAI
    openai_api_key: str = "",
    openai_model: str = "gpt-4o-mini",
    openai_timeout_s: int = 60,
    # Google
    google_api_key: str = "",
    google_model: str = "gemini-2.0-flash",
    # Anthropic
    anthropic_api_key: str = "",
    anthropic_model: str = "claude-sonnet-4-6",
    anthropic_max_tokens: int = 2048,
    anthropic_timeout_s: int = 60,
) -> LlmClient:
    """Instantiate the configured LLM backend.

    Args:
        provider: One of ``"ollama"``, ``"openai"``, ``"google"``, ``"anthropic"``.
        All remaining kwargs are provider-specific settings forwarded to the
        respective client constructor.

    Returns:
        An :class:`LlmClient`-compatible instance.

    Raises:
        ValueError: If *provider* is not a recognised value.
        RuntimeError: If the required SDK package is not installed or the API
            key is missing.
    """
    match provider:
        case "ollama":
            logger.info("LLM provider: Ollama", extra={"model": ollama_model})
            return OllamaClient(
                base_url=ollama_base_url,
                model=ollama_model,
                timeout_s=ollama_timeout_s,
            )
        case "openai":
            if not openai_api_key:
                raise RuntimeError(
                    "RAG_OPENAI_API_KEY is required when RAG_LLM_PROVIDER=openai"
                )
            logger.info("LLM provider: OpenAI", extra={"model": openai_model})
            return OpenAIClient(
                api_key=openai_api_key,
                model=openai_model,
                timeout_s=openai_timeout_s,
            )
        case "google":
            if not google_api_key:
                raise RuntimeError(
                    "RAG_GOOGLE_API_KEY is required when RAG_LLM_PROVIDER=google"
                )
            logger.info("LLM provider: Google Gemini", extra={"model": google_model})
            return GoogleClient(api_key=google_api_key, model=google_model)
        case "anthropic":
            if not anthropic_api_key:
                raise RuntimeError(
                    "RAG_ANTHROPIC_API_KEY is required when RAG_LLM_PROVIDER=anthropic"
                )
            logger.info("LLM provider: Anthropic", extra={"model": anthropic_model})
            return AnthropicClient(
                api_key=anthropic_api_key,
                model=anthropic_model,
                max_tokens=anthropic_max_tokens,
                timeout_s=anthropic_timeout_s,
            )
        case _:
            raise ValueError(
                f"Unknown LLM provider: {provider!r}. "
                "Choose from: ollama, openai, google, anthropic"
            )
