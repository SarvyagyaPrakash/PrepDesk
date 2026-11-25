from pathlib import Path

import numpy as np
import pytest

import jobs
import matcher
from skills import find_skills


@pytest.fixture
def temp_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Provide isolated data/ and SQLite paths for matcher tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_file = tmp_path / "test_prepdesk.db"
    monkeypatch.setenv("PREPDESK_DATA_DIR", str(data_dir))
    monkeypatch.setenv("PREPDESK_DB", str(db_file))
    matcher._RESUME_CACHE.clear()
    return data_dir, db_file


def test_find_skills_edge_cases() -> None:
    text = (
        "Built microservices with C++, C#, Node.js, and deployed to k8s using CI/CD. "
        "Plain words: nodes, json, digital, go to the store, R&D, section C."
    )
    found = find_skills(text)
    assert {"c++", "c#", "node.js", "kubernetes", "ci/cd", "microservices"} <= found
    assert "javascript" not in found
    assert "git" not in found
    assert "golang" not in found


def test_match_resume_missing_skills_redaction_and_application_append(
    temp_env: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir, _ = temp_env
    resume_file = data_dir / "resume.txt"
    resume_file.write_text(
        "\n".join(
            [
                "Contact: alex.student@university.edu | +1 (555) 234-5678",
                "- Built REST APIs with Python, FastAPI, and PostgreSQL for student portal (alex.student@university.edu, 555-234-5678).",
                "- Deployed containerized services with Docker and GitHub Actions.",
            ]
        ),
        encoding="utf-8",
    )

    def fake_embed_passages(texts: list[str]) -> np.ndarray:
        return np.tile(np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32), (len(texts), 1))

    def fake_embed_query(text: str) -> np.ndarray:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)

    monkeypatch.setattr(matcher.embeddings, "embed_passages", fake_embed_passages)
    monkeypatch.setattr(matcher.embeddings, "embed_query", fake_embed_query)

    app = jobs.add_application(company="Acme", role="Backend Intern", notes="Applied via referral")
    jd = """
    Requirements:
    - Strong experience with Python, PostgreSQL, Docker, and Kubernetes.
    - Proficiency in GraphQL and Terraform is required.
    """

    result = matcher.match_resume(
        job_description=jd,
        resume_path="data/resume.txt",
        application_id=app["id"],
    )

    assert result["skills"]["found_in_resume"] == ["docker", "postgresql", "python"]
    assert result["skills"]["missing"] == ["graphql", "kubernetes", "terraform"]
    assert "rough heuristic" in result["note"].lower()
    assert len(result["matched_requirements"]) > 0

    evidence_blob = " ".join(
        item["resume_evidence"] for item in result["matched_requirements"]
    )
    assert "alex.student@university.edu" not in evidence_blob
    assert "555-234-5678" not in evidence_blob
    assert "[REDACTED_EMAIL]" in evidence_blob
    assert "[REDACTED_PHONE]" in evidence_blob

    updated_app = jobs.get_application(app["id"])
    lines = updated_app["notes"].splitlines()
    assert lines[0] == "Applied via referral"
    assert lines[1].startswith("Resume match ")
    assert "missing: graphql, kubernetes, terraform" in lines[1]


@pytest.mark.parametrize("bad_path", ["../..", "/etc/passwd", "data/../secret.txt"])
def test_read_resume_rejects_path_escape(temp_env: tuple[Path, Path], bad_path: str) -> None:
    with pytest.raises(ValueError, match="outside the allowed data/ directory"):
        matcher.read_resume(bad_path)


def test_read_resume_missing_file_raises_value_error(temp_env: tuple[Path, Path]) -> None:
    with pytest.raises(ValueError, match="Resume file not found"):
        matcher.read_resume("data/nonexistent.pdf")


def test_match_resume_bad_application_id_raises_value_error(temp_env: tuple[Path, Path]) -> None:
    data_dir, _ = temp_env
    (data_dir / "resume.txt").write_text(
        "- Built backend services in Python and PostgreSQL for web apps.",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="9999"):
        matcher.match_resume(
            job_description="- Experience with Python.",
            resume_path="data/resume.txt",
            application_id=9999,
        )


def test_match_resume_default_resume_fallback(
    temp_env: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir, _ = temp_env

    # Neither data/resume.pdf nor data/resume.txt exists
    with pytest.raises(ValueError, match=r"data/resume\.pdf.*data/resume\.txt"):
        matcher.match_resume(job_description="- Experience with Python.")

    # Falls back to data/resume.txt when data/resume.pdf is absent
    (data_dir / "resume.txt").write_text(
        "- Built backend REST APIs in Python and SQL for student services.",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        matcher.embeddings,
        "embed_passages",
        lambda texts: np.tile(np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32), (len(texts), 1)),
    )
    monkeypatch.setattr(
        matcher.embeddings,
        "embed_query",
        lambda text: np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
    )

    result = matcher.match_resume(job_description="- Experience with Python and SQL.")
    assert result["skills"]["found_in_resume"] == ["python", "sql"]


@pytest.mark.slow
def test_match_resume_integration_database_vs_cooking_jd(temp_env: tuple[Path, Path]) -> None:
    data_dir, _ = temp_env
    (data_dir / "resume.txt").write_text(
        "\n".join(
            [
                "- Designed PostgreSQL schemas, B-tree indexes, and query optimization plans.",
                "- Built Python ETL pipelines migrating SQL databases and Redis caches.",
                "- Tuned ACID transactions and connection pooling for high-throughput services.",
            ]
        ),
        encoding="utf-8",
    )

    db_jd = """
    Requirements:
    - Strong experience with PostgreSQL, SQL query optimization, and database indexing.
    - Ability to build Python data pipelines and manage Redis caching.
    """
    cooking_jd = """
    Requirements:
    - Strong experience baking sourdough bread, pastry lamination, and sauce preparation.
    - Ability to manage commercial kitchen prep stations and menu plating.
    """

    db_result = matcher.match_resume(db_jd, resume_path="data/resume.txt")
    cooking_result = matcher.match_resume(cooking_jd, resume_path="data/resume.txt")

    assert db_result["overall_match_percent"] > cooking_result["overall_match_percent"]
