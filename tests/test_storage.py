import tempfile
import unittest
from datetime import date
from pathlib import Path

from storage import WorkoutStore


class WorkoutStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "diary.db"
        self.store = WorkoutStore(self.path)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_saved_sets_survive_restart_and_replace_existing_exercise(self):
        self.store.save_exercise("2026-11-23", "Грудь", "Жим штанги лёжа", [(8, 60), (6, 65)])
        self.store.close()
        self.store = WorkoutStore(self.path)
        self.assertEqual(self.store.get_sets("2026-11-23", "Грудь", "Жим штанги лёжа"),
                         [(8, 60.0), (6, 65.0)])
        self.store.save_exercise("2026-11-23", "Грудь", "Жим штанги лёжа", [(10, 62.5)])
        self.assertEqual(self.store.list_workouts(), [("2026-11-23", 1, 1)])
        self.assertEqual(self.store.get_sets("2026-11-23", "Грудь", "Жим штанги лёжа"),
                         [(10, 62.5)])

    def test_cleanup_deletes_only_older_workouts_and_their_sets(self):
        self.store.save_exercise("2026-10-01", "Спина", "Подтягивания", [(5, 0)])
        self.store.save_exercise("2026-11-20", "Спина", "Подтягивания", [(8, 0)])
        today = date(2026, 11, 23)
        self.assertEqual(self.store.count_older_than(30, today), 1)
        self.assertEqual(self.store.delete_older_than(30, today), 1)
        self.assertEqual(self.store.list_workouts(), [("2026-11-20", 1, 1)])
        self.assertEqual(self.store.connection.execute("SELECT COUNT(*) FROM sets").fetchone()[0], 1)

    def test_invalid_input_does_not_create_partial_workout(self):
        with self.assertRaises(ValueError):
            self.store.save_exercise("2026-11-23", "Ноги", "Присед", [(0, 50)])
        self.assertEqual(self.store.list_workouts(), [])
        with self.assertRaises(ValueError):
            self.store.save_exercise("2026-02-30", "Ноги", "Присед", [(5, 50)])


if __name__ == "__main__":
    unittest.main()
