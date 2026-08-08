import { CalendarCheck, Loader2, Play, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useAppData } from "@/app/providers/AppDataProvider";
import { useToast } from "@/app/providers/ToastProvider";
import { CameraPanel } from "@/components/camera/CameraPanel";
import { api, type AttendanceSession, type ScanResult } from "@/lib/api";
import { todayIso } from "@/lib/constants";
import { getErrorMessage } from "@/lib/utils";

export function AttendancePage() {
  const today = todayIso();
  const { sessions, refresh, busy, setBusy } = useAppData();
  const { setToast } = useToast();
  const todaySession =
    sessions.find((session) => session.attendance_date === today && session.status === "active") ?? null;
  const [activeSession, setActiveSession] = useState<AttendanceSession | null>(todaySession);
  const [scan, setScan] = useState<ScanResult | null>(null);
  const [sessionLive, setSessionLive] = useState(false);
  const scanningRef = useRef(false);
  const autoRef = useRef<number | null>(null);
  const cameraShotRef = useRef<(() => string | null) | null>(null);

  useEffect(() => {
    const latest = sessions.find((session) => session.attendance_date === today && session.status === "active") ?? null;
    setActiveSession(latest);
    if (!latest) {
      setSessionLive(false);
      setScan(null);
    }
  }, [sessions, today]);

  const scanFace = async (sessionId: number) => {
    if (scanningRef.current) return;
    const capture = cameraShotRef.current;
    if (!capture) return;
    const imageData = capture();
    if (!imageData) return;

    scanningRef.current = true;
    try {
      const result = await api<ScanResult>(`/api/attendance/sessions/${sessionId}/scan-frame`, {
        method: "POST",
        body: JSON.stringify({ image_data: imageData })
      });
      setScan(result);
      if (result.marked) {
        setToast(`${result.student?.full_name ?? "Student"} marked present.`);
        await refresh();
      }
    } catch (error) {
      setToast(getErrorMessage(error, "Scan failed"));
      setSessionLive(false);
    } finally {
      scanningRef.current = false;
    }
  };

  useEffect(() => {
    if (!sessionLive || !activeSession || activeSession.status !== "active") {
      if (autoRef.current) window.clearInterval(autoRef.current);
      autoRef.current = null;
      return;
    }
    autoRef.current = window.setInterval(() => {
      void scanFace(activeSession.id);
    }, 2200);
    return () => {
      if (autoRef.current) window.clearInterval(autoRef.current);
    };
  }, [sessionLive, activeSession]);

  const toggleSession = async () => {
    if (sessionLive && activeSession?.status === "active") {
      setBusy("complete");
      try {
        setSessionLive(false);
        await api(`/api/attendance/sessions/${activeSession.id}/complete`, { method: "POST" });
        setToast("Attendance session completed.");
        setScan(null);
        await refresh();
      } catch (error) {
        setToast(getErrorMessage(error, "Could not complete session"));
      } finally {
        setBusy("");
      }
      return;
    }

    setBusy("session");
    try {
      const payload = await api<{ session: AttendanceSession }>("/api/attendance/sessions", {
        method: "POST",
        body: JSON.stringify({ title: "Daily Attendance", attendance_date: today })
      });
      setActiveSession(payload.session);
      setSessionLive(true);
      setToast(`Attendance started for ${today}.`);
      await refresh();
    } catch (error) {
      setToast(getErrorMessage(error, "Session failed"));
    } finally {
      setBusy("");
    }
  };

  const isLive = sessionLive && activeSession?.status === "active";

  return (
    <section className="attendance-simple">
      <div className="attendance-toolbar panel">
        <div className="attendance-date">
          <CalendarCheck size={18} />
          <div>
            <span>Today</span>
            <strong>{today}</strong>
          </div>
        </div>
        <button
          className={isLive ? "danger-button" : "primary-button"}
          onClick={toggleSession}
          disabled={busy === "session" || busy === "complete"}
        >
          {busy === "session" || busy === "complete" ? (
            <Loader2 className="spin" size={18} />
          ) : isLive ? (
            <Square size={18} />
          ) : (
            <Play size={18} />
          )}
          {isLive ? "Complete Session" : "Start Attendance"}
        </button>
      </div>

      <div className="attendance-stage">
        <CameraPanel
          autoStart={isLive}
          hideControls={isLive}
          idleText={isLive ? "Starting camera…" : "Press Start Attendance to begin."}
          onReady={(capture) => {
            cameraShotRef.current = capture;
          }}
        />

        <div className="panel attendance-result">
          <div className="panel-title">
            <h2>{isLive ? "Live recognition" : "Attendance"}</h2>
            {isLive && <span className="badge good">Scanning</span>}
          </div>
          {scan?.student ? (
            <div className={scan.marked || scan.already_marked ? "scan-result success" : "scan-result"}>
              <strong>{scan.student.full_name}</strong>
              <span>Roll {scan.student.roll_number}</span>
              <span>
                {[scan.student.department, scan.student.academic_year, scan.student.semester, scan.student.section]
                  .filter(Boolean)
                  .join(" · ") || "Student details"}
              </span>
              <small>{scan.reason}</small>
            </div>
          ) : (
            <p className="result-line">
              {isLive
                ? "Looking for a face… student details appear here when recognized."
                : "Start attendance to open the camera and mark students automatically."}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
