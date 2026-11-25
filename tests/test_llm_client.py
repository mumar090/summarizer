from unittest.mock import MagicMock

import pytest
import requests

from app.core.errors import SummarizationError, TransientError
from app.utils.llm_client import OllamaClient


def _client(response=None, side_effect=None):
    session = MagicMock()
    session.post.return_value = response
    session.post.side_effect = side_effect
    return OllamaClient("http://ollama:11434/", "gemma3:1b", timeout=5, session=session), session


def _resp(status=200, json=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json if json is not None else {}
    return r


def test_sends_prompt_and_returns_text():
    client, session = _client(_resp(json={"response": "  The summary.  "}))
    assert client.generate("prompt", system="sys", max_tokens=100) == "The summary."
    url = session.post.call_args.args[0]
    payload = session.post.call_args.kwargs["json"]
    assert url == "http://ollama:11434/api/generate"
    assert payload["system"] == "sys"
    assert payload["options"]["num_predict"] == 100
    assert payload["stream"] is False


@pytest.mark.parametrize("exc", [requests.Timeout(), requests.ConnectionError()])
def test_network_errors_are_transient(exc):
    client, _ = _client(side_effect=exc)
    with pytest.raises(TransientError):
        client.generate("p")


@pytest.mark.parametrize("status", [500, 503, 429])
def test_server_errors_are_transient(status):
    client, _ = _client(_resp(status))
    with pytest.raises(TransientError):
        client.generate("p")


def test_missing_model_is_permanent_with_actionable_message():
    client, _ = _client(_resp(404))
    with pytest.raises(SummarizationError, match="ollama pull gemma3:1b") as exc:
        client.generate("p")
    assert not isinstance(exc.value, TransientError)


def test_empty_response_is_transient():
    client, _ = _client(_resp(json={"response": ""}))
    with pytest.raises(TransientError):
        client.generate("p")
