"""Browser-free tests for the Flask routes, using Flask's test client.

Generated with AI assistance (Grok, xAI, 2026). Do not submit these
tests as unaided CS50 work.
"""

import os
import tempfile
import unittest

from app import create_app, safe_next


class SafeNextTests(unittest.TestCase):
    def test_allows_local_paths_only(self):
        self.assertEqual(safe_next("/tasks?status=overdue"), "/tasks?status=overdue")
        self.assertEqual(safe_next("  /  "), "/")
        self.assertIsNone(safe_next("https://example.com"))
        self.assertIsNone(safe_next("//example.com"))
        self.assertIsNone(safe_next("/\\example"))
        self.assertIsNone(safe_next("tasks"))
        self.assertIsNone(safe_next(""))


class AppFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        path = os.path.join(self.tmp.name, "app.db")
        self.app = create_app(path)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_dashboard_and_validation(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"No tasks yet", page.data)
        self.assertIn(b"StudyTrack", page.data)
        self.assertIn(b"0%", page.data)

        bad = self.client.post(
            "/tasks/new",
            data={
                "title": "",
                "subject": "",
                "description": "",
                "due_date": "2026-02-31",
                "priority": "urgent",
            },
        )
        self.assertEqual(bad.status_code, 400)
        self.assertIn(b"Title is required", bad.data)
        self.assertIn(b"real calendar date", bad.data)
        self.assertIn(b"Priority must be", bad.data)

        missing = self.client.get("/tasks/5/edit")
        self.assertEqual(missing.status_code, 302)

        unknown = self.client.get("/not-a-page")
        self.assertEqual(unknown.status_code, 404)
        self.assertIn(b"Page not found", unknown.data)

    def test_create_filter_complete_and_delete(self):
        created = self.client.post(
            "/tasks/new",
            data={
                "title": "Review pointers",
                "subject": "C",
                "description": "week 4 short",
                "due_date": "2026-10-18",
                "priority": "high",
            },
            follow_redirects=True,
        )
        self.assertEqual(created.status_code, 200)
        self.assertIn(b"Task created.", created.data)
        self.assertIn(b"Review pointers", created.data)
        self.assertIn(b"Overdue", created.data)

        home = self.client.get("/")
        self.assertIn(b"Review pointers", home.data)
        self.assertNotIn(b"No tasks yet", home.data)

        only_c = self.client.get("/tasks?subject=C&priority=high&status=overdue&q=pointers")
        self.assertIn(b"Review pointers", only_c.data)
        self.assertIn(b"Showing 1 of 1", only_c.data)

        none = self.client.get("/tasks?q=zzzz-not-there")
        self.assertIn(b"No matching tasks", none.data)

        done = self.client.post(
            "/tasks/1/complete",
            data={"completed": "1", "next": "/"},
            follow_redirects=True,
        )
        self.assertIn(b"Marked complete.", done.data)

        # Completing it means it is no longer overdue.
        overdue = self.client.get("/tasks?status=overdue")
        self.assertIn(b"No matching tasks", overdue.data)

        reopen = self.client.post(
            "/tasks/1/complete",
            data={"completed": "0", "next": "/tasks"},
            follow_redirects=True,
        )
        self.assertIn(b"Marked as not complete.", reopen.data)

        bad_toggle = self.client.post(
            "/tasks/1/complete",
            data={"completed": "maybe", "next": "https://example.com"},
            follow_redirects=False,
        )
        self.assertEqual(bad_toggle.status_code, 302)
        self.assertTrue(bad_toggle.headers["Location"].endswith("/tasks"))

        edited = self.client.post(
            "/tasks/1/edit",
            data={
                "title": "Review pointers again",
                "subject": "C",
                "description": "added a note",
                "due_date": "2026-10-28",
                "priority": "medium",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Task updated.", edited.data)
        self.assertIn(b"Review pointers again", edited.data)

        confirm = self.client.get("/tasks/1/delete")
        self.assertEqual(confirm.status_code, 200)
        self.assertIn(b"Delete this task?", confirm.data)
        self.assertIn(b"Review pointers again", confirm.data)

        removed = self.client.post("/tasks/1/delete", follow_redirects=True)
        self.assertIn(b"Task deleted.", removed.data)
        self.assertNotIn(b"Review pointers again", removed.data)

        gone = self.client.post("/tasks/1/delete", follow_redirects=True)
        self.assertIn(b"That task could not be found.", gone.data)


if __name__ == "__main__":
    unittest.main()
