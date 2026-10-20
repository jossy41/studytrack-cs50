
"""StudyTrack web application routes and request handling.

Developed with assistance from Grok (xAI). The implementation was
subsequently reviewed, tested, and debugged.

Routes:
- GET  /                         Display dashboard and deadline statistics.
- GET  /tasks                    Search and filter tasks.
- GET/POST /tasks/new            Create a task.
- GET/POST /tasks/<id>/edit      Edit an existing task.
- GET/POST /tasks/<id>/delete    Confirm and delete a task.
- POST /tasks/<id>/complete      Update task completion status.
"""
import os
from datetime import date

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

import helpers

# How many deadline rows to show on the dashboard before linking to the full list.
PREVIEW_LIMIT = 6


def safe_next(target):
    """Allow a redirect only to a same-site path such as /tasks?status=overdue.

    Rejects full URLs and scheme-relative URLs (//example.com) so a form
    cannot send the browser to another site.
    """
    if not target:
        return None
    target = str(target).strip()
    if not target.startswith("/"):
        return None
    if target.startswith("//") or target.startswith("/\\"):
        return None
    if "\\" in target or "\n" in target or "\r" in target:
        return None
    return target


def redirect_back(fallback):
    """Go back to the page that submitted the form, when that path is safe."""
    nxt = safe_next(request.form.get("next"))
    if nxt:
        return redirect(nxt)
    return redirect(fallback)


def create_app(db_path=None):
    """Build the Flask app. Tests pass their own database path."""
    app = Flask(__name__)
    # Flash messages need a secret. Override this outside a local demo.
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "dev-only-studytrack-key"
    )
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    if db_path is None:
        db_path = os.environ.get("STUDYTRACK_DB")
    if not db_path:
        folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance")
        os.makedirs(folder, exist_ok=True)
        db_path = os.path.join(folder, "studytrack.db")
    else:
        folder = os.path.dirname(os.path.abspath(db_path))
        if folder:
            os.makedirs(folder, exist_ok=True)

    app.config["DB_PATH"] = db_path
    helpers.init_db(db_path)

    @app.before_request
    def open_db():
        g.db = helpers.connect(app.config["DB_PATH"])

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.context_processor
    def inject_dates():
        today = date.today()
        return {
            "today": today,
            "today_label": helpers.format_long_date(today),
        }

    @app.get("/")
    def dashboard():
        stats = helpers.dashboard_stats(g.db)
        return render_template(
            "dashboard.html",
            stats=stats,
            upcoming=stats["upcoming"][:PREVIEW_LIMIT],
            overdue=stats["overdue"][:PREVIEW_LIMIT],
            upcoming_more=max(0, len(stats["upcoming"]) - PREVIEW_LIMIT),
            overdue_more=max(0, len(stats["overdue"]) - PREVIEW_LIMIT),
        )

    @app.get("/tasks")
    def tasks():
        filters = {
            "q": request.args.get("q", ""),
            "subject": request.args.get("subject", ""),
            "priority": request.args.get("priority", ""),
            "status": request.args.get("status", "all"),
        }
        rows = helpers.list_tasks(
            g.db,
            query=filters["q"],
            subject=filters["subject"],
            priority=filters["priority"],
            status=filters["status"],
        )
        active = any(
            [
                helpers.collapse_spaces(filters["q"]),
                helpers.collapse_spaces(filters["subject"]),
                filters["priority"].strip().lower() in helpers.PRIORITIES,
                filters["status"].strip().lower()
                in ("pending", "completed", "overdue", "upcoming"),
            ]
        )
        return render_template(
            "tasks.html",
            tasks=rows,
            filters=filters,
            subjects=helpers.distinct_subjects(g.db),
            priorities=helpers.PRIORITIES,
            total=helpers.count_tasks(g.db),
            filters_active=active,
        )

    @app.route("/tasks/new", methods=["GET", "POST"])
    def new_task():
        if request.method == "POST":
            data, errors = helpers.validate_task(request.form)
            if errors:
                return (
                    render_template(
                        "form.html",
                        mode="new",
                        errors=errors,
                        values=request.form,
                    ),
                    400,
                )
            helpers.create_task(g.db, data)
            flash("Task created.", "success")
            return redirect(url_for("tasks"))
        return render_template(
            "form.html",
            mode="new",
            errors=[],
            values={"priority": "medium"},
        )

    @app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
    def edit_task(task_id):
        task = helpers.get_task(g.db, task_id)
        if task is None:
            flash("That task could not be found.", "error")
            return redirect(url_for("tasks"))
        if request.method == "POST":
            data, errors = helpers.validate_task(request.form)
            if errors:
                return (
                    render_template(
                        "form.html",
                        mode="edit",
                        task=task,
                        errors=errors,
                        values=request.form,
                    ),
                    400,
                )
            if not helpers.update_task(g.db, task_id, data):
                flash("That task could not be found.", "error")
                return redirect(url_for("tasks"))
            flash("Task updated.", "success")
            return redirect(url_for("tasks"))
        return render_template(
            "form.html",
            mode="edit",
            task=task,
            errors=[],
            values=task,
        )

    @app.route("/tasks/<int:task_id>/delete", methods=["GET", "POST"])
    def delete_task(task_id):
        task = helpers.get_task(g.db, task_id)
        if task is None:
            flash("That task could not be found.", "error")
            return redirect(url_for("tasks"))
        if request.method == "POST":
            if helpers.delete_task(g.db, task_id):
                flash("Task deleted.", "success")
            else:
                flash("That task could not be found.", "error")
            return redirect(url_for("tasks"))
        return render_template("delete.html", task=task)

    @app.post("/tasks/<int:task_id>/complete")
    def complete(task_id):
        raw = request.form.get("completed", "")
        if raw not in ("0", "1"):
            flash("Could not update that task.", "error")
            return redirect_back(url_for("tasks"))
        if not helpers.set_completed(g.db, task_id, raw == "1"):
            flash("That task could not be found.", "error")
        elif raw == "1":
            flash("Marked complete.", "success")
        else:
            flash("Marked as not complete.", "success")
        return redirect_back(url_for("tasks"))

    @app.errorhandler(404)
    def not_found(_exc):
        return render_template("not_found.html"), 404

    @app.errorhandler(500)
    def server_error(_exc):
        return render_template("error.html"), 500

    return app


def main():
    """Start the local server. The preview listens on 0.0.0.0 port 8080."""
    app = create_app()
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()
