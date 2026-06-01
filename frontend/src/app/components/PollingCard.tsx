"use client";
import Icon from "./Icon";
import type { MigrationHook } from "./hooks/useMigration";

type Props = Pick<MigrationHook, "pollingTask" | "uploadProgress" | "pollingBanks">;

export default function PollingCard({ pollingTask, uploadProgress, pollingBanks }: Props) {
  if (!pollingTask) return null;
  const progress = uploadProgress ?? 30;

  return (
    <section className="card-elevated animate-scale-in" aria-label="Processing migration" aria-live="polite">
      <div className="px-5 py-3.5 border-b border-[var(--border)] flex items-center gap-3">
        <span className="w-4 h-4 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
        <div>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Processing in Background</h3>
          <p className="text-[11px] text-[var(--muted-foreground)]">{pollingBanks} bank(s) &middot; Polling for completion...</p>
        </div>
      </div>
      <div className="p-5 space-y-3">
        <div className="progress-track" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
          <div className="progress-fill progress-fill-indeterminate" style={{ width: `${progress}%` }} />
        </div>
        <div className="flex items-center justify-between">
          <p className="text-[11px] text-[var(--muted-foreground)] font-mono">Task: {pollingTask.slice(0, 16)}...</p>
          <span className="text-[11px] font-semibold text-[var(--primary)] tabular-nums">{progress}%</span>
        </div>
      </div>
    </section>
  );
}
