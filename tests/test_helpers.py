"""Tests for validation, storage, filters, and dashboard counts.

Generated with AI assistance (Grok, xAI, 2026). Do not submit these
tests as unaided CS50 work.
"""

import os
import tempfile
import unittest
from datetime import date

import helpers


TODAY = date(2026, 10, 20)


def sample(**overrides):
    data = {
        "title": "Read the notes",
        "subject": "CS50",
        "description": "Arrays and pointers",
        "due_date": "2026-10-25",
        "priority": "medium",
    }
    data.update(overrides)
    return data


class ValidateTests(unittest.TestCase):
    def test_missing_fields(self):
        data, errors = helpers.validate_task({})
        self.assertIsNone(data)
        joined = " ".join(errors)
        self.assertIn("Title is required", joined)
        self.assertIn("Subject is required", joined)
        self.assertIn("Due date is required", joined)
        self.assertIn("Priority must be", joined)

    def test_impossible_and_sloppy_dates(self):
        for raw in ("2026-02-31", "not-a-date", "2026-2-01", "10/20/2026"):
            data, errors = helpers.validate_task(sample(due_date=raw))
            self.assertIsNone(data, raw)
            self.assertTrue(any("real calendar date" in item for item in errors), raw)

    def test_trims_and_accepts_a_real_task(self):
        data, errors = helpers.validate_task(
            {
                "title": "  Review   hashing ",
                "subject": " Algorithms ",
                "description": "  Chapter 5\nWith notes  ",
                "due_date": "2026-11-02",
                "priority": "HIGH",
            }
        )
        self.assertEqual(errors, [])
        self.assertEqual(data["title"], "Review hashing")
        self.assertEqual(data["subject"], "Algorithms")
        self.assertEqual(data["description"], "Chapter 5\nWith notes")
        self.assertEqual(data["priority"], "high")
        self.assertEqual(data["due_date"], "2026-11-02")

    def test_length_limits(self):
        data, errors = helpers.validate_task(
            sample(title="x" * 121, subject="y" * 61, description="z" * 2001)
        )
        self.assertIsNone(data)
        self.assertEqual(len(errors), 3)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "tasks.db")
        helpers.init_db(self.path)
        helpers.init_db(self.path)
        self.conn = helpers.connect(self.path)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def add(self, **overrides):
        return helpers.create_task(self.conn, sample(**overrides))

    def test_counts_overdue_upcoming_and_completion(self):
        overdue_id = self.add(title="Lab", due_date="2026-10-18", priority="high", subject="C")
        soon_id = self.add(
            title="Problem set",
            due_date="2026-10-22",
            priority="low",
            subject="Python",
            description="find the bug",
        )
        self.add(title="Essay", due_date="2026-12-01", priority="medium", subject="Writing")

        stats = helpers.dashboard_stats(self.conn, TODAY)
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["completed"], 0)
        self.assertEqual(stats["pending"], 3)
        self.assertEqual(stats["overdue_count"], 1)
        self.assertEqual(stats["percent"], 0)
        self.assertEqual(stats["overdue"][0]["id"], overdue_id)
        self.assertEqual([row["id"] for row in stats["upcoming"]], [soon_id])

        self.assertTrue(helpers.set_completed(self.conn, soon_id, True))
        stats = helpers.dashboard_stats(self.conn, TODAY)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["pending"], 2)
        self.assertEqual(stats["percent"], 33)
        self.assertEqual(stats["upcoming"], [])

        # A finished task with a past date is not overdue.
        self.assertTrue(helpers.set_completed(self.conn, overdue_id, True))
        stats = helpers.dashboard_stats(self.conn, TODAY)
        self.assertEqual(stats["overdue_count"], 0)
        self.assertEqual(stats["percent"], 67)

    def test_search_filters_and_wildcard_escaping(self):
        self.add(title="Overdue lab", due_date="2026-10-18", subject="C", description="pointers")
        match_id = self.add(
            title="Upcoming set",
            due_date="2026-10-22",
            subject="Python",
            priority="low",
            description="find the bug",
        )
        self.add(title="100% quiz", due_date="2026-10-21", subject="Math", description="score")
        self.add(title="a_b drill", due_date="2026-10-21", subject="Math", description="")
        self.add(title="axb drill", due_date="2026-10-21", subject="Math", description="")

        found = helpers.list_tasks(self.conn, query="BUG", today=TODAY)
        self.assertEqual([row["id"] for row in found], [match_id])

        found = helpers.list_tasks(self.conn, subject="C", today=TODAY)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["title"], "Overdue lab")

        found = helpers.list_tasks(self.conn, status="overdue", today=TODAY)
        self.assertEqual(len(found), 1)

        found = helpers.list_tasks(self.conn, status="pending", priority="low", today=TODAY)
        self.assertEqual([row["title"] for row in found], ["Upcoming set"])

        found = helpers.list_tasks(self.conn, query="100%", today=TODAY)
        self.assertEqual([row["title"] for row in found], ["100% quiz"])

        found = helpers.list_tasks(self.conn, query="a_b", today=TODAY)
        self.assertEqual([row["title"] for row in found], ["a_b drill"])

        upcoming = helpers.list_tasks(self.conn, status="upcoming", today=TODAY)
        titles = {row["title"] for row in upcoming}
        self.assertIn("Upcoming set", titles)
        self.assertNotIn("Overdue lab", titles)
        self.assertNotIn("Essay", titles)

    def test_order_edit_and_delete(self):
        low_id = self.add(title="Low same day", due_date="2026-10-21", priority="low")
        high_id = self.add(title="High same day", due_date="2026-10-21", priority="high")
        done_id = self.add(title="Done early", due_date="2026-10-01", priority="high")
        helpers.set_completed(self.conn, done_id, True)

        ordered = [row["id"] for row in helpers.list_tasks(self.conn, today=TODAY)]
        self.assertEqual(ordered, [high_id, low_id, done_id])

        updated = sample(title="High same day revised", due_date="2026-10-21", priority="high")
        self.assertTrue(helpers.update_task(self.conn, high_id, updated))
        task = helpers.get_task(self.conn, high_id, TODAY)
        self.assertEqual(task["title"], "High same day revised")
        self.assertFalse(task["completed"])

        self.assertTrue(helpers.delete_task(self.conn, low_id))
        self.assertIsNone(helpers.get_task(self.conn, low_id, TODAY))
        self.assertFalse(helpers.delete_task(self.conn, low_id))
        self.assertFalse(helpers.set_completed(self.conn, low_id, True))
        self.assertFalse(helpers.update_task(self.conn, low_id, updated))

    def test_due_phrases(self):
        overdue = helpers.annotate_task(
            {"completed": 0, "due_date": "2026-10-19", "title": "A"}, TODAY
        )
        today_task = helpers.annotate_task(
            {"completed": 0, "due_date": "2026-10-20", "title": "B"}, TODAY
        )
        done = helpers.annotate_task(
            {"completed": 1, "due_date": "2026-10-19", "title": "C"}, TODAY
        )
        self.assertEqual(overdue["bucket"], "overdue")
        self.assertIn("Overdue by 1 day", overdue["due_phrase"])
        self.assertEqual(today_task["bucket"], "today")
        self.assertIn("Due today", today_task["due_phrase"])
        self.assertEqual(done["bucket"], "completed")
        self.assertIn("Completed", done["due_phrase"])


if __name__ == "__main__":
    unittest.main()
