"use client";
import { useState, useEffect, useCallback } from "react";
import Icon from "./Icon";

export type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

let toastId = 0;
let globalAddToast: ((t: Omit<Toast, "id">) => void) | null = null;

export function toast(type: ToastType, message: string, duration = 4000) {
  if (globalAddToast) globalAddToast({ type, message, duration });
}

const borderColors: Record<ToastType, string> = {
  success: "border-l-[var(--success)]",
  error: "border-l-[var(--error)]",
  info: "border-l-[var(--info)]",
  warning: "border-l-[var(--warning)]",
};

const iconColors: Record<ToastType, string> = {
  success: "text-[var(--success)]",
  error: "text-[var(--error)]",
  info: "text-[var(--info)]",
  warning: "text-[var(--warning)]",
};

const icons: Record<ToastType, string> = {
  success: "check-circle",
  error: "xmark",
  info: "bell",
  warning: "bell",
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((t: Omit<Toast, "id">) => {
    const id = `toast-${++toastId}`;
    const duration = t.duration ?? 4000;
    setToasts((prev) => [...prev, { ...t, id, duration }]);
    setTimeout(() => { setToasts((prev) => prev.filter((toast) => toast.id !== id)); }, duration);
  }, []);

  useEffect(() => { globalAddToast = addToast; return () => { globalAddToast = null; }; }, [addToast]);

  const remove = (id: string) => setToasts((prev) => prev.filter((t) => t.id !== id));

  return (
    <>
      {children}
      <div className="fixed top-14 right-4 z-50 flex flex-col gap-2 max-w-sm" aria-live="polite" aria-label="Notifications" style={{ pointerEvents: "none" }}>
        {toasts.map((t) => (
          <div key={t.id} className={`border border-[var(--border)] bg-[var(--card)] rounded-lg border-l-[3px] ${borderColors[t.type]} shadow-sm animate-slide-up p-3 flex items-start gap-2.5`} style={{ pointerEvents: "auto" }} role="status">
            <div className={`${iconColors[t.type]} shrink-0 mt-0.5`} aria-hidden="true">
              <Icon name={icons[t.type]} className="w-4 h-4" />
            </div>
            <p className="text-xs text-[var(--foreground)] flex-1 leading-snug">{t.message}</p>
            <button onClick={() => remove(t.id)} className="text-[var(--muted-foreground)] hover:text-[var(--foreground)] shrink-0 cursor-pointer" aria-label="Dismiss notification">
              <Icon name="close" className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>
    </>
  );
}
