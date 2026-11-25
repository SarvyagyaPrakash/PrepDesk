from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

import briefing
import db
import deadlines
import jobs
import server


@pytest.fixture
def temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point PREPDESK_DB at a fresh temporary SQLite file for each test."""
    db_file = tmp_path / "data" / "test_prepdesk.db"
    monkeypatch.setenv("PREPDESK_DB", str(db_file))
    return db_file


def test_weekly_briefing_returns_overdue_due_soon_and_followups(temp_db: Path) -> None:
    today = date.today()
    past_date = (today - timedelta(days=2)).isoformat()
    soon_date = (today + timedelta(days=3)).isoformat()
    later_date = (today + timedelta(days=12)).isoformat()

    deadlines.add_deadline(title="Overdue Lab", due_date=past_date, course="CS201")
    deadlines.add_deadline(title="Soon Quiz", due_date=soon_date, course="CS301")
    deadlines.add_deadline(title="Later Exam", due_date=later_date, course="CS401")

    stale_app = jobs.add_application(company="Acme", role="SWE Intern", status="applied")
    jobs.add_application(company="Beta", role="ML Intern", status="applied")

    old_ts = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    conn = db.get_connection()
    try:
        conn.execute(
            "UPDATE applications SET updated_at = ? WHERE id = ?",
            (old_ts, stale_app["id"]),
        )
        conn.commit()
    finally:
        conn.close()

    result = briefing.weekly_briefing(days=7)

    assert result["today"]["date"] == today.isoformat()
    assert [d["title"] for d in result["overdue_deadlines"]] == ["Overdue Lab"]
    assert [d["title"] for d in result["due_soon_deadlines"]] == ["Soon Quiz"]
    assert [a["company"] for a in result["followups_due"]] == ["Acme"]
    assert result["counts"] == {
        "overdue_deadlines": 1,
        "due_soon_deadlines": 1,
        "followups_due": 1,
    }


def test_upcoming_deadlines_resource_format(temp_db: Path) -> None:
    today = date.today()
    due_6 = (today + timedelta(days=6)).isoformat()
    overdue_2 = (today - timedelta(days=2)).isoformat()

    deadlines.add_deadline(title="DBMS exam", due_date=due_6, course="DBMS")
    deadlines.add_deadline(title="OS lab", due_date=overdue_2, course="OS")

    text = briefing.format_upcoming_deadlines(days_ahead=14)
    lines = text.splitlines()

    assert f"{overdue_2} | OS lab | OS | 2 days overdue" in lines
    assert f"{due_6} | DBMS exam | DBMS | in 6 days" in lines


def test_prompts_return_non_empty_text_with_tool_names() -> None:
    quiz_text = server.quiz_me(topic="B-trees", num_questions=4)
    assert quiz_text.strip()
    assert "search_notes" in quiz_text
    assert "B-trees" in quiz_text
    assert "4" in quiz_text

    plan_text = server.weekly_plan()
    assert plan_text.strip()
    assert "weekly_briefing" in plan_text
