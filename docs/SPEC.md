# PrepDesk Specification

PrepDesk is a local Model Context Protocol (MCP) server for students, acting as a study and placement assistant.

## Planned MCP Surface

### Tools

- `index_notes(folder)`
- `search_notes(question, top_k)`
- `add_deadline(title, due_date, course)`
- `list_deadlines(days_ahead)`
- `get_today()`
- `add_application(company, role, link, notes, status)`
- `update_application(id, status, notes)`
- `list_applications(status)`
- `followups_due(days_since_update)`
- `match_resume(job_description)`

### Resource

- `deadlines://upcoming`

### Prompts

- `quiz_me(topic)`
- `weekly_plan()`

## Domain Model

- **Application statuses:** `wishlist`, `applied`, `oa`, `interview`, `offer`, `rejected`

## Architecture & Engineering Rules

- **Stdio safety:** Never call `print()` to `stdout`; use Python's `logging` module writing to `stderr`.
- **Thin server layer:** `server.py` only registers MCP tools, resources, and prompts. Core logic lives in `jobs.py`, `notes.py`, `embeddings.py`, `matcher.py`, and `db.py` so it can be tested independently of MCP.
- **Tool metadata:** Every tool must define type hints and a clear docstring for LLM consumption.
- **Filesystem boundary:** File access is strictly restricted to `./data`; any path outside `./data` must be rejected.
- **Storage:** All structured data is stored locally in SQLite at `data/prepdesk.db`.
