from datetime import date, timedelta
from pathlib import Path

import pytest

import deadlines


@pytest.fixture
def temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point PREPDESK_DB at a fresh temporary SQLite file for each test."""
    db_file = tmp_path / "data" / "test_prepdesk.db"
    monkeypatch.setenv("PREPDESK_DB", str(db_file))
    return db_file


def test_add_deadline_valid(temp_db: Path) -> None:
    created = deadlines.add_deadline(
        title="OS Assignment 3",
        due_date="2026-12-05",
        course="CS301",
    )

    assert temp_db.exists()
    assert isinstance(created, dict)
    assert created["id"] == 1
    assert created["title"] == "OS Assignment 3"
    assert created["course"] == "CS301"
    assert created["due_date"] == "2026-12-05"
    assert created["created_at"]

    no_course = deadlines.add_deadline(title="Resume Review", due_date="2026-12-10")
    assert no_course["course"] == ""


@pytest.mark.parametrize(
    "bad_date",
    [
        "25-11-2026",
        "2026/11/25",
        "next friday",
        "2026-02-30",
        "2026-13-01",
        "",
    ],
)
def test_add_deadline_invalid_date_raises_value_error(temp_db: Path, bad_date: str) -> None:
    with pytest.raises(ValueError, match=r"YYYY-MM-DD.*example"):
        deadlines.add_deadline(title="Invalid", due_date=bad_date)


def test_list_deadlines_upcoming_window_overdue_and_sorting(temp_db: Path) -> None:
    today = date.today()
    past_3 = (today - timedelta(days=3)).isoformat()
    past_1 = (today - timedelta(days=1)).isoformat()
    today_str = today.isoformat()
    in_5_days = (today + timedelta(days=5)).isoformat()
    in_14_days = (today + timedelta(days=14)).isoformat()
    in_20_days = (today + timedelta(days=20)).isoformat()

    # Insert out of chronological order to verify sorting
    deadlines.add_deadline(title="Far Future", due_date=in_20_days, course="CS400")
    deadlines.add_deadline(title="Edge Upcoming", due_date=in_14_days, course="CS302")
    deadlines.add_deadline(title="Due Today", due_date=today_str, course="CS101")
    deadlines.add_deadline(title="Older Overdue", due_date=past_3, course="CS201")
    deadlines.add_deadline(title="Soon Upcoming", due_date=in_5_days, course="CS202")
    deadlines.add_deadline(title="Recent Overdue", due_date=past_1, course="CS201")

    items = deadlines.list_deadlines(days_ahead=14)
    titles = [item["title"] for item in items]

    assert titles == [
        "Older Overdue",
        "Recent Overdue",
        "Due Today",
        "Soon Upcoming",
        "Edge Upcoming",
    ]
    assert "Far Future" not in titles

    by_title = {item["title"]: item for item in items}
    assert by_title["Older Overdue"]["days_left"] == -3
    assert by_title["Older Overdue"]["status"] == "overdue"
    assert by_title["Recent Overdue"]["days_left"] == -1
    assert by_title["Recent Overdue"]["status"] == "overdue"
    assert by_title["Due Today"]["days_left"] == 0
    assert by_title["Due Today"]["status"] == "today"
    assert by_title["Soon Upcoming"]["days_left"] == 5
    assert by_title["Soon Upcoming"]["status"] == "upcoming"
    assert by_title["Edge Upcoming"]["days_left"] == 14
    assert by_title["Edge Upcoming"]["status"] == "upcoming"


def test_get_today() -> None:
    result = deadlines.get_today()
    expected = date.today()
    assert result["date"] == expected.isoformat()
    assert result["weekday"] == expected.strftime("%A")
