from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import db
import jobs


@pytest.fixture
def temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point PREPDESK_DB at a fresh temporary SQLite file for each test."""
    db_file = tmp_path / "data" / "test_prepdesk.db"
    monkeypatch.setenv("PREPDESK_DB", str(db_file))
    return db_file


def test_add_application_defaults_and_custom_status(temp_db: Path) -> None:
    created = jobs.add_application(
        company="Acme Corp",
        role="Backend Intern",
        link="https://acme.example/jobs/1",
        notes="Referred by alumni",
    )

    assert temp_db.exists()
    assert isinstance(created, dict)
    assert created["id"] == 1
    assert created["company"] == "Acme Corp"
    assert created["role"] == "Backend Intern"
    assert created["status"] == "applied"
    assert created["link"] == "https://acme.example/jobs/1"
    assert created["notes"] == "Referred by alumni"
    assert created["created_at"] == created["updated_at"]

    wishlist = jobs.add_application(
        company="Beta Labs",
        role="ML Engineer",
        status="wishlist",
    )
    assert wishlist["id"] == 2
    assert wishlist["status"] == "wishlist"


def test_update_application_status_and_notes(temp_db: Path) -> None:
    created = jobs.add_application(
        company="Acme Corp",
        role="SWE",
        notes="Initial submission",
    )

    updated = jobs.update_application(
        id=created["id"],
        status="oa",
        notes="Received HackerRank invite",
    )
    assert updated["id"] == created["id"]
    assert updated["status"] == "oa"
    assert updated["notes"] == "Received HackerRank invite"
    assert updated["created_at"] == created["created_at"]
    assert updated["updated_at"] >= created["updated_at"]

    notes_only = jobs.update_application(id=created["id"], notes="Completed OA")
    assert notes_only["status"] == "oa"
    assert notes_only["notes"] == "Completed OA"


def test_invalid_status_raises_value_error(temp_db: Path) -> None:
    with pytest.raises(ValueError, match="Allowed values:.*wishlist.*applied.*oa.*interview.*offer.*rejected"):
        jobs.add_application(company="Acme", role="SWE", status="ghosted")

    created = jobs.add_application(company="Acme", role="SWE")
    with pytest.raises(ValueError, match="Allowed values:"):
        jobs.update_application(id=created["id"], status="archived")

    with pytest.raises(ValueError, match="Allowed values:"):
        jobs.list_applications(status="unknown")


def test_list_applications_filters_by_status(temp_db: Path) -> None:
    jobs.add_application(company="Co A", role="Role 1", status="wishlist")
    jobs.add_application(company="Co B", role="Role 2", status="applied")
    jobs.add_application(company="Co C", role="Role 3", status="oa")
    jobs.add_application(company="Co D", role="Role 4", status="applied")

    all_apps = jobs.list_applications()
    assert len(all_apps) == 4
    assert all(isinstance(app, dict) for app in all_apps)

    applied_apps = jobs.list_applications(status="applied")
    assert len(applied_apps) == 2
    assert {app["company"] for app in applied_apps} == {"Co B", "Co D"}

    oa_apps = jobs.list_applications(status="oa")
    assert len(oa_apps) == 1
    assert oa_apps[0]["company"] == "Co C"


def test_update_missing_id_raises_value_error(temp_db: Path) -> None:
    with pytest.raises(ValueError, match="9999"):
        jobs.update_application(id=9999, status="interview")


def test_followups_due_filters_by_age_and_active_status(temp_db: Path) -> None:
    stale_app = jobs.add_application(company="Stale Applied", role="SWE", status="applied")
    stale_oa = jobs.add_application(company="Stale OA", role="SWE", status="oa")
    stale_interview = jobs.add_application(company="Stale Interview", role="SWE", status="interview")
    stale_wishlist = jobs.add_application(company="Stale Wishlist", role="SWE", status="wishlist")
    stale_rejected = jobs.add_application(company="Stale Rejected", role="SWE", status="rejected")
    recent_app = jobs.add_application(company="Recent Applied", role="SWE", status="applied")

    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    conn = db.get_connection()
    try:
        conn.execute(
            "UPDATE applications SET updated_at = ? WHERE id IN (?, ?, ?, ?, ?)",
            (
                old_timestamp,
                stale_app["id"],
                stale_oa["id"],
                stale_interview["id"],
                stale_wishlist["id"],
                stale_rejected["id"],
            ),
        )
        conn.commit()
    finally:
        conn.close()

    due = jobs.followups_due(days_since_update=7)
    due_companies = {app["company"] for app in due}
    assert due_companies == {"Stale Applied", "Stale OA", "Stale Interview"}
    assert recent_app["company"] not in due_companies
    assert "Stale Wishlist" not in due_companies
    assert "Stale Rejected" not in due_companies
