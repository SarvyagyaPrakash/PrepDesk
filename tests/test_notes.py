from pathlib import Path

import numpy as np
import pytest

import notes


@pytest.fixture
def temp_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Provide isolated data/ and SQLite paths for notes tests."""
    data_dir = tmp_path / "data"
    notes_dir = data_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    db_file = tmp_path / "test_prepdesk.db"
    monkeypatch.setenv("PREPDESK_DATA_DIR", str(data_dir))
    monkeypatch.setenv("PREPDESK_DB", str(db_file))
    return notes_dir, db_file


def test_chunk_text_sizes_and_overlap() -> None:
    paragraphs = [
        f"Paragraph {i}. " + ("word " * 40).strip()
        for i in range(10)
    ]
    text = "\n\n".join(paragraphs)

    chunks = notes.chunk_text(text, size=500, overlap=100)
    assert len(chunks) > 2
    assert all(0 < len(c) <= 500 for c in chunks)

    # Consecutive chunks should share overlapping content from the boundary
    for prev, curr in zip(chunks, chunks[1:]):
        tail = prev[-40:]
        assert tail in curr or any(word in curr for word in tail.split())


@pytest.mark.parametrize("bad_folder", ["../..", "/etc", "data/../outside", "/tmp"])
def test_index_notes_rejects_path_escape(temp_env: tuple[Path, Path], bad_folder: str) -> None:
    with pytest.raises(ValueError, match="outside the allowed data/ directory"):
        notes.index_notes(bad_folder)


def test_index_notes_skips_unchanged_and_reindexes_modified(
    temp_env: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir, _ = temp_env
    file_a = notes_dir / "os.txt"
    file_a.write_text("Virtual memory uses page tables and TLB caching.", encoding="utf-8")

    def fake_embed_passages(texts: list[str]) -> np.ndarray:
        return np.ones((len(texts), 4), dtype=np.float32) * 0.5

    monkeypatch.setattr(notes.embeddings, "embed_passages", fake_embed_passages)

    first = notes.index_notes("data/notes")
    assert first == {
        "files_indexed": 1,
        "files_unchanged": 0,
        "chunks_added": 1,
        "skipped_no_text": [],
    }

    second = notes.index_notes("data/notes")
    assert second == {
        "files_indexed": 0,
        "files_unchanged": 1,
        "chunks_added": 0,
        "skipped_no_text": [],
    }

    # Modify the file and confirm it re-indexes
    file_a.write_text("Updated: page faults trigger OS trap handlers.", encoding="utf-8")
    third = notes.index_notes("data/notes")
    assert third == {
        "files_indexed": 1,
        "files_unchanged": 0,
        "chunks_added": 1,
        "skipped_no_text": [],
    }


@pytest.mark.slow
def test_search_notes_integration_with_real_model(temp_env: tuple[Path, Path]) -> None:
    notes_dir, _ = temp_env
    (notes_dir / "databases.txt").write_text(
        "B-trees, ACID transactions, SQL indexing, and query optimization in relational databases.",
        encoding="utf-8",
    )
    (notes_dir / "cooking.txt").write_text(
        "Simmer pasta sauce with tomatoes, garlic, olive oil, and fresh basil leaves.",
        encoding="utf-8",
    )

    stats = notes.index_notes("data/notes")
    assert stats["files_indexed"] == 2
    assert stats["chunks_added"] == 2

    results = notes.search_notes("How do SQL indexes and ACID transactions work?", top_k=2)
    assert len(results) == 2
    assert results[0]["source"] == "notes/databases.txt"
    assert results[0]["page"] is None
    assert results[0]["score"] > results[1]["score"]
    assert len(results[0]["text"]) <= 800
