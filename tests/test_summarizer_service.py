import pytest

from app.core.errors import SummarizationError
from app.db.models import StatusEnum
from app.services import summarizer_service
from app.services.summarizer_service import Summarizer, summarize_url, trim_summary


def test_short_text_uses_single_call(fake_llm):
    s = Summarizer(fake_llm, char_limit=200, chunk_size=1000, overlap=0)
    assert s.summarize_text("Some article text. " * 10) == "A short factual summary."
    assert len(fake_llm.prompts) == 1
    assert "at most 200 characters" in fake_llm.prompts[0]


def test_long_text_is_map_reduced(fake_llm):
    s = Summarizer(fake_llm, char_limit=200, chunk_size=500, overlap=0)
    progress = []
    s.summarize_text("Sentence about things. " * 100, lambda st, p: progress.append((st, p)))
    # 2300 chars / 500 per chunk -> 5 map calls + 1 reduce call
    assert len(fake_llm.prompts) == 6
    assert "Merge them" in fake_llm.prompts[-1]
    assert [p for _, p in progress] == sorted(p for _, p in progress)
    assert all(st == StatusEnum.SUMMARIZING for st, _ in progress)


def test_reduce_recurses_when_partials_do_not_fit(fake_llm):
    fake_llm.reply = "x " * 200  # 400-char partial summaries
    s = Summarizer(fake_llm, char_limit=300, chunk_size=500, overlap=0)
    s.summarize_text("Sentence about things. " * 200)
    merge_prompts = [p for p in fake_llm.prompts if "Merge them" in p]
    assert len(merge_prompts) > 1


def test_input_is_capped(fake_llm):
    s = Summarizer(fake_llm, char_limit=200, chunk_size=1000, overlap=0, max_input_chars=1000)
    s.summarize_text("a " * 50_000)
    assert len(fake_llm.prompts) == 1


def test_trim_removes_preamble():
    assert trim_summary("Here is a summary of the page: The cat sat.", 100) == "The cat sat."


def test_trim_cuts_on_sentence_boundary():
    text = "First sentence is here. Second sentence is here. Third one is long."
    assert trim_summary(text, 50) == "First sentence is here. Second sentence is here."


def test_trim_falls_back_to_word_boundary():
    out = trim_summary("word " * 100, 50)
    assert len(out) <= 50
    assert out.endswith("…")


def test_summarize_url_reports_stages(monkeypatch, fake_llm):
    monkeypatch.setattr(summarizer_service, "fetch_url", lambda url: "<html/>")
    monkeypatch.setattr(summarizer_service, "extract_main_text", lambda html: "Real content. " * 20)
    stages = []
    out = summarize_url(
        "https://example.com",
        on_progress=lambda st, p: stages.append(st),
        summarizer=Summarizer(fake_llm, chunk_size=1000, overlap=0),
    )
    assert out == "A short factual summary."
    assert stages[:3] == [StatusEnum.FETCHING, StatusEnum.EXTRACTING, StatusEnum.SUMMARIZING]


def test_summarize_url_rejects_empty_pages(monkeypatch, fake_llm):
    monkeypatch.setattr(summarizer_service, "fetch_url", lambda url: "<html/>")
    monkeypatch.setattr(summarizer_service, "extract_main_text", lambda html: "Loading...")
    with pytest.raises(SummarizationError, match="Not enough readable text"):
        summarize_url("https://example.com", summarizer=Summarizer(fake_llm))
    assert fake_llm.prompts == []
