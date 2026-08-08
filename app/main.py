from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from app.database import get_connection, init_db, now_iso, rows_to_dicts
from app.schemas import AttendanceSessionIn, CaptureRequest, FrameCaptureRequest, FrameScanRequest, ReportFilters, StudentIn
from app.config import DATASET_DIR, DEFAULT_SAMPLE_TARGET, TRAINING_DATA_PATH
from app.services.face_service import face_service
from app.utils.reports import build_attendance_report, export_attendance_report
from app.validation import (
    assert_can_enroll_face,
    assert_model_ready,
    assert_session_active,
    assert_student_payload,
)


app = FastAPI(title="Face Recognition Attendance API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def cleanup_orphan_face_data() -> None:
    with get_connection() as conn:
        valid_ids = {row["id"] for row in conn.execute("SELECT id FROM college_students").fetchall()}

    removed = 0
    for path in DATASET_DIR.glob("user.*.*.jpg"):
        parts = path.name.split(".")
        if len(parts) < 4 or not parts[1].isdigit():
            continue
        student_id = int(parts[1])
        if student_id in valid_ids:
            continue
        try:
            path.unlink(missing_ok=True)
            removed += 1
        except OSError:
            pass
        with get_connection() as conn:
            conn.execute("DELETE FROM face_samples WHERE file_path = ?", (str(path),))

    if removed:
        with get_connection() as conn:
            remaining = conn.execute("SELECT COUNT(*) AS count FROM face_samples").fetchone()["count"]
        if remaining:
            face_service.train()
        else:
            if TRAINING_DATA_PATH.exists():
                TRAINING_DATA_PATH.unlink()
            face_service.reset_model()


@app.on_event("startup")
def startup() -> None:
    init_db()
    cleanup_orphan_face_data()


def upsert_student(student: StudentIn) -> dict:
    timestamp = now_iso()
    assert_student_payload(student, require_group=True)
    with get_connection() as conn:
        by_roll = conn.execute(
            "SELECT id, roll_number FROM college_students WHERE lower(roll_number) = lower(?)",
            (student.roll_number,),
        ).fetchone()
        if by_roll and student.id and by_roll["id"] != student.id:
            raise HTTPException(
                status_code=400,
                detail=f"Roll number {student.roll_number} is already used by another student.",
            )
        if by_roll and not student.id:
            student = student.model_copy(update={"id": by_roll["id"]})

        if student.id:
            existing = conn.execute("SELECT id FROM college_students WHERE id = ?", (student.id,)).fetchone()
            if existing:
                try:
                    conn.execute(
                        """
                        UPDATE college_students
                        SET roll_number = ?, full_name = ?, age = ?, email = ?, phone = ?,
                            department = ?, program = ?, academic_year = ?, semester = ?,
                            section = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            student.roll_number,
                            student.full_name,
                            student.age,
                            student.email,
                            student.phone,
                            student.department,
                            student.program,
                            student.academic_year,
                            student.semester,
                            student.section,
                            timestamp,
                            student.id,
                        ),
                    )
                except Exception as exc:
                    raise HTTPException(status_code=400, detail=f"Could not update student: {exc}") from exc
            else:
                try:
                    conn.execute(
                        """
                        INSERT INTO college_students (
                            id, roll_number, full_name, age, email, phone, department,
                            program, academic_year, semester, section, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            student.id,
                            student.roll_number,
                            student.full_name,
                            student.age,
                            student.email,
                            student.phone,
                            student.department,
                            student.program,
                            student.academic_year,
                            student.semester,
                            student.section,
                            timestamp,
                            timestamp,
                        ),
                    )
                except Exception as exc:
                    raise HTTPException(status_code=400, detail=f"Could not create student: {exc}") from exc
            student_id = student.id
        else:
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO college_students (
                        roll_number, full_name, age, email, phone, department,
                        program, academic_year, semester, section, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        student.roll_number,
                        student.full_name,
                        student.age,
                        student.email,
                        student.phone,
                        student.department,
                        student.program,
                        student.academic_year,
                        student.semester,
                        student.section,
                        timestamp,
                        timestamp,
                    ),
                )
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Could not create student: {exc}") from exc
            student_id = cursor.lastrowid

        row = conn.execute("SELECT * FROM college_students WHERE id = ?", (student_id,)).fetchone()
        return dict(row)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "time": now_iso()}


@app.get("/api/dashboard")
def dashboard() -> dict:
    today = date.today().isoformat()
    with get_connection() as conn:
        students = conn.execute("SELECT COUNT(*) AS count FROM college_students WHERE status = 'active'").fetchone()["count"]
        sessions_today = conn.execute(
            "SELECT COUNT(*) AS count FROM attendance_sessions WHERE attendance_date = ?",
            (today,),
        ).fetchone()["count"]
        present_today = conn.execute(
            """
            SELECT COUNT(DISTINCT ar.student_id) AS count
            FROM attendance_records ar
            JOIN attendance_sessions s ON s.id = ar.session_id
            WHERE s.attendance_date = ?
            """,
            (today,),
        ).fetchone()["count"]
        recent_sessions = rows_to_dicts(
            conn.execute(
                """
                SELECT s.*, COUNT(ar.id) AS present_count
                FROM attendance_sessions s
                LEFT JOIN attendance_records ar ON ar.session_id = s.id
                GROUP BY s.id
                ORDER BY s.started_at DESC
                LIMIT 6
                """
            ).fetchall()
        )
    return {
        "students": students,
        "sessions_today": sessions_today,
        "present_today": present_today,
        "recent_sessions": recent_sessions,
    }


@app.get("/api/students")
def list_students(search: str = "", status: str = "active") -> dict:
    clauses = ["status = ?"]
    values: list[str] = [status]
    if search:
        clauses.append("(roll_number LIKE ? OR full_name LIKE ? OR department LIKE ?)")
        like = f"%{search}%"
        values.extend([like, like, like])
    with get_connection() as conn:
        rows = rows_to_dicts(
            conn.execute(
                f"""
                SELECT s.*, COUNT(fs.id) AS sample_count
                FROM college_students s
                LEFT JOIN face_samples fs ON fs.student_id = s.id
                WHERE {' AND '.join(clauses)}
                GROUP BY s.id
                ORDER BY s.created_at DESC
                """,
                values,
            ).fetchall()
        )
    return {"students": rows}


@app.post("/api/students")
def save_student(student: StudentIn) -> dict:
    try:
        return {"student": upsert_student(student)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/students/{student_id}")
def delete_student(student_id: int) -> dict:
    with get_connection() as conn:
        student = conn.execute("SELECT * FROM college_students WHERE id = ?", (student_id,)).fetchone()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found.")

        sample_rows = conn.execute(
            "SELECT file_path FROM face_samples WHERE student_id = ?",
            (student_id,),
        ).fetchall()
        file_paths = {Path(row["file_path"]) for row in sample_rows}
        for path in DATASET_DIR.glob(f"user.{student_id}.*.jpg"):
            file_paths.add(path)
        for path in file_paths:
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                pass

        conn.execute("DELETE FROM attendance_records WHERE student_id = ?", (student_id,))
        conn.execute("DELETE FROM face_samples WHERE student_id = ?", (student_id,))
        conn.execute("DELETE FROM recognition_events WHERE predicted_student_id = ?", (student_id,))
        conn.execute("DELETE FROM STUDENTS WHERE Id = ?", (student_id,))
        conn.execute("DELETE FROM college_students WHERE id = ?", (student_id,))

        remaining_samples = conn.execute("SELECT COUNT(*) AS count FROM face_samples").fetchone()["count"]
        if remaining_samples:
            result = face_service.train()
            conn.execute(
                """
                INSERT INTO model_versions (model_path, student_count, sample_count, status, notes, trained_at)
                VALUES (?, ?, ?, 'ready', ?, ?)
                """,
                (
                    result["model_path"],
                    result["student_count"],
                    result["sample_count"],
                    "Model retrained after deleting a student.",
                    now_iso(),
                ),
            )
        else:
            if TRAINING_DATA_PATH.exists():
                TRAINING_DATA_PATH.unlink()
            face_service.reset_model()
            conn.execute("DELETE FROM model_versions")
    return {"deleted": True, "student_id": student_id}


@app.post("/api/enrollment/capture")
def enroll_and_capture(payload: CaptureRequest) -> dict:
    try:
        assert_can_enroll_face(payload.student, payload.sample_target)
        student = upsert_student(payload.student)
        result = face_service.capture_samples(student["id"], payload.sample_target)
        with get_connection() as conn:
            for sample in result["samples"]:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO face_samples (
                        student_id, file_path, sharpness, brightness, quality_label, captured_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        student["id"],
                        sample["file_path"],
                        sample["sharpness"],
                        sample["brightness"],
                        sample["quality_label"],
                        now_iso(),
                    ),
                )
        return {"student": student, "capture": result}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/enrollment/capture-frame")
def enroll_and_capture_frame(payload: FrameCaptureRequest) -> dict:
    try:
        assert_can_enroll_face(payload.student, payload.sample_target)
        student = upsert_student(payload.student)
        frame = face_service.frame_from_data_url(payload.image_data)
        result = face_service.capture_sample_from_frame(student["id"], frame)
        with get_connection() as conn:
            for sample in result["samples"]:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO face_samples (
                        student_id, file_path, sharpness, brightness, quality_label, captured_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        student["id"],
                        sample["file_path"],
                        sample["sharpness"],
                        sample["brightness"],
                        sample["quality_label"],
                        now_iso(),
                    ),
                )
        return {"student": student, "capture": result}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/enrollment/status")
def enrollment_status(roll_number: str = Query(min_length=1), student_id: int | None = None) -> dict:
    with get_connection() as conn:
        student = None
        if student_id:
            student = conn.execute("SELECT * FROM college_students WHERE id = ?", (student_id,)).fetchone()
        if not student:
            student = conn.execute(
                "SELECT * FROM college_students WHERE lower(roll_number) = lower(?)",
                (roll_number.strip(),),
            ).fetchone()
        if not student:
            return {
                "exists": False,
                "registered": False,
                "sample_count": 0,
                "can_enroll": True,
                "student": None,
            }
        samples = conn.execute(
            "SELECT COUNT(*) AS count FROM face_samples WHERE student_id = ?",
            (student["id"],),
        ).fetchone()["count"]
        registered = samples >= DEFAULT_SAMPLE_TARGET
        return {
            "exists": True,
            "registered": registered,
            "sample_count": samples,
            "can_enroll": not registered,
            "student": dict(student),
        }


@app.post("/api/model/train")
def train_model() -> dict:
    try:
        with get_connection() as conn:
            samples = conn.execute("SELECT COUNT(*) AS count FROM face_samples").fetchone()["count"]
        if samples < 1:
            raise HTTPException(status_code=400, detail="No face photos found. Capture a face first.")
        result = face_service.train()
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO model_versions (model_path, student_count, sample_count, status, notes, trained_at)
                VALUES (?, ?, ?, 'ready', ?, ?)
                """,
                (
                    result["model_path"],
                    result["student_count"],
                    result["sample_count"],
                    "LBPH model trained from validated local samples.",
                    now_iso(),
                ),
            )
        return {"model": result}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/camera/stream")
def camera_stream() -> StreamingResponse:
    return StreamingResponse(face_service.stream_frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.post("/api/camera/stop")
def stop_camera() -> dict:
    face_service.stop_camera()
    return {"status": "stopped"}


@app.post("/api/attendance/sessions")
def create_attendance_session(payload: AttendanceSessionIn | None = None) -> dict:
    timestamp = now_iso()
    attendance_date = date.today().isoformat()
    title = "Daily Attendance"
    if payload and payload.title:
        title = payload.title.strip() or title
    assert_model_ready()
    with get_connection() as conn:
        active_students = conn.execute(
            "SELECT COUNT(*) AS count FROM college_students WHERE status = 'active'"
        ).fetchone()["count"]
        if active_students < 1:
            raise HTTPException(status_code=400, detail="Register at least one student before starting attendance.")

        # Finish any previous live session so admin can start attendance again today.
        conn.execute(
            """
            UPDATE attendance_sessions
            SET status = 'completed', ended_at = ?
            WHERE attendance_date = ? AND status = 'active'
            """,
            (timestamp, attendance_date),
        )

        cursor = conn.execute(
            """
            INSERT INTO attendance_sessions (
                attendance_date, title, department, program, academic_year,
                semester, section, status, started_at
            )
            VALUES (?, ?, '', '', '', '', '', 'active', ?)
            """,
            (attendance_date, title, timestamp),
        )
        row = conn.execute("SELECT * FROM attendance_sessions WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return {"session": dict(row)}


@app.get("/api/attendance/sessions")
def list_attendance_sessions() -> dict:
    with get_connection() as conn:
        rows = rows_to_dicts(
            conn.execute(
                """
                SELECT s.*, COUNT(ar.id) AS present_count
                FROM attendance_sessions s
                LEFT JOIN attendance_records ar ON ar.session_id = s.id
                GROUP BY s.id
                ORDER BY s.started_at DESC
                LIMIT 30
                """
            ).fetchall()
        )
    return {"sessions": rows}


def apply_recognition_result(conn, session, session_id: int, result) -> dict:
    student = None
    accepted = result.accepted
    reason = result.reason
    predicted_id = result.student_id if result.student_id else None

    if predicted_id:
        student = conn.execute(
            "SELECT * FROM college_students WHERE id = ? AND status = 'active'",
            (predicted_id,),
        ).fetchone()
        if not student:
            accepted = False
            reason = "Face matched an old/deleted student. Re-register faces if needed."
            predicted_id = None
        elif not accepted:
            student = None

    if accepted and predicted_id and not student:
        accepted = False
        reason = "Matched student is inactive or missing."
        predicted_id = None

    conn.execute(
        """
        INSERT INTO recognition_events (
            session_id, predicted_student_id, confidence, accepted, reason, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (session_id, predicted_id, result.confidence, 1 if accepted else 0, reason, now_iso()),
    )

    marked = False
    already_marked = False
    if accepted and student and result.confidence is not None:
        existing = conn.execute(
            """
            SELECT ar.id
            FROM attendance_records ar
            JOIN attendance_sessions s ON s.id = ar.session_id
            WHERE ar.student_id = ?
              AND s.attendance_date = ?
            LIMIT 1
            """,
            (student["id"], session["attendance_date"]),
        ).fetchone()
        if existing:
            already_marked = True
            reason = "Already marked present today."
        else:
            conn.execute(
                """
                INSERT INTO attendance_records (session_id, student_id, status, confidence, marked_at)
                VALUES (?, ?, 'present', ?, ?)
                """,
                (session_id, student["id"], result.confidence, now_iso()),
            )
            marked = True
            reason = "Marked present."

    present_count = conn.execute(
        "SELECT COUNT(*) AS count FROM attendance_records WHERE session_id = ?",
        (session_id,),
    ).fetchone()["count"]

    return {
        "accepted": accepted,
        "marked": marked,
        "already_marked": already_marked,
        "reason": reason,
        "student": dict(student) if student else None,
        "confidence": round(result.confidence, 2) if result.confidence is not None else None,
        "face_count": result.face_count,
        "present_count": present_count,
    }


@app.post("/api/attendance/sessions/{session_id}/scan")
def scan_attendance(session_id: int) -> dict:
    assert_model_ready()
    with get_connection() as conn:
        session = assert_session_active(
            conn.execute("SELECT * FROM attendance_sessions WHERE id = ?", (session_id,)).fetchone()
        )

    result = face_service.recognize_current_face()
    with get_connection() as conn:
        return apply_recognition_result(conn, session, session_id, result)


@app.post("/api/attendance/sessions/{session_id}/scan-frame")
def scan_attendance_frame(session_id: int, payload: FrameScanRequest) -> dict:
    assert_model_ready()
    with get_connection() as conn:
        session = assert_session_active(
            conn.execute("SELECT * FROM attendance_sessions WHERE id = ?", (session_id,)).fetchone()
        )

    try:
        frame = face_service.frame_from_data_url(payload.image_data)
        result = face_service.recognize_frame(frame)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with get_connection() as conn:
        return apply_recognition_result(conn, session, session_id, result)


@app.post("/api/attendance/sessions/{session_id}/complete")
def complete_attendance_session(session_id: int) -> dict:
    with get_connection() as conn:
        session = conn.execute("SELECT * FROM attendance_sessions WHERE id = ?", (session_id,)).fetchone()
        assert_session_active(session)
        conn.execute(
            "UPDATE attendance_sessions SET status = 'completed', ended_at = ? WHERE id = ?",
            (now_iso(), session_id),
        )
    return {"status": "completed"}


@app.get("/api/reports")
def attendance_report(
    preset: str = Query(default="today"),
    start_date: date | None = None,
    end_date: date | None = None,
    department: str = "",
    program: str = "",
    academic_year: str = "",
    semester: str = "",
    section: str = "",
) -> dict:
    try:
        filters = ReportFilters(
            preset=preset,
            start_date=start_date,
            end_date=end_date,
            department=department,
            program=program,
            academic_year=academic_year,
            semester=semester,
            section=section,
        )
        return build_attendance_report(filters)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/reports/export")
def export_report(
    preset: str = Query(default="today"),
    start_date: date | None = None,
    end_date: date | None = None,
    department: str = "",
    program: str = "",
    academic_year: str = "",
    semester: str = "",
    section: str = "",
) -> FileResponse:
    try:
        filters = ReportFilters(
            preset=preset,
            start_date=start_date,
            end_date=end_date,
            department=department,
            program=program,
            academic_year=academic_year,
            semester=semester,
            section=section,
        )
        path = export_attendance_report(filters)
        return FileResponse(path, filename=path.name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
