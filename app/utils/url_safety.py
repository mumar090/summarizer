import ipaddress
import socket
from urllib.parse import urlsplit

from app.core.errors import SummarizationError, TransientError, UnsafeURLError


def ensure_public_url(url: str) -> None:
    """Reject URLs that resolve to non-public addresses (SSRF protection).

    The service fetches arbitrary user-supplied URLs from inside our network, so without this
    check a caller could make it hit internal services (Redis, Ollama, cloud metadata endpoints).
    Every redirect hop is re-checked by the fetcher. Note: this does not defend against DNS
    rebinding between the check and the request; an egress proxy would be the full fix.
    """
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise UnsafeURLError("Only http and https URLs are supported")
    host = parts.hostname
    if not host:
        raise SummarizationError("URL has no host")

    try:
        infos = socket.getaddrinfo(host, parts.port or None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        if exc.errno in (socket.EAI_AGAIN,):
            raise TransientError(f"DNS lookup for {host} failed temporarily") from exc
        raise SummarizationError(f"Could not resolve host {host}") from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise UnsafeURLError(f"URL resolves to a non-public address ({host})")
