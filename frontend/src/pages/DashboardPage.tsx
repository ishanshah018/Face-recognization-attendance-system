import { useState } from "react";
import { Activity, CalendarCheck, CheckCircle2, Trash2, Users } from "lucide-react";
import { useAppData } from "@/app/providers/AppDataProvider";
import { useToast } from "@/app/providers/ToastProvider";
import { EmptyRow } from "@/components/ui/EmptyRow";
import { ConfirmModal } from "@/components/ui/ConfirmModal";
import { api } from "@/lib/api";
import { getErrorMessage } from "@/lib/utils";

export function DashboardPage() {
  const { dashboard, sessions, refresh } = useAppData();
  const { setToast } = useToast();
  
  const [showConfirm, setShowConfirm] = useState(false);
  const [clearing, setClearing] = useState(false);

  const stats = [
    { label: "Active students", value: dashboard?.students ?? "-", icon: Users },
    { label: "Sessions today", value: dashboard?.sessions_today ?? "-", icon: CalendarCheck },
    { label: "Present today", value: dashboard?.present_today ?? "-", icon: CheckCircle2 }
  ];

  const handleClearAll = async () => {
    setClearing(true);
    try {
      await api("/api/system/clear", { method: "POST" });
      setToast("System successfully reset. All data cleared.");
      setShowConfirm(false);
      await refresh();
    } catch (error) {
      setToast(getErrorMessage(error, "Failed to reset system"));
    } finally {
      setClearing(false);
    }
  };

  return (
    <section className="content-grid">
      <div className="stats-grid three">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <article className="stat-card" key={stat.label}>
              <Icon size={20} />
              <span>{stat.label}</span>
              <strong>{stat.value}</strong>
            </article>
          );
        })}
      </div>
      
      <div className="panel wide">
        <div className="panel-title">
          <h2>Recent Sessions</h2>
          <Activity size={18} />
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Title</th>
                <th>Department</th>
                <th>Section</th>
                <th>Present</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {sessions.slice(0, 8).map((session) => (
                <tr key={session.id}>
                  <td>{session.attendance_date}</td>
                  <td>{session.title}</td>
                  <td>{session.department || "-"}</td>
                  <td>{session.section || "-"}</td>
                  <td>{session.present_count ?? 0}</td>
                  <td>
                    <span className="badge">{session.status}</span>
                  </td>
                </tr>
              ))}
              {!sessions.length && <EmptyRow columns={6} text="No attendance sessions yet." />}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "24px", gridColumn: "1 / -1" }}>
        <button className="danger-button" onClick={() => setShowConfirm(true)}>
          <Trash2 size={16} style={{ marginRight: "8px" }} />
          Remove All Data
        </button>
      </div>

      {showConfirm && (
        <ConfirmModal
          title="Reset database and datasets?"
          confirmLabel="Reset Everything"
          busy={clearing}
          onCancel={() => setShowConfirm(false)}
          onConfirm={handleClearAll}
        >
          Are you absolutely sure you want to delete all students, face datasets, trained models, and attendance history? This action <strong>cannot be undone</strong> and will clear everything to start from scratch.
        </ConfirmModal>
      )}
    </section>
  );
}
