import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from pypdf import PdfReader

import embeddings
from db import get_connection

logger = logging.getLogger("prepdesk.notes")

_BASE_DIR = Path(__file__).resolve().parent
_SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt"}
_SENTENCE_BREAKS = ("\n\n", "\n", ". ", "! ", "? ", " ")


def _get_data_dir() -> Path:
    """Resolve the allowed data/ directory, overridable via PREPDESK_DATA_DIR for tests."""
    env_dir = os.environ.get("PREPDESK_DATA_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    return (_BASE_DIR / "data").resolve()


def _resolve_folder(folder: str) -> tuple[Path, Path]:
    """Resolve folder and verify it lies inside the project's data/ directory."""
    data_dir = _get_data_dir()
    folder_path = Path(folder)
    if folder_path.is_absolute():
        resolved = folder_path.resolve()
    else:
        project_root = data_dir.parent if data_dir.name == "data" else _BASE_DIR
        resolved = (project_root / folder_path).resolve()

    if not resolved.is_relative_to(data_dir):
        raise ValueError(
            f"Access denied: '{folder}' resolves outside the allowed data/ directory."
        )
    if not resolved.exists() or not resolved.is_dir():
        raise ValueError(f"Notes folder does not exist: '{resolved}'.")
    return resolved, data_dir


def chunk_text(text: str, size: int = 800, overlap: int = 150) -> list[str]:
    """Split text into overlapping chunks, preferring paragraph or sentence boundaries."""
    if size <= 0:
        raise ValueError("chunk size must be positive.")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and < size.")

    cleaned = text.strip()
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    length = len(cleaned)
    min_split = max(overlap + 1, size // 2)

    while start < length:
        if start + size >= length:
            tail = cleaned[start:].strip()
            if tail:
                chunks.append(tail)
            break

        window_end = start + size
        split_at = window_end
        for sep in _SENTENCE_BREAKS:
            idx = cleaned.rfind(sep, start + min_split, window_end)
            if idx != -1:
                split_at = idx + len(sep)
                break

        chunk = cleaned[start:split_at].strip()
        if chunk:
            chunks.append(chunk)

        next_start = split_at - overlap
        start = next_start if next_start > start else split_at

    return chunks


def _extract_file_chunks(file_path: Path) -> list[tuple[int | None, int, str]]:
    """Extract (page, chunk_index, chunk_text) tuples from a supported file."""
    suffix = file_path.suffix.lower()
    extracted: list[tuple[int | None, int, str]] = []

    if suffix == ".pdf":
        reader = PdfReader(str(file_path))
        for page_num, page in enumerate(reader.pages, start=1):
            page_text = (page.extract_text() or "").strip()
            if not page_text:
                continue
            for idx, piece in enumerate(chunk_text(page_text)):
                extracted.append((page_num, idx, piece))
    else:
        raw_text = file_path.read_text(encoding="utf-8", errors="replace").strip()
        if raw_text:
            for idx, piece in enumerate(chunk_text(raw_text)):
                extracted.append((None, idx, piece))

    return extracted


def index_notes(folder: str = "data/notes") -> dict[str, Any]:
    """Index .pdf, .md, and .txt files inside data/, skipping unchanged files."""
    resolved_folder, data_dir = _resolve_folder(folder)
    files = sorted(
        p for p in resolved_folder.rglob("*")
        if p.is_file() and p.suffix.lower() in _SUPPORTED_EXTENSIONS
    )

    files_indexed = 0
    files_unchanged = 0
    chunks_added = 0
    skipped_no_text: list[str] = []

    conn = get_connection()
    try:
        for file_path in files:
            rel_source = str(file_path.relative_to(data_dir))
            file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()

            existing = conn.execute(
                "SELECT sha256 FROM indexed_files WHERE path = ?",
                (rel_source,),
            ).fetchone()
            if existing is not None and existing["sha256"] == file_hash:
                logger.info("Skipping unchanged file: %s", rel_source)
                files_unchanged += 1
                continue

            logger.info("Indexing file: %s", rel_source)
            file_chunks = _extract_file_chunks(file_path)
            if not file_chunks:
                logger.warning("No extractable text in file: %s", rel_source)
                skipped_no_text.append(rel_source)
                continue

            vectors = embeddings.embed_passages([item[2] for item in file_chunks])
            now = datetime.now(timezone.utc).isoformat()

            conn.execute("DELETE FROM chunks WHERE source = ?", (rel_source,))
            for (page_num, chunk_idx, text_piece), vec in zip(file_chunks, vectors):
                conn.execute(
                    """
                    INSERT INTO chunks (source, page, chunk_index, text, embedding)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        rel_source,
                        page_num,
                        chunk_idx,
                        text_piece,
                        vec.astype(np.float32).tobytes(),
                    ),
                )
            conn.execute(
                """
                INSERT OR REPLACE INTO indexed_files (path, sha256, indexed_at)
                VALUES (?, ?, ?)
                """,
                (rel_source, file_hash, now),
            )
            conn.commit()

            files_indexed += 1
            chunks_added += len(file_chunks)
    finally:
        conn.close()

    return {
        "files_indexed": files_indexed,
        "files_unchanged": files_unchanged,
        "chunks_added": chunks_added,
        "skipped_no_text": skipped_no_text,
    }


def search_notes(question: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Search indexed note chunks by cosine similarity and return the top_k matches."""
    if top_k <= 0:
        return []

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT source, page, text, embedding FROM chunks"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        raise ValueError("No notes are indexed yet. Run index_notes first.")

    query_vec = embeddings.embed_query(question)
    chunk_matrix = np.vstack(
        [np.frombuffer(row["embedding"], dtype=np.float32) for row in rows]
    )
    scores = chunk_matrix @ query_vec
    top_indices = np.argsort(scores)[::-1][:top_k]

    results: list[dict[str, Any]] = []
    for idx in top_indices:
        row = rows[int(idx)]
        results.append(
            {
                "source": row["source"],
                "page": row["page"],
                "score": round(float(scores[int(idx)]), 3),
                "text": row["text"][:800],
            }
        )
    return results
