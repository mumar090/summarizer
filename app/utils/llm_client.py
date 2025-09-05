import os
import requests
from app.core.config import settings


class LLMClientError(Exception):
    pass


class OllamaClient:
    def __init__(self, base_url: str = settings.OLLAMA_BASE_URL, model: str = settings.OLLAMA_MODEL):
        self.base = base_url
        self.model = model


def summarize(self, prompt: str, max_tokens: int = 512, timeout: int = None) -> str:
    url = f"{self.base}/api/generate"
    payload = {
    "model": self.model,
    "prompt": prompt,
    "stream": False,
    "options": {"num_predict": max_tokens}
    }
    try:
        resp = requests.post(url, json=payload, timeout=timeout or settings.REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        data = resp.json()
        # Ollama's response key may vary; commonly 'response'
        out = data.get("response") or data.get("text") or ""
        return out.strip()
    except Exception as e:
        raise LLMClientError(str(e))


ollama_client = OllamaClient()