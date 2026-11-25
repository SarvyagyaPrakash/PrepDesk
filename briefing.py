import logging
from typing import Any

import deadlines
import jobs

logger = logging.getLogger("prepdesk.briefing")


def weekly_briefing(days: int = 7) -> dict[str, Any]:
    """Assemble today's date, overdue/due-soon deadlines, job follow-ups, and counts."""
    today = deadlines.get_today()
    all_deadlines = deadlines.list_deadlines(days_ahead=days)

    overdue_deadlines = [d for d in all_deadlines if d["status"] == "overdue"]
    due_soon_deadlines = [
        d for d in all_deadlines if d["status"] in ("today", "upcoming")
    ]
    followups = jobs.followups_due(7)

    return {
        "today": today,
        "overdue_deadlines": overdue_deadlines,
        "due_soon_deadlines": due_soon_deadlines,
        "followups_due": followups,
        "counts": {
            "overdue_deadlines": len(overdue_deadlines),
            "due_soon_deadlines": len(due_soon_deadlines),
            "followups_due": len(followups),
        },
    }


def format_upcoming_deadlines(days_ahead: int = 14) -> str:
    """Format overdue and upcoming deadlines as a readable plain-text list."""
    items = deadlines.list_deadlines(days_ahead=days_ahead)
    if not items:
        return f"No overdue or upcoming deadlines in the next {days_ahead} days."

    lines: list[str] = []
    for item in items:
        days_left = item["days_left"]
        if days_left < 0:
            overdue_days = abs(days_left)
            timing = f"{overdue_days} day{'s' if overdue_days != 1 else ''} overdue"
        elif days_left == 0:
            timing = "today"
        else:
            timing = f"in {days_left} day{'s' if days_left != 1 else ''}"

        course = item["course"] or "-"
        lines.append(f"{item['due_date']} | {item['title']} | {course} | {timing}")
    return "\n".join(lines)
