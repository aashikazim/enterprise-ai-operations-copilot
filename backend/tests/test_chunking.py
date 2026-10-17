import pytest

from app.services.chunking import chunk_text


def test_chunk_short_text():
    assert chunk_text("hello") == ["hello"]


def test_chunk_empty_text():
    assert chunk_text("   ") == []


def test_chunk_overlap():
    chunks = chunk_text(
        "abcdefghij",
        chunk_size=6,
        overlap=2,
    )

    assert chunks == ["abcdef", "efghij"]


def test_invalid_chunk_configuration():
    with pytest.raises(ValueError):
        chunk_text(
            "hello",
            chunk_size=5,
            overlap=5,
        )