import { Download, Loader2, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { useToast } from "@/app/providers/ToastProvider";
import { EmptyRow } from "@/components/ui/EmptyRow";
import { Field } from "@/components/ui/Field";
import { api, buildQuery, type Report } from "@/lib/api";
import { getErrorMessage } from "@/lib/utils";
import { validateReportFilters } from "@/lib/validation";

export function ReportsPage() {
  const { setToast } = useToast();
  const [filters, setFilters] = useState({
    preset: "today",
    start_date: "",
    end_date: "",
    department: "",
    program: "",
    academic_year: "",
    semester: "",
    section: ""
  });
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);

  const query = buildQuery(filters);

  const loadReport = async () => {
    const filterError = validateReportFilters(filters);
    if (filterError) {
      setToast(filterError);
      return;
    }
    setLoading(true);
    try {
      setReport(await api<Report>(`/api/reports?${query}`));
    } catch (error) {
      setToast(getErrorMessage(error, "Report failed"));
    } finally {
      setLoading(false);
    }
  };

  const exportExcel = () => {
    const filterError = validateReportFilters(filters);
    if (filterError) {
      setToast(filterError);
      return;
    }
    window.location.href = `/api/reports/export?${query}`;
  };

  useEffect(() => {
    void loadReport();
  }, []);

  return (
    <section className="panel wide">
      <div className="report-filters">
        <label>
          Range
          <select value={filters.preset} onChange={(event) => setFilters({ ...filters, preset: event.target.value })}>
            <option value="today">Today</option>
            <option value="this_month">This month</option>
            <option value="last_month">Last month</option>
            <option value="this_year">This year</option>
            <option value="last_year">Last year</option>
            <option value="custom">Custom</option>
          </select>
        </label>
        {filters.preset === "custom" && (
          <>
            <Field
              label="Start"
              type="date"
              value={filters.start_date}
              onChange={(value) => setFilters({ ...filters, start_date: value })}
            />
            <Field
              label="End"
              type="date"
              value={filters.end_date}
              onChange={(value) => setFilters({ ...filters, end_date: value })}
            />
          </>
        )}
        <Field
          label="Department"
          value={filters.department}
          onChange={(value) => setFilters({ ...filters, department: value })}
        />
        <Field
          label="Year"
          value={filters.academic_year}
          onChange={(value) => setFilters({ ...filters, academic_year: value })}
        />
        <Field
          label="Semester"
          value={filters.semester}
          onChange={(value) => setFilters({ ...filters, semester: value })}
        />
        <Field label="Section" value={filters.section} onChange={(value) => setFilters({ ...filters, section: value })} />
        <button className="primary-button" onClick={loadReport} disabled={loading}>
          {loading ? <Loader2 className="spin" size={18} /> : <Search size={18} />}
          Apply
        </button>
        <button className="secondary-button" onClick={exportExcel}>
          <Download size={18} />
          Excel
        </button>
      </div>
      {report && (
        <>
          <div className="stats-grid compact">
            <article className="stat-card">
              <span>Sessions</span>
              <strong>{report.summary.sessions}</strong>
            </article>
            <article className="stat-card">
              <span>Present</span>
              <strong>{report.summary.present}</strong>
            </article>
            <article className="stat-card">
              <span>Absent</span>
              <strong>{report.summary.absent}</strong>
            </article>
            <article className="stat-card">
              <span>Total Rows</span>
              <strong>{report.summary.total}</strong>
            </article>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Roll</th>
                  <th>Name</th>
                  <th>Department</th>
                  <th>Section</th>
                  <th>Status</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {report.rows.map((row, index) => (
                  <tr key={`${row.date}-${row.roll_number}-${index}`}>
                    <td>{row.date}</td>
                    <td>{row.roll_number}</td>
                    <td>{row.full_name}</td>
                    <td>{row.department || "-"}</td>
                    <td>{row.section || "-"}</td>
                    <td>
                      <span className={row.status === "Present" ? "badge good" : "badge muted"}>{row.status}</span>
                    </td>
                    <td>{row.confidence || "-"}</td>
                  </tr>
                ))}
                {!report.rows.length && <EmptyRow columns={7} text="No report rows for this filter." />}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
