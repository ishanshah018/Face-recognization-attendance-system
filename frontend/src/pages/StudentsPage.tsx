import { Search, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useAppData } from "@/app/providers/AppDataProvider";
import { useToast } from "@/app/providers/ToastProvider";
import { ConfirmModal } from "@/components/ui/ConfirmModal";
import { EmptyRow } from "@/components/ui/EmptyRow";
import { api, type Student } from "@/lib/api";
import { getErrorMessage } from "@/lib/utils";

export function StudentsPage() {
  const { students, refresh } = useAppData();
  const { setToast } = useToast();
  const [query, setQuery] = useState("");
  const [pendingDelete, setPendingDelete] = useState<Student | null>(null);
  const [deleting, setDeleting] = useState(false);

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return students.filter((student) =>
      [student.roll_number, student.full_name, student.department, student.program, student.section]
        .join(" ")
        .toLowerCase()
        .includes(q)
    );
  }, [students, query]);

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await api(`/api/students/${pendingDelete.id}`, { method: "DELETE" });
      setToast(`${pendingDelete.full_name} deleted. All related data removed.`);
      setPendingDelete(null);
      await refresh();
    } catch (error) {
      setToast(getErrorMessage(error, "Delete failed"));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <section className="panel wide">
      <div className="toolbar">
        <div className="search-box">
          <Search size={17} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search students" />
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Roll</th>
              <th>Name</th>
              <th>Department</th>
              <th>Program</th>
              <th>Year</th>
              <th>Sem</th>
              <th>Section</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((student) => (
              <tr key={student.id}>
                <td>{student.roll_number}</td>
                <td>{student.full_name}</td>
                <td>{student.department || "-"}</td>
                <td>{student.program || "-"}</td>
                <td>{student.academic_year || "-"}</td>
                <td>{student.semester || "-"}</td>
                <td>{student.section || "-"}</td>
                <td>
                  <button
                    className="icon-button danger-icon"
                    title="Delete student"
                    onClick={() => setPendingDelete(student)}
                  >
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
            {!filtered.length && <EmptyRow columns={8} text="No students found." />}
          </tbody>
        </table>
      </div>

      {pendingDelete && (
        <ConfirmModal
          title="Delete student?"
          confirmLabel="Delete permanently"
          busy={deleting}
          onCancel={() => setPendingDelete(null)}
          onConfirm={confirmDelete}
        >
          This permanently removes <strong>{pendingDelete.full_name}</strong> ({pendingDelete.roll_number}), including
          attendance records, face photos, and retrains the recognition model.
        </ConfirmModal>
      )}
    </section>
  );
}
