from app.utils.text_extraction import fetch_url, extract_main_text, FetchError
from app.utils.llm_client import ollama_client
from app.core.config import settings


MAX_CHUNK = settings.MAX_CHARS_PER_CHUNK
CHAR_LIMIT = settings.SUMMARY_CHAR_LIMIT


SYSTEM_PROMPT = (
"You are a concise technical summarizer. Read the provided text and return a neutral, factual summary of the entire page. "
"Keep it under the requested character limit and use complete sentences."
)

def _make_prompt(text: str, char_limit: int) -> str:
    return f"{SYSTEM_PROMPT}\n\nCONTENT:\n{text}\n\nSUMMARY (<= {char_limit} characters):"

def summarize_url(url: str) -> tuple[str, float]:
    # Returns (summary, progress)
    html = fetch_url(url)
    text = extract_main_text(html)
    if not text or len(text) < 50:
        raise ValueError("Extracted content is too short to summarize")


    # If short enough, single call
    if len(text) <= MAX_CHUNK:
        prompt = _make_prompt(text, CHAR_LIMIT)
        out = ollama_client.summarize(prompt, max_tokens=1024)
        summary = out[:CHAR_LIMIT]
        return summary, 1.0


    # Chunking: summarize each chunk then summarize result
    chunks = [text[i:i+MAX_CHUNK] for i in range(0, len(text), MAX_CHUNK)]
    partials = []
    for chunk in chunks:
        p = ollama_client.summarize(_make_prompt(chunk, CHAR_LIMIT//2), max_tokens=800)
        partials.append(p)
    combined = "\n\n".join(partials)
    final = ollama_client.summarize(_make_prompt(combined, CHAR_LIMIT), max_tokens=1024)
    return final[:CHAR_LIMIT], 1.0