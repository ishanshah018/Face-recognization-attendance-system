import { Camera, Loader2, UserPlus } from "lucide-react";
import { useMemo, useState } from "react";
import { useAppData } from "@/app/providers/AppDataProvider";
import { useToast } from "@/app/providers/ToastProvider";
import { CameraPanel } from "@/components/camera/CameraPanel";
import { Field } from "@/components/ui/Field";
import { api, type Student, type StudentPayload } from "@/lib/api";
import { blankStudent, FACE_SAMPLE_TARGET } from "@/lib/constants";
import { getErrorMessage, wait } from "@/lib/utils";
import { validateStudentForm } from "@/lib/validation";

export function EnrollPage() {
  const { students, refresh, busy, setBusy } = useAppData();
  const { setToast } = useToast();
  const [student, setStudent] = useState<StudentPayload>({ ...blankStudent });
  const [lastCapture, setLastCapture] = useState("");
  const [cameraShot, setCameraShot] = useState<(() => string | null) | null>(null);

  const update = (key: keyof StudentPayload, value: string) => {
    setStudent((current) => ({
      ...current,
      [key]: key === "age" || key === "id" ? (value ? Number(value) : null) : value
    }));
  };

  const formReady = useMemo(() => validateStudentForm(student) === null, [student]);

  const capture = async () => {
    const formError = validateStudentForm(student);
    if (formError) {
      setToast(formError);
      return;
    }
    if (!cameraShot) {
      setToast("Start the camera first.");
      return;
    }

    setBusy("capture");
    setLastCapture("");
    try {
      const status = await api<{
        registered: boolean;
        can_enroll: boolean;
        student: Student | null;
        sample_count: number;
      }>(
        `/api/enrollment/status?roll_number=${encodeURIComponent(student.roll_number)}${
          student.id ? `&student_id=${student.id}` : ""
        }`
      );
      if (!status.can_enroll || status.registered) {
        const name = status.student?.full_name ?? student.full_name;
        const roll = status.student?.roll_number ?? student.roll_number;
        throw new Error(`Face already registered for ${name} (${roll}). Delete the student to register again.`);
      }

      const localMatch = students.find(
        (item) =>
          item.roll_number.toLowerCase() === student.roll_number.trim().toLowerCase() ||
          (student.id != null && item.id === student.id)
      );
      if (localMatch && (localMatch.sample_count ?? 0) >= FACE_SAMPLE_TARGET) {
        throw new Error(
          `Face already registered for ${localMatch.full_name} (${localMatch.roll_number}). Delete the student to register again.`
        );
      }

      let captured = 0;
      let enrolledStudent = student;
      for (let attempt = 0; attempt < FACE_SAMPLE_TARGET * 4 && captured < FACE_SAMPLE_TARGET; attempt += 1) {
        const imageData = cameraShot();
        if (!imageData) throw new Error("Camera frame is not ready yet.");
        const payload = await api<{
          student: Student;
          capture: { captured: number; skipped: number; last_reason: string; success: boolean };
        }>("/api/enrollment/capture-frame", {
          method: "POST",
          body: JSON.stringify({
            student: enrolledStudent,
            sample_target: FACE_SAMPLE_TARGET,
            image_data: imageData
          })
        });
        enrolledStudent = { ...enrolledStudent, id: payload.student.id };
        captured += payload.capture.captured;
        await wait(120);
      }

      if (captured < FACE_SAMPLE_TARGET) {
        setLastCapture(`Captured ${captured} photos. Adjust face and try again.`);
        setToast(`Only ${captured} photos saved. Try again.`);
        return;
      }

      setBusy("train");
      setLastCapture("Face registered. Training…");
      await api("/api/model/train", { method: "POST" });
      setLastCapture("Face registered and model trained.");
      setToast("Trained");
      setStudent({ ...blankStudent });
      await refresh();
    } catch (error) {
      setToast(getErrorMessage(error, "Capture failed"));
    } finally {
      setBusy("");
    }
  };

  return (
    <section className="split-layout">
      <div className="panel form-panel">
        <div className="panel-title">
          <h2>Student Details</h2>
          <UserPlus size={18} />
        </div>
        <div className="form-grid">
          <Field label="Student ID" value={student.id ?? ""} onChange={(value) => update("id", value)} type="number" />
          <Field label="Roll Number" value={student.roll_number} onChange={(value) => update("roll_number", value)} required />
          <Field label="Full Name" value={student.full_name} onChange={(value) => update("full_name", value)} required />
          <Field label="Age" value={student.age ?? ""} onChange={(value) => update("age", value)} type="number" />
          <Field label="Email" value={student.email ?? ""} onChange={(value) => update("email", value)} />
          <Field label="Phone" value={student.phone ?? ""} onChange={(value) => update("phone", value)} />
          <Field label="Department" value={student.department} onChange={(value) => update("department", value)} required />
          <Field label="Program" value={student.program} onChange={(value) => update("program", value)} />
          <Field
            label="Academic Year"
            value={student.academic_year}
            onChange={(value) => update("academic_year", value)}
            required
          />
          <Field label="Semester" value={student.semester} onChange={(value) => update("semester", value)} required />
          <Field label="Section" value={student.section} onChange={(value) => update("section", value)} required />
        </div>
        <div className="actions">
          <button
            className="primary-button"
            onClick={capture}
            disabled={!formReady || busy === "capture" || busy === "train"}
            title={formReady ? "Capture face" : "Fill all required student details first"}
          >
            {busy === "capture" || busy === "train" ? <Loader2 className="spin" size={18} /> : <Camera size={18} />}
            {busy === "train" ? "Training…" : "Capture Face"}
          </button>
        </div>
        {lastCapture && <p className="result-line">{lastCapture}</p>}
      </div>
      <CameraPanel onReady={(captureFn) => setCameraShot(captureFn ? () => captureFn : null)} />
    </section>
  );
}
