import pytest

from app.utils.chunking import chunk_text


def test_short_text_is_single_chunk():
    assert chunk_text("  hello world  ", 100) == ["hello world"]


def test_empty_text_has_no_chunks():
    assert chunk_text("   ", 100) == []


def test_chunks_respect_max_size_and_cover_all_words():
    words = [f"word{i}" for i in range(2000)]
    text = " ".join(words)
    chunks = chunk_text(text, 500)
    assert all(len(c) <= 500 for c in chunks)
    assert " ".join(chunks).split() == words


def test_prefers_paragraph_boundaries():
    para = "Sentence one is here. " * 10
    text = f"{para.strip()}\n\n{para.strip()}\n\n{para.strip()}"
    chunks = chunk_text(text, len(para) + 10)
    assert all(c.endswith("here.") for c in chunks)


def test_overlap_repeats_context_on_word_boundary():
    text = " ".join(f"w{i}" for i in range(300))
    chunks = chunk_text(text, 200, overlap=40)
    for prev, nxt in zip(chunks, chunks[1:], strict=False):
        assert nxt.split()[0] in prev.split()  # starts with a whole word seen in the previous chunk


def test_unbreakable_text_is_hard_split():
    chunks = chunk_text("x" * 1050, 100)
    assert [len(c) for c in chunks] == [100] * 10 + [50]


@pytest.mark.parametrize("size, overlap", [(0, 0), (100, 50), (100, -1)])
def test_invalid_arguments(size, overlap):
    with pytest.raises(ValueError):
        chunk_text("text", size, overlap)
