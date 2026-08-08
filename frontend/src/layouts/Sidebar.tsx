import { GraduationCap, ShieldCheck } from "lucide-react";
import { NavLink } from "react-router-dom";
import { NAV_ITEMS } from "@/config/navigation";

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">
          <GraduationCap size={22} />
        </div>
        <div>
          <strong>Face Attendance</strong>
          <span>College Admin</span>
        </div>
      </div>
      <nav className="nav">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}
              title={item.label}
            >
              <Icon size={19} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
      <div className="system-pill">
        <ShieldCheck size={17} />
        <span>Local SQLite + OpenCV</span>
      </div>
    </aside>
  );
}
