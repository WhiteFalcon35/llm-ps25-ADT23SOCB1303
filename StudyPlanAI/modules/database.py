import json
import sqlite3
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "studypilot.db"


def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    with connect() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                schedule_json TEXT NOT NULL,
                subjects_json TEXT NOT NULL,
                settings_json TEXT
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS topic_progress (
                subject TEXT NOT NULL,
                topic TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                quiz_score REAL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (subject, topic)
            )
        """)


def save_plan(schedule, subjects, settings=None):
    initialize_database()

    with connect() as connection:
        cursor = connection.execute("""
            INSERT INTO plans (
                created_at,
                schedule_json,
                subjects_json,
                settings_json
            )
            VALUES (?, ?, ?, ?)
        """, (
            datetime.now().isoformat(timespec="seconds"),
            json.dumps(schedule),
            json.dumps(subjects),
            json.dumps(settings or {})
        ))

        return cursor.lastrowid


def load_latest_plan():
    initialize_database()

    with connect() as connection:
        row = connection.execute("""
            SELECT *
            FROM plans
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "schedule": json.loads(row["schedule_json"]),
        "subjects": json.loads(row["subjects_json"]),
        "settings": json.loads(row["settings_json"] or "{}")
    }


def update_topic(subject, topic, status, quiz_score=None):
    initialize_database()

    allowed_statuses = {
        "Pending",
        "In Progress",
        "Completed",
        "Needs Revision"
    }

    if status not in allowed_statuses:
        raise ValueError("Invalid topic status.")

    if quiz_score is not None:
        quiz_score = float(quiz_score)

        if not 0 <= quiz_score <= 100:
            raise ValueError("Quiz score must be between 0 and 100.")

    with connect() as connection:
        connection.execute("""
            INSERT INTO topic_progress (
                subject,
                topic,
                status,
                quiz_score,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(subject, topic)
            DO UPDATE SET
                status = excluded.status,
                quiz_score = excluded.quiz_score,
                updated_at = excluded.updated_at
        """, (
            subject,
            topic,
            status,
            quiz_score,
            datetime.now().isoformat(timespec="seconds")
        ))


def get_topic_progress():
    initialize_database()

    with connect() as connection:
        rows = connection.execute("""
            SELECT subject, topic, status, quiz_score, updated_at
            FROM topic_progress
            ORDER BY subject, topic
        """).fetchall()

    return [dict(row) for row in rows]