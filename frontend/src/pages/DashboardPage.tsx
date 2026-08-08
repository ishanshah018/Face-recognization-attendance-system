import { Activity, CalendarCheck, CheckCircle2, Users } from "lucide-react";
import { useAppData } from "@/app/providers/AppDataProvider";
import { EmptyRow } from "@/components/ui/EmptyRow";

export function DashboardPage() {
  const { dashboard, sessions } = useAppData();

  const stats = [
    { label: "Active students", value: dashboard?.students ?? "-", icon: Users },
    { label: "Sessions today", value: dashboard?.sessions_today ?? "-", icon: CalendarCheck },
    { label: "Present today", value: dashboard?.present_today ?? "-", icon: CheckCircle2 }
  ];

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
    </section>
  );
}
