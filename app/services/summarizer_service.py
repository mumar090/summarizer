import logging
import re
from collections.abc import Callable

from app.core.config import settings
from app.core.errors import SummarizationError
from app.db.models import StatusEnum
from app.utils.chunking import chunk_text
from app.utils.llm_client import LLMClient, get_llm_client
from app.utils.text_extraction import extract_main_text, fetch_url

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[StatusEnum, float], None]

SYSTEM_PROMPT = (
    "You are a precise summarizer. Summarize the text you are given in neutral, factual prose. "
    "Use complete sentences. Only use information that is in the text. "
    "Do not add a preamble such as 'Here is a summary'."
)
MAX_REDUCE_DEPTH = 3

_PREAMBLE_RE = re.compile(r"^\s*(here('s| is)[^\n:]*|summary)\s*:\s*", re.IGNORECASE)
_SENTENCE_END_RE = re.compile(r"[.!?][\"')\]]?(?=\s|$)")


def _noop(status: StatusEnum, progress: float) -> None:
    pass


class Summarizer:
    """Map-reduce summarization for texts longer than the model's comfortable context."""

    def __init__(
        self,
        llm: LLMClient,
        *,
        char_limit: int = settings.SUMMARY_CHAR_LIMIT,
        chunk_size: int = settings.MAX_CHARS_PER_CHUNK,
        overlap: int = settings.CHUNK_OVERLAP_CHARS,
        max_input_chars: int = settings.MAX_INPUT_CHARS,
    ):
        self.llm = llm
        self.char_limit = char_limit
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.max_input_chars = max_input_chars

    def summarize_text(self, text: str, on_progress: ProgressCallback = _noop) -> str:
        if len(text) > self.max_input_chars:
            # Bound cost/latency for huge pages; the start of a page usually carries the gist.
            logger.info("Truncating input from %d to %d chars", len(text), self.max_input_chars)
            text = text[: self.max_input_chars]

        chunks = chunk_text(text, self.chunk_size, self.overlap)
        if not chunks:
            raise SummarizationError("No text to summarize")

        if len(chunks) == 1:
            on_progress(StatusEnum.SUMMARIZING, 0.5)
            summary = self._summarize(chunks[0], self.char_limit)
        else:
            # Map: summarize each chunk to half the final budget so the reduce step has room.
            partials = []
            for i, chunk in enumerate(chunks, start=1):
                partials.append(self._summarize(chunk, self.char_limit // 2, excerpt=True))
                on_progress(StatusEnum.SUMMARIZING, 0.3 + 0.6 * i / len(chunks))
            summary = self._reduce(partials)

        return trim_summary(summary, self.char_limit)

    def _reduce(self, partials: list[str], depth: int = 0) -> str:
        combined = "\n\n".join(partials)
        if len(combined) <= self.chunk_size or depth >= MAX_REDUCE_DEPTH:
            return self._summarize(combined[: self.chunk_size], self.char_limit, combine=True)
        # Too many partial summaries to fit in one prompt: reduce them in groups first.
        groups = chunk_text(combined, self.chunk_size)
        return self._reduce(
            [self._summarize(g, self.char_limit // 2, combine=True) for g in groups], depth + 1
        )

    def _summarize(self, text: str, char_limit: int, *, excerpt=False, combine=False) -> str:
        if combine:
            task = (
                "These are summaries of consecutive sections of one web page. "
                "Merge them into one coherent summary of the whole page"
            )
        elif excerpt:
            task = "This is one section of a longer web page. Summarize this section"
        else:
            task = "Summarize this web page"
        prompt = f"{task} in at most {char_limit} characters.\n\n<text>\n{text}\n</text>"
        # ~3 chars per token, plus headroom so the model can finish its last sentence.
        return self.llm.generate(prompt, system=SYSTEM_PROMPT, max_tokens=char_limit // 3 + 64)


def trim_summary(text: str, limit: int) -> str:
    """Strip chatty preambles and cut to `limit` chars on a sentence boundary where possible."""
    text = _PREAMBLE_RE.sub("", text, count=1).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    ends = [m.end() for m in _SENTENCE_END_RE.finditer(cut)]
    if ends and ends[-1] >= limit // 2:
        return cut[: ends[-1]]
    space = cut.rfind(" ", 0, limit - 1)
    return (cut[:space] if space > 0 else cut[: limit - 1]).rstrip(",;: ") + "…"


def get_summarizer() -> Summarizer:
    return Summarizer(get_llm_client())


def summarize_url(
    url: str,
    on_progress: ProgressCallback = _noop,
    summarizer: Summarizer | None = None,
) -> str:
    on_progress(StatusEnum.FETCHING, 0.05)
    html = fetch_url(url)

    on_progress(StatusEnum.EXTRACTING, 0.2)
    text = extract_main_text(html)
    if len(text) < settings.MIN_CONTENT_CHARS:
        raise SummarizationError(
            "Not enough readable text on the page to summarize " "(it may require JavaScript or a login)"
        )

    on_progress(StatusEnum.SUMMARIZING, 0.3)
    return (summarizer or get_summarizer()).summarize_text(text, on_progress)
