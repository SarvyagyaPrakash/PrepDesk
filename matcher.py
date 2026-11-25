import hashlib
import logging
import re
from pathlib import Path
from typing import Any

import numpy as np
from pypdf import PdfReader

import embeddings
import jobs
from paths import safe_data_path
from skills import find_skills

logger = logging.getLogger("prepdesk.matcher")

MATCH_THRESHOLD = 0.60

_RESUME_CACHE: dict[str, tuple[str, list[str], np.ndarray]] = {}

_BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*•·▪]|\d+[.)])\s+")
_CUE_WORDS_RE = re.compile(
    r"\b(?:experience|proficient|knowledge|familiar|ability|strong|required|skills|degree|build|develop)\b",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\w)"
)


def _redact_pii(text: str) -> str:
    """Redact email addresses and phone numbers from resume text."""
    redacted = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    redacted = _PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    return redacted


def _read_resume_file(resolved_path: Path) -> str:
    """Extract text from a resolved .pdf or .txt resume file."""
    if not resolved_path.exists() or not resolved_path.is_file():
        raise ValueError(f"Resume file not found: '{resolved_path}'.")

    suffix = resolved_path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(resolved_path))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
        text = "\n".join(p for p in pages if p).strip()
    elif suffix == ".txt":
        text = resolved_path.read_text(encoding="utf-8", errors="replace").strip()
    else:
        raise ValueError(
            f"Unsupported resume format '{suffix}'. Only .pdf and .txt files are supported."
        )

    if not text:
        raise ValueError(
            f"No extractable text found in '{resolved_path}'; it may be a scanned image."
        )
    return text


def read_resume(path: str = "data/resume.pdf") -> str:
    """Read and extract text from a resume (.pdf or .txt) inside the data/ directory."""
    resolved = safe_data_path(path)
    return _read_resume_file(resolved)


def _split_resume_units(text: str) -> list[str]:
    """Split resume text into short units (bullets or lines of 20-300 characters)."""
    units: list[str] = []
    for raw_line in text.splitlines():
        line = _BULLET_PREFIX_RE.sub("", raw_line).strip()
        if len(line) < 20:
            continue
        if len(line) <= 300:
            units.append(line)
            continue

        # Split long lines into <= 300 char pieces on whitespace
        start = 0
        while start < len(line):
            if start + 300 >= len(line):
                tail = line[start:].strip()
                if len(tail) >= 20:
                    units.append(tail)
                break
            cut = line.rfind(" ", start + 100, start + 300)
            if cut == -1:
                cut = start + 300
            piece = line[start:cut].strip()
            if len(piece) >= 20:
                units.append(piece)
            start = cut + 1
    return units


def _extract_jd_lines(job_description: str) -> list[str]:
    """Extract up to 40 requirement lines (bullets + sentences with cue words) from a JD."""
    lines: list[str] = []
    seen: set[str] = set()

    def _add(candidate: str) -> None:
        cleaned = " ".join(candidate.split()).strip()
        if len(cleaned) < 15:
            return
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            lines.append(cleaned)

    for raw_line in job_description.splitlines():
        if _BULLET_PREFIX_RE.match(raw_line):
            _add(_BULLET_PREFIX_RE.sub("", raw_line))

    for sentence in re.split(r"[.!?\n]+", job_description):
        stripped = _BULLET_PREFIX_RE.sub("", sentence).strip()
        if stripped and _CUE_WORDS_RE.search(stripped):
            _add(stripped)

    return lines[:40]


def _get_cached_resume(resume_path: str) -> tuple[str, list[str], np.ndarray]:
    """Load, parse, and embed the resume, caching in memory by file sha256."""
    resolved = safe_data_path(resume_path)
    if not resolved.exists() or not resolved.is_file():
        raise ValueError(f"Resume file not found: '{resolved}'.")

    file_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()
    cached = _RESUME_CACHE.get(file_hash)
    if cached is not None:
        logger.debug("Using cached resume embeddings for sha256=%s", file_hash[:12])
        return cached

    resume_text = _read_resume_file(resolved)
    units = _split_resume_units(resume_text)
    if units:
        unit_vecs = embeddings.embed_passages(units)
    else:
        unit_vecs = np.empty((0, 0), dtype=np.float32)

    _RESUME_CACHE[file_hash] = (resume_text, units, unit_vecs)
    return resume_text, units, unit_vecs


def match_resume(
    job_description: str,
    resume_path: str = "data/resume.pdf",
    application_id: int | None = None,
) -> dict[str, Any]:
    """Compare a resume against a job description by skill overlap and embedding similarity."""
    existing_app: dict[str, Any] | None = None
    if application_id is not None:
        existing_app = jobs.get_application(application_id)

    resume_text, resume_units, resume_vecs = _get_cached_resume(resume_path)

    jd_skills = sorted(find_skills(job_description))
    resume_skills = find_skills(resume_text)
    found_skills = [s for s in jd_skills if s in resume_skills]
    missing_skills = [s for s in jd_skills if s not in resume_skills]

    jd_lines = _extract_jd_lines(job_description)
    matched_requirements: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    if jd_lines and resume_units and resume_vecs.size > 0:
        jd_vecs = np.vstack([embeddings.embed_query(line) for line in jd_lines])
        sim_matrix = jd_vecs @ resume_vecs.T

        for i, line in enumerate(jd_lines):
            sims = sim_matrix[i]
            best_idx = int(np.argmax(sims))
            best_sim = float(sims[best_idx])
            if best_sim >= MATCH_THRESHOLD:
                matched_requirements.append(
                    {
                        "jd_line": line,
                        "resume_evidence": _redact_pii(resume_units[best_idx]),
                        "similarity": round(best_sim, 3),
                    }
                )
            else:
                gaps.append(
                    {
                        "jd_line": line,
                        "best_similarity": round(best_sim, 3),
                    }
                )
    else:
        for line in jd_lines:
            gaps.append({"jd_line": line, "best_similarity": 0.0})

    skills_cov = (len(found_skills) / len(jd_skills) * 100.0) if jd_skills else None
    req_cov = (len(matched_requirements) / len(jd_lines) * 100.0) if jd_lines else None

    if skills_cov is not None and req_cov is not None:
        overall = 0.6 * skills_cov + 0.4 * req_cov
    elif skills_cov is not None:
        overall = skills_cov
    elif req_cov is not None:
        overall = req_cov
    else:
        overall = 0.0

    overall_percent = round(overall, 1)

    matched_requirements.sort(key=lambda item: item["similarity"], reverse=True)
    gaps.sort(key=lambda item: item["best_similarity"])

    if application_id is not None and existing_app is not None:
        missing_summary = ", ".join(missing_skills) if missing_skills else "none"
        note_line = f"Resume match {int(round(overall))}% - missing: {missing_summary}"
        prev_notes = (existing_app.get("notes") or "").strip()
        new_notes = f"{prev_notes}\n{note_line}" if prev_notes else note_line
        jobs.update_application(id=application_id, notes=new_notes)

    return {
        "overall_match_percent": overall_percent,
        "skills": {
            "in_job_description": jd_skills,
            "found_in_resume": found_skills,
            "missing": missing_skills,
        },
        "matched_requirements": matched_requirements[:8],
        "gaps": gaps[:8],
        "note": (
            "Rough heuristic combining keyword skill coverage and embedding similarity; "
            "use as directional guidance rather than an exact score."
        ),
    }
