import { RefreshCw } from "lucide-react";
import { useLocation } from "react-router-dom";
import { useAppData } from "@/app/providers/AppDataProvider";
import { NAV_ITEMS } from "@/config/navigation";
import { getErrorMessage } from "@/lib/utils";
import { useToast } from "@/app/providers/ToastProvider";

export function Topbar() {
  const location = useLocation();
  const { refresh } = useAppData();
  const { setToast } = useToast();
  const title = NAV_ITEMS.find((item) =>
    item.path === "/" ? location.pathname === "/" : location.pathname.startsWith(item.path)
  )?.label;

  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">Admin Console</p>
        <h1>{title ?? "Admin"}</h1>
      </div>
      <button
        className="icon-button"
        onClick={() => {
          refresh().catch((error) => setToast(getErrorMessage(error, "Refresh failed")));
        }}
        title="Refresh data"
      >
        <RefreshCw size={18} />
      </button>
    </header>
  );
}
