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

  const borderColors: Record<ToastType, string> = {
    success: "border-l-[var(--success)]",
    error: "border-l-[var(--error)]",
    info: "border-l-[var(--primary)]",
    warning: "border-l-[var(--warning)]",
  };

  const iconColors: Record<ToastType, string> = {
    success: "text-[var(--success)]",
    error: "text-[var(--error)]",
    info: "text-[var(--primary)]",
    warning: "text-[var(--warning)]",
  };

  const icons: Record<ToastType, string> = { success: "check", error: "xmark", info: "bell", warning: "bell" };

  return (
    <>
      {children}
      <div className="fixed top-16 right-4 z-50 flex flex-col gap-2 max-w-sm" style={{ pointerEvents: "none" }}>
        {toasts.map((t) => (
          <div key={t.id} className={`card-elevated border-l-[3px] ${borderColors[t.type]} animate-slide-in-right p-3.5 flex items-start gap-2.5`} style={{ pointerEvents: "auto" }}>
            <div className={`${iconColors[t.type]} shrink-0 mt-0.5`}>
              <Icon name={icons[t.type]} className="w-4 h-4" />
            </div>
            <p className="text-sm text-[var(--foreground)] flex-1 leading-snug">{t.message}</p>
            <button onClick={() => remove(t.id)} className="text-[var(--muted-foreground)] hover:text-[var(--foreground)] shrink-0 cursor-pointer">
              <Icon name="close" className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </>
  );
}
