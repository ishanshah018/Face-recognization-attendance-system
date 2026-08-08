import sqlite3
from datetime import datetime
from typing import Any

from app.config import DATABASE_PATH, DATASET_DIR


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS college_students (
                id INTEGER PRIMARY KEY,
                roll_number TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                age INTEGER,
                email TEXT,
                phone TEXT,
                department TEXT NOT NULL DEFAULT '',
                program TEXT NOT NULL DEFAULT '',
                academic_year TEXT NOT NULL DEFAULT '',
                semester TEXT NOT NULL DEFAULT '',
                section TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS face_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                file_path TEXT NOT NULL UNIQUE,
                sharpness REAL NOT NULL,
                brightness REAL NOT NULL,
                quality_label TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES college_students(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS model_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_path TEXT NOT NULL,
                student_count INTEGER NOT NULL,
                sample_count INTEGER NOT NULL,
                status TEXT NOT NULL,
                notes TEXT,
                trained_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS attendance_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attendance_date TEXT NOT NULL,
                title TEXT NOT NULL,
                department TEXT NOT NULL DEFAULT '',
                program TEXT NOT NULL DEFAULT '',
                academic_year TEXT NOT NULL DEFAULT '',
                semester TEXT NOT NULL DEFAULT '',
                section TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                started_at TEXT NOT NULL,
                ended_at TEXT
            );

            CREATE TABLE IF NOT EXISTS attendance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'present',
                confidence REAL NOT NULL,
                marked_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES attendance_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES college_students(id) ON DELETE CASCADE,
                UNIQUE(session_id, student_id)
            );

            CREATE TABLE IF NOT EXISTS recognition_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                predicted_student_id INTEGER,
                confidence REAL,
                accepted INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES attendance_sessions(id) ON DELETE SET NULL,
                FOREIGN KEY (predicted_student_id) REFERENCES college_students(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_students_group
                ON college_students(department, program, academic_year, semester, section);
            CREATE INDEX IF NOT EXISTS idx_attendance_sessions_date
                ON attendance_sessions(attendance_date);
            CREATE INDEX IF NOT EXISTS idx_attendance_records_session
                ON attendance_records(session_id);
            CREATE INDEX IF NOT EXISTS idx_recognition_events_session
                ON recognition_events(session_id);
            """
        )
        legacy_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='STUDENTS'"
        ).fetchone()
        if legacy_exists:
            legacy_rows = conn.execute("SELECT Id, Name, age FROM STUDENTS").fetchall()
            for row in legacy_rows:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO college_students (
                        id, roll_number, full_name, age, department, program,
                        academic_year, semester, section, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, '', '', '', '', '', ?, ?)
                    """,
                    (
                        row["Id"],
                        f"LEGACY-{row['Id']}",
                        row["Name"],
                        row["age"],
                        now_iso(),
                        now_iso(),
                    ),
                )
        for image_path in DATASET_DIR.glob("user.*.*.jpg"):
            parts = image_path.name.split(".")
            if len(parts) < 4 or not parts[1].isdigit():
                continue
            student_id = int(parts[1])
            student_exists = conn.execute("SELECT id FROM college_students WHERE id = ?", (student_id,)).fetchone()
            if not student_exists:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO face_samples (
                    student_id, file_path, sharpness, brightness, quality_label, captured_at
                )
                VALUES (?, ?, 0, 0, 'Legacy', ?)
                """,
                (student_id, str(image_path), now_iso()),
            )
