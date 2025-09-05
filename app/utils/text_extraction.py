import requests
from readability import Document as ReadabilityDoc
from bs4 import BeautifulSoup


DEFAULT_HEADERS = {"User-Agent": "summarizer-bot/1.0"}


class FetchError(Exception):
    pass


def fetch_url(url: str, timeout: int = 20) -> str:
    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        raise FetchError(str(e))




def extract_main_text(html: str) -> str:
    try:
        doc = ReadabilityDoc(html)
        summary_html = doc.summary()
        soup = BeautifulSoup(summary_html, "lxml")
        text = soup.get_text(" ", strip=True)
        if len(text) > 200:
            return text
    except Exception:
        pass


    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    return text