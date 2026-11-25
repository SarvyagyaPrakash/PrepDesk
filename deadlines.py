import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

from db import get_connection

logger = logging.getLogger("prepdesk.deadlines")

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_due_date(due_date: str) -> date:
    """Validate that due_date is a real YYYY-MM-DD calendar date."""
    if not isinstance(due_date, str) or not _DATE_PATTERN.fullmatch(due_date):
        raise ValueError(
            f"Invalid due_date '{due_date}'. Expected format YYYY-MM-DD (for example, '2026-12-01')."
        )
    try:
        return date.fromisoformat(due_date)
    except ValueError as exc:
        raise ValueError(
            f"Invalid due_date '{due_date}': not a real calendar date. "
            "Expected format YYYY-MM-DD (for example, '2026-12-01')."
        ) from exc


def get_today() -> dict[str, str]:
    """Return today's local date as YYYY-MM-DD along with the weekday name."""
    today = date.today()
    return {
        "date": today.isoformat(),
        "weekday": today.strftime("%A"),
    }


def add_deadline(title: str, due_date: str, course: str = "") -> dict[str, Any]:
    """Insert a new deadline and return the created record as a dict."""
    _validate_due_date(due_date)
    created_at = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO deadlines (title, course, due_date, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (title, course, due_date, created_at),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, title, course, due_date, created_at FROM deadlines WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        logger.info("Added deadline id=%s title=%s due_date=%s", cursor.lastrowid, title, due_date)
        return dict(row)
    finally:
        conn.close()


def list_deadlines(days_ahead: int = 14) -> list[dict[str, Any]]:
    """Return overdue deadlines and upcoming deadlines within days_ahead, sorted by due_date."""
    today = date.today()
    cutoff = (today + timedelta(days=days_ahead)).isoformat()

    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, title, course, due_date
            FROM deadlines
            WHERE due_date <= ?
            ORDER BY due_date ASC, id ASC
            """,
            (cutoff,),
        ).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            due_dt = date.fromisoformat(row["due_date"])
            days_left = (due_dt - today).days
            if days_left < 0:
                status = "overdue"
            elif days_left == 0:
                status = "today"
            else:
                status = "upcoming"

            results.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "course": row["course"],
                    "due_date": row["due_date"],
                    "days_left": days_left,
                    "status": status,
                }
            )
        return results
    finally:
        conn.close()
