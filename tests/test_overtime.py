import csv
import importlib
import io
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


class OvertimeActionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.tempdir.name, "overtime.db")
        with patch.dict(os.environ, {
            "DB_PATH": cls.db_path,
            "SECRET_KEY": "test-secret",
            "APP_USERNAME": "test",
            "APP_PASSWORD": "test",
            "APP_PASSWORD_HASH": "",
        }):
            cls.app_module = importlib.import_module("app")
        cls.app_module.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        cls.tempdir.cleanup()

    def setUp(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute("DELETE FROM entries")
        self.client = self.app_module.app.test_client()
        with self.client.session_transaction() as session:
            session["auth"] = True
            session["csrf"] = "test-token"

    def post_entry(self, path, date, hours, action):
        return self.client.post(path, data={
            "csrf": "test-token", "date": date, "hours": hours,
            "minutes": "", "action": action,
        })

    def test_existing_database_is_migrated_without_losing_entries(self):
        path = os.path.join(self.tempdir.name, "legacy.db")
        with sqlite3.connect(path) as db:
            db.executescript("""
                CREATE TABLE entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_date TEXT NOT NULL,
                    minutes INTEGER NOT NULL CHECK (minutes > 0),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                INSERT INTO entries (id, work_date, minutes, created_at)
                VALUES (42, '2026-01-02', 90, '2026-01-03 04:05:06');
            """)
        with patch.object(self.app_module, "DB_PATH", path):
            self.app_module.init_db()
            self.app_module.init_db()
        with sqlite3.connect(path) as db:
            row = db.execute(
                "SELECT id, work_date, minutes, created_at, action FROM entries"
            ).fetchone()
        self.assertEqual(row, (42, "2026-01-02", 90, "2026-01-03 04:05:06", "add"))

    def test_add_and_take_affect_totals_and_csv(self):
        self.assertEqual(self.post_entry("/", "2026-01-02", "1", "add").status_code, 302)
        self.assertEqual(self.post_entry("/", "2026-02-02", "2.5", "take").status_code, 302)
        page = self.client.get("/overview").get_data(as_text=True)
        self.assertIn("-1h 30m", page)
        self.assertIn("-2h 30m", page)
        self.assertIn("Taken", page)
        self.assertIn("Added", page)
        rows = list(csv.reader(io.StringIO(self.client.get("/export.csv").get_data(as_text=True))))
        self.assertEqual(rows, [
            ["date", "minutes", "hours"],
            ["2026-01-02", "60", "1.00"],
            ["2026-02-02", "-150", "-2.50"],
        ])
        with sqlite3.connect(self.db_path) as db:
            taken_id = db.execute("SELECT id FROM entries WHERE action = 'take'").fetchone()[0]
        self.client.post(f"/delete/{taken_id}", data={"csrf": "test-token"})
        page = self.client.get("/overview").get_data(as_text=True)
        self.assertIn("1h", page)
        self.assertNotIn("-2h 30m", page)

    def test_edit_changes_action_and_delete_reverses_effect(self):
        self.post_entry("/", "2026-01-02", "1.5", "take")
        with sqlite3.connect(self.db_path) as db:
            entry_id = db.execute("SELECT id FROM entries").fetchone()[0]
        edit_page = self.client.get(f"/edit/{entry_id}").get_data(as_text=True)
        self.assertIn('value="take" selected', edit_page)
        self.assertIn('value="1"', edit_page)
        self.assertIn('value="30"', edit_page)
        self.assertEqual(self.post_entry(f"/edit/{entry_id}", "2026-01-02", "2", "add").status_code, 302)
        self.assertIn("2h", self.client.get("/overview").get_data(as_text=True))
        self.client.post(f"/delete/{entry_id}", data={"csrf": "test-token"})
        self.assertIn("No overtime logged yet", self.client.get("/overview").get_data(as_text=True))

    def test_invalid_action_is_rejected(self):
        for action in ("invalid", ""):
            response = self.post_entry("/", "2026-01-02", "1", action)
            self.assertIn("Choose whether to add or take overtime.", response.get_data(as_text=True))
        with sqlite3.connect(self.db_path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM entries").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
