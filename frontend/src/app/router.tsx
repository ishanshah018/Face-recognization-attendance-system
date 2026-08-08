import { Navigate, useRoutes } from "react-router-dom";
import { AppLayout } from "@/layouts/AppLayout";
import { AttendancePage } from "@/pages/AttendancePage";
import { DashboardPage } from "@/pages/DashboardPage";
import { EnrollPage } from "@/pages/EnrollPage";
import { ReportsPage } from "@/pages/ReportsPage";
import { StudentsPage } from "@/pages/StudentsPage";

export function AppRouter() {
  return useRoutes([
    {
      path: "/",
      element: <AppLayout />,
      children: [
        { index: true, element: <DashboardPage /> },
        { path: "students", element: <StudentsPage /> },
        { path: "enroll", element: <EnrollPage /> },
        { path: "attendance", element: <AttendancePage /> },
        { path: "reports", element: <ReportsPage /> },
        { path: "*", element: <Navigate to="/" replace /> }
      ]
    }
  ]);
}
