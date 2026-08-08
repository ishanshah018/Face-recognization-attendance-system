import { Loader2, Trash2, X } from "lucide-react";
import type { ReactNode } from "react";

interface ConfirmModalProps {
  title: string;
  children: ReactNode;
  confirmLabel?: string;
  busy?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmModal({
  title,
  children,
  confirmLabel = "Confirm",
  busy = false,
  onCancel,
  onConfirm
}: ConfirmModalProps) {
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card">
        <div className="panel-title">
          <h2>{title}</h2>
          <button className="icon-button" onClick={onCancel} disabled={busy}>
            <X size={16} />
          </button>
        </div>
        <div className="modal-copy">{children}</div>
        <div className="actions">
          <button className="secondary-button" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button className="danger-button" onClick={onConfirm} disabled={busy}>
            {busy ? <Loader2 className="spin" size={18} /> : <Trash2 size={18} />}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
