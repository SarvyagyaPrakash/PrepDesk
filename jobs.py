import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from db import get_connection

logger = logging.getLogger("prepdesk.jobs")

VALID_STATUSES: tuple[str, ...] = (
    "wishlist",
    "applied",
    "oa",
    "interview",
    "offer",
    "rejected",
)

FOLLOWUP_STATUSES: tuple[str, ...] = ("applied", "oa", "interview")


def _validate_status(status: str) -> None:
    """Validate that status is one of the allowed application statuses."""
    if status not in VALID_STATUSES:
        allowed = ", ".join(VALID_STATUSES)
        raise ValueError(f"Invalid status '{status}'. Allowed values: {allowed}.")


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _parse_utc_iso(timestamp: str) -> datetime:
    """Parse an ISO-8601 timestamp string into a timezone-aware UTC datetime."""
    dt = datetime.fromisoformat(timestamp)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def add_application(
    company: str,
    role: str,
    link: str = "",
    notes: str = "",
    status: str = "applied",
) -> dict[str, Any]:
    """Insert a new job application and return the created record as a dict."""
    _validate_status(status)
    now = _utc_now_iso()

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO applications (company, role, status, link, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (company, role, status, link, notes, now, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM applications WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        logger.info("Added application id=%s for %s (%s)", cursor.lastrowid, company, role)
        return dict(row)
    finally:
        conn.close()


def get_application(id: int) -> dict[str, Any]:
    """Fetch a single job application by ID, raising ValueError if it does not exist."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM applications WHERE id = ?",
            (id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Application with id {id} does not exist.")
        return dict(row)
    finally:
        conn.close()


def update_application(
    id: int,
    status: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Update an existing application's status and/or notes and return the updated dict."""
    if status is not None:
        _validate_status(status)

    now = _utc_now_iso()
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT * FROM applications WHERE id = ?",
            (id,),
        ).fetchone()
        if existing is None:
            raise ValueError(f"Application with id {id} does not exist.")

        conn.execute(
            """
            UPDATE applications
            SET status = COALESCE(?, status),
                notes = COALESCE(?, notes),
                updated_at = ?
            WHERE id = ?
            """,
            (status, notes, now, id),
        )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM applications WHERE id = ?",
            (id,),
        ).fetchone()
        logger.info("Updated application id=%s", id)
        return dict(updated)
    finally:
        conn.close()


def list_applications(status: str | None = None) -> list[dict[str, Any]]:
    """List job applications, optionally filtered by status."""
    if status is not None:
        _validate_status(status)

    conn = get_connection()
    try:
        if status is not None:
            rows = conn.execute(
                "SELECT * FROM applications WHERE status = ? ORDER BY updated_at DESC, id DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM applications ORDER BY updated_at DESC, id DESC",
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def followups_due(days_since_update: int = 7) -> list[dict[str, Any]]:
    """Return active applications (applied, oa, interview) not updated within the given days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_since_update)
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM applications
            WHERE status IN ('applied', 'oa', 'interview')
            ORDER BY updated_at ASC, id ASC
            """
        ).fetchall()
        due: list[dict[str, Any]] = []
        for row in rows:
            updated_at = row["updated_at"]
            if updated_at and _parse_utc_iso(updated_at) < cutoff:
                due.append(dict(row))
        return due
    finally:
        conn.close()
