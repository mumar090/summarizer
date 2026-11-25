from unittest.mock import MagicMock

import pytest

from app.core.errors import SummarizationError, TransientError, UnsafeURLError
from app.utils import text_extraction
from app.utils.text_extraction import extract_main_text, fetch_url
from app.utils.url_safety import ensure_public_url

ARTICLE = "<p>" + "The rover collected rock samples near the crater rim. " * 8 + "</p>"
PAGE = f"""
<html><head><title>t</title><script>var tracking = 1;</script><style>p{{}}</style></head>
<body>
  <nav><a href="/">Home</a> <a href="/about">About us</a></nav>
  <article><h1>Mars mission update</h1>{ARTICLE}{ARTICLE}</article>
  <footer>Copyright 2025 Cookie settings</footer>
</body></html>
"""


def test_extracts_article_and_drops_boilerplate():
    text = extract_main_text(PAGE)
    assert "rover collected rock samples" in text
    assert "tracking" not in text
    assert "Cookie settings" not in text


def test_keeps_paragraph_breaks():
    text = extract_main_text(PAGE)
    assert "\n\n" in text


def test_fallback_for_non_article_pages():
    html = "<html><body><div>Short status page: all systems operational.</div></body></html>"
    assert "all systems operational" in extract_main_text(html)


@pytest.mark.parametrize(
    "url", ["http://127.0.0.1/", "http://10.0.0.5/x", "http://169.254.169.254/latest", "http://[::1]/"]
)
def test_rejects_private_addresses(url):
    with pytest.raises(UnsafeURLError):
        ensure_public_url(url)


def test_rejects_non_http_schemes():
    with pytest.raises(UnsafeURLError):
        ensure_public_url("file:///etc/passwd")


def test_accepts_public_ip():
    ensure_public_url("http://93.184.216.34/")


def _response(status=200, headers=None, body=b""):
    resp = MagicMock()
    resp.status_code = status
    resp.headers = headers or {"Content-Type": "text/html; charset=utf-8"}
    resp.is_redirect = status in (301, 302, 303, 307, 308)
    resp.iter_content.return_value = [body]
    resp.__enter__.return_value = resp
    return resp


@pytest.fixture
def fake_get(monkeypatch):
    get = MagicMock()
    monkeypatch.setattr(text_extraction._session, "get", get)
    return get


def test_redirect_to_private_address_is_blocked(fake_get):
    fake_get.return_value = _response(302, {"Location": "http://127.0.0.1/admin"})
    with pytest.raises(UnsafeURLError):
        fetch_url("http://93.184.216.34/")


def test_server_errors_are_transient(fake_get):
    fake_get.return_value = _response(503)
    with pytest.raises(TransientError):
        fetch_url("http://93.184.216.34/")


def test_client_errors_are_permanent(fake_get):
    fake_get.return_value = _response(404)
    with pytest.raises(SummarizationError) as exc:
        fetch_url("http://93.184.216.34/")
    assert not isinstance(exc.value, TransientError)


def test_rejects_unsupported_content_type(fake_get):
    fake_get.return_value = _response(200, {"Content-Type": "application/pdf"})
    with pytest.raises(SummarizationError, match="Unsupported content type"):
        fetch_url("http://93.184.216.34/")


def test_rejects_oversized_pages(fake_get, monkeypatch):
    monkeypatch.setattr(text_extraction.settings, "FETCH_MAX_BYTES", 10)
    fake_get.return_value = _response(200, body=b"x" * 11)
    with pytest.raises(SummarizationError, match="larger than"):
        fetch_url("http://93.184.216.34/")


def test_decodes_body(fake_get):
    fake_get.return_value = _response(200, body="Grüße".encode())
    assert fetch_url("http://93.184.216.34/") == "Grüße"
