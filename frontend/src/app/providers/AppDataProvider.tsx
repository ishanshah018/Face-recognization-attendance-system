import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, type AttendanceSession, type Dashboard, type Student } from "@/lib/api";
import { useToast } from "@/app/providers/ToastProvider";
import { getErrorMessage } from "@/lib/utils";

interface AppDataContextValue {
  dashboard: Dashboard | null;
  students: Student[];
  sessions: AttendanceSession[];
  busy: string;
  setBusy: (value: string) => void;
  refresh: () => Promise<void>;
}

const AppDataContext = createContext<AppDataContextValue | null>(null);

export function AppDataProvider({ children }: { children: ReactNode }) {
  const { setToast } = useToast();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [students, setStudents] = useState<Student[]>([]);
  const [sessions, setSessions] = useState<AttendanceSession[]>([]);
  const [busy, setBusy] = useState("");

  const refresh = useCallback(async () => {
    const [dashboardData, studentData, sessionData] = await Promise.all([
      api<Dashboard>("/api/dashboard"),
      api<{ students: Student[] }>("/api/students"),
      api<{ sessions: AttendanceSession[] }>("/api/attendance/sessions")
    ]);
    setDashboard(dashboardData);
    setStudents(studentData.students);
    setSessions(sessionData.sessions);
  }, []);

  useEffect(() => {
    refresh().catch((error) => setToast(getErrorMessage(error, "Failed to load data")));
  }, [refresh, setToast]);

  const value = useMemo(
    () => ({
      dashboard,
      students,
      sessions,
      busy,
      setBusy,
      refresh
    }),
    [dashboard, students, sessions, busy, refresh]
  );

  return <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>;
}

export function useAppData() {
  const context = useContext(AppDataContext);
  if (!context) {
    throw new Error("useAppData must be used within AppDataProvider");
  }
  return context;
}
