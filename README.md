# StudyTrack
#### Video Demo: TODO
#### Description:

StudyTrack is a small web application that helps a student keep a list of study tasks in one place. Each task has a title, a subject, an optional description, a due date, and a priority of low, medium, or high. The student can add tasks, change them, delete them after a confirmation page, and mark them complete or incomplete. The list can be searched by words in the title or description and filtered by subject, priority, and status (pending, completed, overdue, or due within the next seven days).

The dashboard is the home page. It shows four counts: total tasks, completed tasks, pending tasks, and overdue tasks. It also shows a completion percentage, which is the number of completed tasks divided by the total, rounded to the nearest whole percent. If there are no tasks, the percentage is 0 rather than an error. Under the counts, the page lists unfinished tasks that are due today or within the next seven days, and a separate list of unfinished tasks whose due date is already past. A completed task is never called overdue, even when its due date is in the past. Empty lists explain that in a sentence instead of showing a blank area.

The application is written in Python with Flask. HTML pages are Jinja templates. Appearance is a single CSS file: a navy sidebar, a blue primary action, and a warm light background. A short SVG mark and the words “StudyTrack” form the wordmark. The mobile layout uses a menu button. That menu is a checkbox and CSS, so the main actions do not depend on JavaScript. The server checks every submitted form. A missing title or subject, a priority outside the three allowed values, a description over 2,000 characters, or a due date that is not a real `YYYY-MM-DD` day (including impossible days such as February 31) is rejected with a message on the form. The values the student already typed stay in the fields. Successful changes use the post-redirect-get pattern and a short flash message so a refresh does not submit the form twice.

Tasks are stored in SQLite. The table is created automatically the first time the app runs. SQL statements pass values with `?` placeholders instead of pasting user text into the query. Search treats `%` and `_` as ordinary characters. The database file lives in `instance/` and is listed in `.gitignore`, because it may contain personal study notes and should not be committed.

There is no account system. Anyone who can open the server can see and change the tasks. That is intentional for a single-student tool running on one computer, and it is also a limitation: do not put secrets in task descriptions, and do not expose the server on a public network.

This copy of the program was generated with AI assistance (Grok, xAI, 2026). See “Authorship” below before using it for a course.

## Development Process and Academic Integrity

StudyTrack was developed with AI assistance from Grok (xAI). The development process also involved reviewing the implementation, testing the application, debugging issues, and verifying its functionality.

CS50x 2026 has specific academic honesty requirements concerning AI-generated code. Anyone evaluating or using this project should distinguish AI-assisted implementation from work independently completed by the developer. Passing tests does not, by itself, establish authorship or guarantee that the project satisfies a course's submission requirements.

The tests listed below were run in the development environment. Running them independently and understanding the implementation are important steps in verifying the project.
## Features

- Dashboard with total, completed, pending, overdue, and completion percentage
- Create, edit, and delete tasks (delete asks for confirmation first)
- Mark a task complete or incomplete
- Filter by subject, priority, and status
- Search titles and descriptions
- Clear labeling of overdue tasks and tasks due within seven days
- SQLite storage that is created automatically
- Server-side validation and flash messages
- Empty states when there are no tasks or no filter matches

## Setup

From the `project` directory (the folder that contains `app.py`):

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

On Windows, activate the virtual environment with `venv\Scripts\activate` instead of `source`.

Python 3.10 or newer is expected. The only third-party dependency is Flask, pinned in `requirements.txt`. SQLite comes with Python.

## Run

```bash
python app.py
```

Then open `http://127.0.0.1:8080/` in a browser.

Optional environment variables:

- `PORT` — port to listen on (default `8080`)
- `STUDYTRACK_DB` — path to the SQLite file (default `instance/studytrack.db`)
- `SECRET_KEY` — key used to sign flash messages (a local development default is used if this is unset; set a long random value if anyone else can reach the server)

The database file and table are created on startup. You do not run a separate migration command.

## Usage

1. Choose **New task** and enter a title, subject, due date, and priority. Description is optional.
2. Open **Dashboard** to see counts, the completion bar, upcoming deadlines, and overdue tasks.
3. Open **Tasks** to search and filter. Use **Apply**, or **Clear** to reset.
4. Use the check button on a task to mark it complete or incomplete.
5. Use **Edit** to change fields. Completion stays as it was.
6. Use **Delete**, then confirm on the next page. **Keep task** cancels.

## Database

Table `tasks`:

| Column | Meaning |
| --- | --- |
| `id` | Integer primary key |
| `title` | Required, up to 120 characters |
| `subject` | Required, up to 60 characters |
| `description` | Optional, up to 2,000 characters |
| `due_date` | Text, `YYYY-MM-DD` |
| `priority` | `low`, `medium`, or `high` |
| `completed` | `0` or `1` |
| `created_at`, `updated_at` | Local timestamps |

Dates have no time of day and no time zone. “Today” is the date on the computer running the app.

## Testing

From the `project` directory, with the virtual environment activated:

```bash
python -m unittest discover -s tests -v
```

`tests/test_helpers.py` checks validation, create/update/delete, completion, overdue rules, search (including `%` and `_`), filters, and ordering.

`tests/test_app.py` uses Flask’s test client to walk through an empty dashboard, rejected input, create, filter, complete, edit, the delete confirmation page, and a missing page.

These tests use temporary database files. They do not read or write `instance/studytrack.db`.

## Project layout

```text
app.py               Flask routes
helpers.py           Validation, dates, and SQL
templates/           Jinja pages
static/styles.css    Layout and visual design
static/favicon.svg   Small wordmark icon
tests/               unittest modules
requirements.txt     Flask pin
```

## Known limitations

- One shared list. There are no accounts, and rows are not separated by user.
- No reminders, repeating tasks, grades, or time estimates.
- The completion percentage counts each task once. High-priority work is not weighted more heavily.
- Subject filters match the whole subject after extra spaces are collapsed. “CS50” and “cs50” are different subjects.
- The app is meant to run locally. Hosting it on a platform with a read-only filesystem will not be able to save the SQLite file.
- There is no JavaScript beyond what the browser does by itself. The interface was checked as server-rendered HTML.
- AI assistance produced this implementation. It is a reference program, not a claim that a student wrote it alone, and it should not be submitted as one.
