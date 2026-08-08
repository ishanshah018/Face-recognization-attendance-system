from __future__ import annotations

import re
import sqlite3

from fastapi import HTTPException

from app.config import DEFAULT_SAMPLE_TARGET, TRAINING_DATA_PATH
from app.database import get_connection
from app.schemas import StudentIn

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^[0-9+\-\s()]{7,20}$")
ROLL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-_/. ]{0,39}$")


def validate_optional_contact(email: str | None, phone: str | None) -> None:
    if email:
        if not EMAIL_RE.match(email):
            raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if phone:
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 7 or not PHONE_RE.match(phone):
            raise HTTPException(status_code=400, detail="Enter a valid phone number.")


def find_student_match(conn: sqlite3.Connection, student: StudentIn) -> sqlite3.Row | None:
    if student.id:
        row = conn.execute("SELECT * FROM college_students WHERE id = ?", (student.id,)).fetchone()
        if row:
            return row
    return conn.execute(
        "SELECT * FROM college_students WHERE lower(roll_number) = lower(?)",
        (student.roll_number,),
    ).fetchone()


def sample_count_for(conn: sqlite3.Connection, student_id: int) -> int:
    return conn.execute(
        "SELECT COUNT(*) AS count FROM face_samples WHERE student_id = ?",
        (student_id,),
    ).fetchone()["count"]


def assert_student_payload(student: StudentIn, *, require_group: bool = True) -> None:
    if not student.roll_number:
        raise HTTPException(status_code=400, detail="Roll number is required.")
    if not ROLL_RE.match(student.roll_number):
        raise HTTPException(status_code=400, detail="Roll number has invalid characters.")
    if not student.full_name or len(student.full_name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Full name is required.")
    if require_group:
        if not student.department:
            raise HTTPException(status_code=400, detail="Department is required.")
        if not student.section:
            raise HTTPException(status_code=400, detail="Section is required.")
        if not student.academic_year:
            raise HTTPException(status_code=400, detail="Academic year is required.")
        if not student.semester:
            raise HTTPException(status_code=400, detail="Semester is required.")
    validate_optional_contact(student.email, student.phone)


def assert_can_enroll_face(student: StudentIn, sample_target: int = DEFAULT_SAMPLE_TARGET) -> sqlite3.Row | None:
    """Block re-registration once a student already has a complete face enrollment."""
    assert_student_payload(student, require_group=True)
    with get_connection() as conn:
        existing = find_student_match(conn, student)
        if not existing:
            return None

        if student.id and existing["id"] != student.id:
            raise HTTPException(
                status_code=400,
                detail=f"Roll number {student.roll_number} already belongs to another student.",
            )

        if student.roll_number and existing["roll_number"].lower() != student.roll_number.lower():
            # Same ID, different roll colliding with uniqueness elsewhere is handled on write.
            pass

        samples = sample_count_for(conn, existing["id"])
        if samples >= sample_target:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Face already registered for {existing['full_name']} "
                    f"({existing['roll_number']}). Delete the student to register again."
                ),
            )
        return existing


def assert_model_ready() -> None:
    if not TRAINING_DATA_PATH.exists():
        raise HTTPException(
            status_code=400,
            detail="Model is not trained yet. Register at least one student face first.",
        )


def assert_session_active(session: sqlite3.Row | None) -> sqlite3.Row:
    if not session:
        raise HTTPException(status_code=404, detail="Attendance session not found.")
    if session["status"] != "active":
        raise HTTPException(status_code=400, detail="This attendance session is already completed.")
    return session
