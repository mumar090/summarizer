import logging
import re
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from readability import Document as ReadabilityDoc

from app.core.config import settings
from app.core.errors import SummarizationError, TransientError
from app.utils.url_safety import ensure_public_url

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "SummarizerBot/1.0 (+https://github.com/mumar090/summarizer)",
    "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5",
}
SUPPORTED_CONTENT_TYPES = ("text/html", "application/xhtml+xml", "text/plain")
READABILITY_MIN_CHARS = 200

_BLOCK_TAGS = ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "pre", "blockquote", "td", "dd"]
_NOISE_TAGS = ["script", "style", "noscript", "nav", "footer", "header", "aside", "form", "svg"]
_CHARSET_RE = re.compile(r"charset=([\w-]+)", re.IGNORECASE)

_session = requests.Session()
_session.headers.update(DEFAULT_HEADERS)


def fetch_url(url: str) -> str:
    """Download a page, following redirects manually so every hop passes the SSRF check."""
    for _ in range(settings.FETCH_MAX_REDIRECTS + 1):
        if not settings.ALLOW_PRIVATE_URLS:
            ensure_public_url(url)
        host = urlsplit(url).hostname
        try:
            resp = _session.get(
                url, timeout=settings.FETCH_TIMEOUT_SECONDS, allow_redirects=False, stream=True
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise TransientError(f"Could not reach {host} ({exc.__class__.__name__})") from exc
        except requests.RequestException as exc:
            raise SummarizationError(f"Could not fetch URL: {exc.__class__.__name__}") from exc

        with resp:
            if resp.is_redirect and "Location" in resp.headers:
                url = urljoin(url, resp.headers["Location"])
                continue
            if resp.status_code == 429 or resp.status_code >= 500:
                raise TransientError(f"{host} returned HTTP {resp.status_code}")
            if resp.status_code >= 400:
                raise SummarizationError(f"Page returned HTTP {resp.status_code}")

            content_type = resp.headers.get("Content-Type", "")
            if content_type and not any(t in content_type for t in SUPPORTED_CONTENT_TYPES):
                raise SummarizationError(
                    f"Unsupported content type '{content_type.split(';')[0]}' (expected HTML or text)"
                )
            body = _read_limited(resp)
            match = _CHARSET_RE.search(content_type)
            encoding = match.group(1) if match else "utf-8"
            try:
                return body.decode(encoding, errors="replace")
            except LookupError:
                return body.decode("utf-8", errors="replace")

    raise SummarizationError("Too many redirects")


def _read_limited(resp: requests.Response) -> bytes:
    chunks, size = [], 0
    for chunk in resp.iter_content(chunk_size=64 * 1024):
        size += len(chunk)
        if size > settings.FETCH_MAX_BYTES:
            raise SummarizationError(f"Page is larger than {settings.FETCH_MAX_BYTES // 1_000_000} MB")
        chunks.append(chunk)
    return b"".join(chunks)


def extract_main_text(html: str) -> str:
    """Return the readable text of a page, keeping paragraph breaks.

    Readability isolates the main article (dropping nav, ads, comments). It struggles with
    non-article pages, so if it returns too little we fall back to stripping known noise tags
    from the full document.
    """
    try:
        article_html = ReadabilityDoc(html).summary(html_partial=True)
        text = _html_to_text(article_html)
        if len(text) >= READABILITY_MIN_CHARS:
            return text
    except Exception:  # readability raises a variety of parser errors on malformed HTML
        logger.debug("Readability failed, falling back to full-page extraction", exc_info=True)
    return _html_to_text(html)


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(_NOISE_TAGS):
        tag.decompose()

    # Use leaf block elements as paragraphs so the chunker can split on natural boundaries.
    paragraphs = []
    for el in soup.find_all(_BLOCK_TAGS):
        if el.find(_BLOCK_TAGS):
            continue
        text = " ".join(el.get_text(" ").split())
        if text:
            paragraphs.append(text)
    joined = "\n\n".join(paragraphs)

    flat = " ".join(soup.get_text(" ").split())
    # If most of the text lives outside block tags (e.g. plain <div>s), prefer the flat text.
    return joined if len(joined) >= 0.5 * len(flat) else flat
