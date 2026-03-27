"""Ollama local LLM client.

Calls the Ollama HTTP API (``POST /api/generate``) with streaming disabled.
All inference runs on-device — no external API keys, no outbound traffic
to public AI services. This is a hard requirement for OEM air-gapped deployments.

See: https://github.com/ollama/ollama/blob/main/docs/api.md
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "mistral:7b-instruct"
_DEFAULT_TIMEOUT_S = 120


class OllamaClient:
    """HTTP client for the Ollama local inference server.

    Wraps ``POST /api/generate`` with ``stream=false``. Uses only stdlib
    ``urllib`` so there is no extra dependency beyond the standard library.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = _DEFAULT_MODEL,
        timeout_s: int = _DEFAULT_TIMEOUT_S,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s

    @property
    def model_id(self) -> str:
        """The Ollama model tag in use (e.g. ``mistral:7b-instruct``)."""
        return self._model

    def generate(self, prompt: str) -> str:
        """Send a prompt to Ollama and return the complete response text.

        Args:
            prompt: The full prompt string, including any system context and
                retrieved RAG chunks assembled by the pipeline.

        Returns:
            The model's response as a plain string.

        Raises:
            RuntimeError: If Ollama is unreachable or returns an HTTP error.
        """
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
                "Ensure Ollama is running: `ollama serve` and the model is pulled: "
                f"`ollama pull {self._model}`"
            ) from exc
