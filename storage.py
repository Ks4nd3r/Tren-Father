"""SQLite storage independent of the user interface."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path


def parse_workout_date(value: str) -> date:
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Дата должна быть в формате ГГГГ-ММ-ДД")
    return parsed


class WorkoutStore:
    def __init__(self, path: str | Path):
        self.connection = sqlite3.connect(str(path))
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY,
                workout_date TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS exercise_entries (
                id INTEGER PRIMARY KEY,
                workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
                muscle_group TEXT NOT NULL,
                exercise_name TEXT NOT NULL,
                UNIQUE(workout_id, muscle_group, exercise_name)
            );
            CREATE TABLE IF NOT EXISTS sets (
                id INTEGER PRIMARY KEY,
                exercise_id INTEGER NOT NULL REFERENCES exercise_entries(id) ON DELETE CASCADE,
                position INTEGER NOT NULL,
                reps INTEGER NOT NULL CHECK(reps > 0),
                weight_kg REAL NOT NULL CHECK(weight_kg >= 0),
                UNIQUE(exercise_id, position)
            );
            CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(workout_date);
        """)

    def close(self) -> None:
        self.connection.close()

    def save_exercise(
        self, workout_date: str, muscle_group: str, exercise_name: str,
        sets: list[tuple[int, float]],
    ) -> None:
        parse_workout_date(workout_date)
        if not muscle_group.strip() or not exercise_name.strip():
            raise ValueError("Выберите группу мышц и упражнение")
        if not sets:
            raise ValueError("Добавьте хотя бы один подход")
        for reps, weight in sets:
            if not isinstance(reps, int) or isinstance(reps, bool) or reps <= 0:
                raise ValueError("Повторы должны быть целым числом больше нуля")
            if weight < 0 or weight != weight or weight == float("inf"):
                raise ValueError("Вес должен быть неотрицательным числом")

        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO workouts(workout_date) VALUES (?)", (workout_date,)
            )
            workout_id = self.connection.execute(
                "SELECT id FROM workouts WHERE workout_date = ?", (workout_date,)
            ).fetchone()[0]
            self.connection.execute(
                "INSERT OR IGNORE INTO exercise_entries(workout_id, muscle_group, exercise_name) "
                "VALUES (?, ?, ?)", (workout_id, muscle_group, exercise_name)
            )
            exercise_id = self.connection.execute(
                "SELECT id FROM exercise_entries WHERE workout_id = ? AND muscle_group = ? "
                "AND exercise_name = ?", (workout_id, muscle_group, exercise_name)
            ).fetchone()[0]
            self.connection.execute("DELETE FROM sets WHERE exercise_id = ?", (exercise_id,))
            self.connection.executemany(
                "INSERT INTO sets(exercise_id, position, reps, weight_kg) VALUES (?, ?, ?, ?)",
                ((exercise_id, index, reps, weight) for index, (reps, weight) in enumerate(sets, 1)),
            )

    def get_sets(self, workout_date: str, muscle_group: str, exercise_name: str) -> list[tuple[int, float]]:
        parse_workout_date(workout_date)
        return self.connection.execute("""
            SELECT s.reps, s.weight_kg FROM sets s
            JOIN exercise_entries e ON e.id = s.exercise_id
            JOIN workouts w ON w.id = e.workout_id
            WHERE w.workout_date = ? AND e.muscle_group = ? AND e.exercise_name = ?
            ORDER BY s.position
        """, (workout_date, muscle_group, exercise_name)).fetchall()

    def list_workouts(self) -> list[tuple[str, int, int]]:
        return self.connection.execute("""
            SELECT w.workout_date, COUNT(DISTINCT e.id), COUNT(s.id)
            FROM workouts w
            LEFT JOIN exercise_entries e ON e.workout_id = w.id
            LEFT JOIN sets s ON s.exercise_id = e.id
            GROUP BY w.id ORDER BY w.workout_date DESC
        """).fetchall()

    def workout_details(self, workout_date: str) -> list[tuple[str, str, int, int, float]]:
        parse_workout_date(workout_date)
        return self.connection.execute("""
            SELECT e.muscle_group, e.exercise_name, s.position, s.reps, s.weight_kg
            FROM workouts w JOIN exercise_entries e ON e.workout_id = w.id
            JOIN sets s ON s.exercise_id = e.id
            WHERE w.workout_date = ? ORDER BY e.id, s.position
        """, (workout_date,)).fetchall()

    def count_older_than(self, days: int, today: date | None = None) -> int:
        cutoff = self._cutoff(days, today)
        return self.connection.execute(
            "SELECT COUNT(*) FROM workouts WHERE workout_date < ?", (cutoff,)
        ).fetchone()[0]

    def delete_older_than(self, days: int, today: date | None = None) -> int:
        cutoff = self._cutoff(days, today)
        with self.connection:
            cursor = self.connection.execute(
                "DELETE FROM workouts WHERE workout_date < ?", (cutoff,)
            )
        return cursor.rowcount

    @staticmethod
    def _cutoff(days: int, today: date | None) -> str:
        if not isinstance(days, int) or days < 1:
            raise ValueError("Период должен быть целым числом дней больше нуля")
        return ((today or date.today()) - timedelta(days=days)).isoformat()
