from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Raised on HTTP error, timeout, or malformed response from Ollama."""


class OllamaClient:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen:7b",
        fallback_model: str = "llama3:8b",
        timeout: int = 30,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self.model = model
        self.fallback_model = fallback_model
        self._timeout = timeout

    def generate(self, prompt: str, model: str | None = None) -> str:
        """
        POST /api/generate with stream=false.
        Returns the response text string.
        Raises OllamaError on any failure.
        """
        use_model = model or self.model
        url = f"{self._base_url}/api/generate"
        payload = json.dumps({
            "model": use_model,
            "prompt": prompt,
            "stream": False,
        }).encode()

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = resp.read().decode()
        except urllib.error.HTTPError as exc:
            raise OllamaError(f"HTTP {exc.code} from Ollama: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise OllamaError(f"Ollama unreachable: {exc.reason}") from exc
        except TimeoutError as exc:
            raise OllamaError(f"Ollama timeout after {self._timeout}s") from exc

        try:
            data = json.loads(body)
            response_text: str = data["response"]
        except (json.JSONDecodeError, KeyError) as exc:
            raise OllamaError(f"Malformed Ollama response: {body[:200]!r}") from exc

        logger.debug("ollama model=%s response=%r", use_model, response_text[:200])
        return response_text
