import logging
import sys
from typing import Any

from fastmcp import FastMCP

import deadlines
import jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("prepdesk")

mcp = FastMCP("PrepDesk")


@mcp.tool()
def ping() -> str:
    """Verify that the PrepDesk MCP server is running and responsive."""
    return "PrepDesk is alive"


@mcp.tool()
def add_application(
    company: str,
    role: str,
    link: str = "",
    notes: str = "",
    status: str = "applied",
) -> dict[str, Any]:
    """Add a new job application to the tracker and return the saved record.

    Use this when the student wants to log a new job they applied to, plan to
    apply to (status='wishlist'), or are tracking in their placement pipeline.
    Allowed statuses: wishlist, applied, oa, interview, offer, rejected.
    """
    return jobs.add_application(
        company=company,
        role=role,
        link=link,
        notes=notes,
        status=status,
    )


@mcp.tool()
def update_application(
    id: int,
    status: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Update the status and/or notes of an existing job application by its ID.

    Use this when an application moves to a new stage (e.g., from 'applied' to
    'oa', 'interview', 'offer', or 'rejected') or when the student wants to
    record new notes about an application. Allowed statuses: wishlist, applied,
    oa, interview, offer, rejected.
    """
    return jobs.update_application(id=id, status=status, notes=notes)


@mcp.tool()
def list_applications(status: str | None = None) -> list[dict[str, Any]]:
    """List tracked job applications, optionally filtered by application status.

    Use this when the student asks to view their job pipeline, check all
    applications, or see applications in a specific stage (wishlist, applied,
    oa, interview, offer, rejected).
    """
    return jobs.list_applications(status=status)


@mcp.tool()
def followups_due(days_since_update: int = 7) -> list[dict[str, Any]]:
    """List active job applications that have not been updated within the given days.

    Use this when the student asks which applications need a follow-up, which
    apps have gone quiet, or what pending applications (applied, oa, interview)
    haven't had activity in N days (default 7).
    """
    return jobs.followups_due(days_since_update=days_since_update)


@mcp.tool()
def get_today() -> dict[str, str]:
    """Return today's local date (YYYY-MM-DD) and weekday name.

    Use this whenever you need the current date or day of the week—especially
    before calling add_deadline when the user gives a relative date like
    'Friday', 'tomorrow', or 'next week'.
    """
    return deadlines.get_today()


@mcp.tool()
def add_deadline(title: str, due_date: str, course: str = "") -> dict[str, Any]:
    """Add an upcoming assignment, exam, or task deadline and return the saved record.

    Use this when the student wants to track a deadline or due date.
    due_date must be YYYY-MM-DD. If the user says a relative date like 'Friday'
    or 'next week', call get_today first and compute the date.
    """
    return deadlines.add_deadline(title=title, due_date=due_date, course=course)


@mcp.tool()
def list_deadlines(days_ahead: int = 14) -> list[dict[str, Any]]:
    """List overdue deadlines and upcoming deadlines within the next days_ahead days.

    Use this when the student asks what is due soon, what assignments or exams
    are coming up, or if anything is overdue. Items are sorted by due_date and
    include days_left and status ('overdue', 'today', or 'upcoming').
    """
    return deadlines.list_deadlines(days_ahead=days_ahead)


if __name__ == "__main__":
    logger.info("Starting PrepDesk MCP server over stdio")
    mcp.run(transport="stdio")
