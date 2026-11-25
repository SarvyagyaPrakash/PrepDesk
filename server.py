import logging
import sys
from typing import Any

from fastmcp import FastMCP

import briefing
import deadlines
import jobs
import matcher
import notes

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


@mcp.tool()
def index_notes(folder: str = "data/notes") -> dict[str, Any]:
    """Index PDF, Markdown, and text lecture notes inside the data/ directory.

    Use this when the student adds new notes or asks to index/refresh their
    study notes before searching them. Only paths inside ./data are allowed.
    """
    return notes.index_notes(folder=folder)


@mcp.tool()
def search_notes(question: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Search the student's indexed study notes for passages relevant to a question.

    Use this when the student asks a study question about their lecture notes
    or wants to find where a topic is covered in their files.
    Returns the most relevant passages from the user's notes with similarity scores.
    If none of the passages actually answers the question, tell the user their
    notes don't cover it; do not invent an answer. Always mention the source file and page.
    """
    return notes.search_notes(question=question, top_k=top_k)


@mcp.tool()
def match_resume(
    job_description: str,
    resume_path: str = "data/resume.pdf",
    application_id: int | None = None,
) -> dict[str, Any]:
    """Compare the user's resume to a pasted job description.

    Use this when the student pastes a job description and wants to see how well
    their resume matches it, optionally logging the summary to an application
    record via application_id. Returns overall match percent, missing skills,
    matched requirements, and gaps. The score is a rough estimate; after calling
    this tool, give practical advice on how to close the identified gaps.
    """
    return matcher.match_resume(
        job_description=job_description,
        resume_path=resume_path,
        application_id=application_id,
    )


@mcp.tool()
def weekly_briefing(days: int = 7) -> dict[str, Any]:
    """Return a weekly status overview of deadlines and job follow-ups.

    Use this when the user asks what to focus on this week, wants a plan, or
    wants a status overview of overdue deadlines, upcoming deadlines within
    the next `days` days, and job applications needing follow-up.
    """
    return briefing.weekly_briefing(days=days)


@mcp.resource("deadlines://upcoming")
def upcoming_deadlines() -> str:
    """Read-only snapshot of upcoming study deadlines."""
    return briefing.format_upcoming_deadlines(days_ahead=14)


@mcp.prompt()
def quiz_me(topic: str, num_questions: int = 5) -> str:
    """Generate an interactive quiz grounded strictly in the student's notes."""
    return (
        f"Quiz the student on '{topic}' with {num_questions} questions.\n"
        f"1. First, call search_notes with question='{topic}' and top_k=6.\n"
        "2. If the returned passages do not cover the topic, tell the student "
        "their notes don't cover it instead of inventing questions.\n"
        f"3. Otherwise, write {num_questions} questions based ONLY on the returned "
        "passages, mixing definition, explain-why, and application questions.\n"
        "4. Ask ONE question at a time and wait for the student's answer.\n"
        "5. After each answer, grade it against the passages, explain any gaps, "
        "and cite the source file and page."
    )


@mcp.prompt()
def weekly_plan() -> str:
    """Create a structured 7-day study and job-search plan from current data."""
    return (
        "Build a practical 7-day plan for the student.\n"
        "1. First, call weekly_briefing to get today's date, overdue deadlines, "
        "upcoming deadlines, and job follow-ups due.\n"
        "2. Produce a day-by-day plan for the next 7 days following these rules:\n"
        "   - Put overdue items first.\n"
        "   - Schedule study blocks before the nearest deadlines.\n"
        "   - Include job follow-ups that are due.\n"
        "   - Limit each day to at most 3 items."
    )


if __name__ == "__main__":
    logger.info("Starting PrepDesk MCP server over stdio")
    mcp.run(transport="stdio")
