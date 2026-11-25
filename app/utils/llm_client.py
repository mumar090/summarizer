from functools import lru_cache
from typing import Protocol

import requests

from app.core.config import settings
from app.core.errors import SummarizationError, TransientError


class LLMClient(Protocol):
    """Anything that can turn a prompt into text. Swapping providers means one new class."""

    def generate(self, prompt: str, *, system: str | None = None, max_tokens: int = 512) -> str: ...


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float,
        temperature: float = 0.2,
        session: requests.Session | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self._session = session or requests.Session()

    def generate(self, prompt: str, *, system: str | None = None, max_tokens: int = 512) -> str:
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": self.temperature},
        }
        if system:
            payload["system"] = system

        try:
            resp = self._session.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise TransientError(f"LLM service unavailable ({exc.__class__.__name__})") from exc

        if resp.status_code == 429 or resp.status_code >= 500:
            raise TransientError(f"LLM service error (HTTP {resp.status_code})")
        if resp.status_code == 404:
            raise SummarizationError(
                f"Model '{self.model}' is not available on the Ollama server "
                f"(run `ollama pull {self.model}`)"
            )
        if resp.status_code >= 400:
            raise SummarizationError(f"LLM request rejected (HTTP {resp.status_code})")

        try:
            data = resp.json()
        except ValueError as exc:
            raise TransientError("LLM returned a malformed response") from exc

        text = (data.get("response") or "").strip()
        if not text:
            raise TransientError("LLM returned an empty response")
        return text


@lru_cache
def get_llm_client() -> LLMClient:
    return OllamaClient(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
        timeout=settings.LLM_TIMEOUT_SECONDS,
        temperature=settings.LLM_TEMPERATURE,
    )
