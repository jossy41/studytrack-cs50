"""StudyTrack task rules and SQLite storage.

This file was generated with AI assistance (Grok, xAI, 2026).
CS50x academic honesty policy does not allow this code to be submitted
as a student's own unaided work. Read it, test it, and only hand in
work you can honestly claim as yours.

Queries use "?" placeholders. Values are passed separately so typed
text cannot change the SQL itself.
"""

import sqlite3
from datetime import date, datetime, timedelta

# Priorities the form is allowed to store. Anything else is rejected.
PRIORITIES = ("low", "medium", "high")

TITLE_MAX = 120
SUBJECT_MAX = 60
DESCRIPTION_MAX = 2000

# Unfinished tasks due today through this many days ahead count as upcoming.
UPCOMING_DAYS = 7

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    due_date TEXT NOT NULL,
    priority TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def connect(db_path):
    """Open SQLite and return rows as dictionaries (sqlite3.Row)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    """Create the tasks table if it does not exist yet. Safe to call again."""
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def format_long_date(value):
    """Format a date like 'Tuesday, October 20, 2026' without platform-specific codes."""
    return value.strftime("%A, %B ") + str(value.day) + value.strftime(", %Y")


def format_short_date(value):
    """Format a date like 'Oct 20, 2026'."""
    return value.strftime("%b ") + str(value.day) + value.strftime(", %Y")


def collapse_spaces(value):
    """Trim ends and turn any run of whitespace into a single space."""
    return " ".join(str(value or "").split())


def parse_due_date(value):
    """Return a date if value is a real YYYY-MM-DD day, otherwise None.

    strptime rejects impossible days such as 2026-02-31.
    """
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None
    # strptime accepts the calendar day; require the canonical zero-padded form
    # so "2026-2-1" is not stored differently from "2026-02-01".
    if parsed.isoformat() != text:
        return None
    return parsed


def validate_task(form):
    """Check a submitted task.

    Returns (cleaned_dict, []) when the input is usable, or (None, errors)
    when it is not. The cleaned dict is what gets stored.
    """
    errors = []
    title = collapse_spaces(form.get("title"))
    subject = collapse_spaces(form.get("subject"))
    # Description may keep line breaks; only the ends are trimmed.
    description = str(form.get("description") or "").strip()
    due_raw = str(form.get("due_date") or "").strip()
    priority = str(form.get("priority") or "").strip().lower()

    if not title:
        errors.append("Title is required.")
    elif len(title) > TITLE_MAX:
        errors.append(f"Title must be {TITLE_MAX} characters or fewer.")

    if not subject:
        errors.append("Subject is required.")
    elif len(subject) > SUBJECT_MAX:
        errors.append(f"Subject must be {SUBJECT_MAX} characters or fewer.")

    if len(description) > DESCRIPTION_MAX:
        errors.append(
            f"Description must be {DESCRIPTION_MAX:,} characters or fewer."
        )

    due = parse_due_date(due_raw)
    if not due_raw:
        errors.append("Due date is required.")
    elif due is None:
        errors.append("Due date must be a real calendar date in YYYY-MM-DD form.")

    if priority not in PRIORITIES:
        errors.append("Priority must be low, medium, or high.")

    if errors:
        return None, errors

    return {
        "title": title,
        "subject": subject,
        "description": description,
        "due_date": due.isoformat(),
        "priority": priority,
    }, []


def _timestamp():
    """Local time stamp stored with each insert and update."""
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def create_task(conn, data):
    """Insert one task and return its new id. The task starts incomplete."""
    now = _timestamp()
    cur = conn.execute(
        """
        INSERT INTO tasks
            (title, subject, description, due_date, priority, completed, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 0, ?, ?)
        """,
        (
            data["title"],
            data["subject"],
            data["description"],
            data["due_date"],
            data["priority"],
            now,
            now,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_task(conn, task_id, data):
    """Replace the editable fields of one task. Completion is left as it is.

    Returns True when a row was updated.
    """
    cur = conn.execute(
        """
        UPDATE tasks
        SET title = ?, subject = ?, description = ?, due_date = ?,
            priority = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            data["title"],
            data["subject"],
            data["description"],
            data["due_date"],
            data["priority"],
            _timestamp(),
            task_id,
        ),
    )
    conn.commit()
    return cur.rowcount == 1


def delete_task(conn, task_id):
    """Delete one task. Returns True when a row was removed."""
    cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    return cur.rowcount == 1


def set_completed(conn, task_id, completed):
    """Mark a task complete or incomplete. Returns True when the id exists."""
    cur = conn.execute(
        "UPDATE tasks SET completed = ?, updated_at = ? WHERE id = ?",
        (1 if completed else 0, _timestamp(), task_id),
    )
    conn.commit()
    return cur.rowcount == 1


def get_task(conn, task_id, today=None):
    """Return one annotated task, or None if that id does not exist."""
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        return None
    return annotate_task(dict(row), today or date.today())


def _like_pattern(term):
    """Build a LIKE pattern that treats % and _ in the search text as ordinary characters."""
    escaped = (
        term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
    return f"%{escaped}%"


def list_tasks(conn, query="", subject="", priority="", status="all", today=None):
    """Return annotated tasks matching the optional search and filters.

    status may be all, pending, completed, overdue, or upcoming.
    Unknown status values are treated as "all" rather than as an error,
    because they come from the query string.
    """
    today = today or date.today()
    clauses = []
    params = []

    text = collapse_spaces(query)
    if text:
        pattern = _like_pattern(text)
        clauses.append(
            "(title LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\')"
        )
        params.extend([pattern, pattern])

    subject = collapse_spaces(subject)
    if subject:
        clauses.append("subject = ?")
        params.append(subject)

    priority = str(priority or "").strip().lower()
    if priority in PRIORITIES:
        clauses.append("priority = ?")
        params.append(priority)

    status = str(status or "all").strip().lower()
    if status not in ("all", "pending", "completed", "overdue", "upcoming"):
        status = "all"

    today_iso = today.isoformat()
    if status == "completed":
        clauses.append("completed = 1")
    elif status == "pending":
        clauses.append("completed = 0")
    elif status == "overdue":
        clauses.append("completed = 0 AND due_date < ?")
        params.append(today_iso)
    elif status == "upcoming":
        end = (today + timedelta(days=UPCOMING_DAYS)).isoformat()
        clauses.append("completed = 0 AND due_date >= ? AND due_date <= ?")
        params.extend([today_iso, end])

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    # The ORDER BY expression is fixed text, not user input.
    sql = f"""
        SELECT * FROM tasks
        {where}
        ORDER BY completed ASC,
                 due_date ASC,
                 CASE priority
                     WHEN 'high' THEN 0
                     WHEN 'medium' THEN 1
                     ELSE 2
                 END,
                 title COLLATE NOCASE
    """
    rows = conn.execute(sql, params).fetchall()
    return [annotate_task(dict(row), today) for row in rows]


def distinct_subjects(conn):
    """Subjects currently in use, for the filter dropdown."""
    rows = conn.execute(
        "SELECT DISTINCT subject FROM tasks ORDER BY subject COLLATE NOCASE"
    ).fetchall()
    return [row["subject"] for row in rows]


def count_tasks(conn):
    """How many tasks are stored, ignoring filters."""
    row = conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()
    return int(row["n"])


def task_bucket(task, today):
    """Classify a task so templates can label it without repeating date math."""
    if task["completed"]:
        return "completed"
    due = date.fromisoformat(task["due_date"])
    if due < today:
        return "overdue"
    if due == today:
        return "today"
    if due <= today + timedelta(days=UPCOMING_DAYS):
        return "upcoming"
    return "later"


def due_phrase(task, today):
    """A short sentence such as 'Overdue by 2 days · Oct 18, 2026'."""
    due = date.fromisoformat(task["due_date"])
    pretty = format_short_date(due)
    if task["completed"]:
        return f"Completed · was due {pretty}"
    delta = (due - today).days
    if delta < 0:
        n = -delta
        unit = "day" if n == 1 else "days"
        return f"Overdue by {n} {unit} · {pretty}"
    if delta == 0:
        return f"Due today · {pretty}"
    if delta == 1:
        return f"Due tomorrow · {pretty}"
    if delta <= UPCOMING_DAYS:
        return f"Due in {delta} days · {pretty}"
    return f"Due {pretty}"


def annotate_task(task, today):
    """Copy a task row and add bucket, due_phrase, and a real boolean completed flag."""
    task = dict(task)
    task["completed"] = bool(task["completed"])
    task["bucket"] = task_bucket(task, today)
    task["due_phrase"] = due_phrase(task, today)
    return task


def completion_percent(completed, total):
    """Nearest whole percent. Zero when there are no tasks, so we never divide by zero."""
    if total <= 0:
        return 0
    return int((100 * completed) / total + 0.5)


def dashboard_stats(conn, today=None):
    """Counts and short lists for the dashboard.

    A completed task is never overdue, even if its due date is in the past.
    Upcoming means unfinished and due within UPCOMING_DAYS, including today.
    """
    today = today or date.today()
    rows = [
        annotate_task(dict(row), today)
        for row in conn.execute("SELECT * FROM tasks").fetchall()
    ]
    total = len(rows)
    completed = sum(1 for row in rows if row["completed"])
    overdue = [row for row in rows if row["bucket"] == "overdue"]
    upcoming = [row for row in rows if row["bucket"] in ("today", "upcoming")]
    overdue.sort(key=lambda row: (row["due_date"], row["title"].lower()))
    upcoming.sort(key=lambda row: (row["due_date"], row["title"].lower()))
    return {
        "total": total,
        "completed": completed,
        "pending": total - completed,
        "overdue_count": len(overdue),
        "percent": completion_percent(completed, total),
        "overdue": overdue,
        "upcoming": upcoming,
    }
