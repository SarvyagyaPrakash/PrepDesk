import logging
import sys
from typing import Any

from fastmcp import FastMCP

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


if __name__ == "__main__":
    logger.info("Starting PrepDesk MCP server over stdio")
    mcp.run(transport="stdio")
