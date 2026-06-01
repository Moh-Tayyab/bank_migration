"use client";
import Icon from "./Icon";

interface ConfirmationDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "warning" | "info";
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmationDialog({ open, title, message, confirmLabel = "Confirm", cancelLabel = "Cancel", variant = "warning", onConfirm, onCancel }: ConfirmationDialogProps) {
  if (!open) return null;

  const iconMap = { danger: "xmark", warning: "bell", info: "bell" };
  const iconBg = { danger: "bg-[var(--error-light)]", warning: "bg-[var(--warning-light)]", info: "bg-[var(--primary-light)]" };
  const iconColor = { danger: "text-[var(--error)]", warning: "text-[var(--warning)]", info: "text-[var(--primary)]" };
  const btnBg = { danger: "bg-[var(--error)] hover:opacity-90 text-white", warning: "bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-[var(--primary-foreground)]", info: "bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-[var(--primary-foreground)]" };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onCancel} role="dialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-message">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div className="relative card-elevated w-full max-w-md p-5 animate-scale-in" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start gap-3.5 mb-4">
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${iconBg[variant]} ${iconColor[variant]}`} aria-hidden="true">
            <Icon name={iconMap[variant]} className="w-4.5 h-4.5" />
          </div>
          <div>
            <h3 id="confirm-title" className="text-base font-semibold text-[var(--foreground)]">{title}</h3>
            <p id="confirm-message" className="text-sm text-[var(--muted-foreground)] mt-1 leading-relaxed">{message}</p>
          </div>
        </div>
        <div className="flex gap-2.5 justify-end mt-5">
          <button onClick={onCancel} className="btn-secondary px-4 py-2 text-sm cursor-pointer">{cancelLabel}</button>
          <button onClick={onConfirm} className={`px-4 py-2 rounded-[var(--radius)] text-sm font-semibold transition-all cursor-pointer ${btnBg[variant]}`}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}
