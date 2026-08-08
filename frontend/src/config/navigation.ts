import {
  Camera,
  Download,
  LayoutDashboard,
  type LucideIcon,
  UserPlus,
  Users
} from "lucide-react";

export interface NavItem {
  path: string;
  label: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { path: "/", label: "Dashboard", icon: LayoutDashboard },
  { path: "/students", label: "Students", icon: Users },
  { path: "/enroll", label: "Register Face", icon: UserPlus },
  { path: "/attendance", label: "Attendance", icon: Camera },
  { path: "/reports", label: "Reports", icon: Download }
];
