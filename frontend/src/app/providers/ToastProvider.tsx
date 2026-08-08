import { CheckCircle2, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { toastTone } from "@/lib/utils";

interface ToastContextValue {
  toast: string;
  setToast: (message: string) => void;
  clearToast: () => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToastState] = useState("");

  const setToast = useCallback((message: string) => {
    setToastState(message);
  }, []);

  const clearToast = useCallback(() => {
    setToastState("");
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToastState(""), 3400);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const value = useMemo(
    () => ({
      toast,
      setToast,
      clearToast
    }),
    [toast, setToast, clearToast]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <Toaster message={toast} onClose={clearToast} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return context;
}

function Toaster({ message, onClose }: { message: string; onClose: () => void }) {
  if (!message) return null;
  const tone = toastTone(message);

  return (
    <div className="toaster-host" aria-live="polite">
      <div className={`toaster toaster-${tone}`} role="status">
        <div className="toaster-icon">{tone === "error" ? <X size={16} /> : <CheckCircle2 size={16} />}</div>
        <p>{message}</p>
        <button className="toaster-close" onClick={onClose} aria-label="Close notification">
          <X size={15} />
        </button>
        <span className="toaster-progress" />
      </div>
    </div>
  );
}
