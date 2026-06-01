"use client";
import Icon from "./Icon";
import DownloadCommand from "./DownloadCommand";
import type { MigrationHook } from "./hooks/useMigration";

type Props = Pick<MigrationHook, "result" | "pct" | "apiBase">;

export default function ResultPanel({ result, pct, apiBase }: Props) {
  if (!result) return null;

  const filename = result.output_path?.split("/").pop();

  return (
    <section className="card-elevated animate-scale-in" aria-label="Migration result">
      <div className="px-5 py-3.5 border-b border-[var(--border)] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${result.success ? "bg-[var(--success-light)]" : "bg-[var(--error-light)]"}`}>
            {result.success
              ? <Icon name="check" className="w-4 h-4 text-[var(--success)]" />
              : <Icon name="xmark" className="w-4 h-4 text-[var(--error)]" />}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--foreground)]">Migration {result.success ? "Completed" : "Failed"}</h3>
            {result.success && filename && <p className="text-[11px] text-[var(--muted-foreground)] font-mono mt-0.5">{filename}</p>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {result.success && filename && (
            <>
              <a href={`${apiBase}/download/${filename}`} className="text-[11px] font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)] flex items-center gap-1 transition-colors" download>
                <Icon name="download" className="w-3 h-3" />Download
              </a>
              <DownloadCommand filename={filename} apiBase={apiBase} />
              <DownloadCommand filename={filename} apiBase={apiBase} type="sh-curl" />
            </>
          )}
          {result.success && <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-[var(--success-light)] text-[var(--success)]">Success</span>}
        </div>
      </div>
      <div className="p-5 space-y-5">
        <div className="grid grid-cols-3 gap-3">
          <div className="stat-card">
            <p className="text-[11px] text-[var(--muted-foreground)] font-medium mb-1">Total Records</p>
            <p className="text-xl font-bold text-[var(--foreground)] tabular-nums">{result.total_records.toLocaleString()}</p>
          </div>
          <div className="stat-card">
            <p className="text-[11px] text-[var(--muted-foreground)] font-medium mb-1">Processed</p>
            <p className="text-xl font-bold text-[var(--success)] tabular-nums">{result.processed.toLocaleString()}</p>
          </div>
          <div className="stat-card">
            <p className="text-[11px] text-[var(--muted-foreground)] font-medium mb-1">Failed</p>
            <p className="text-xl font-bold text-[var(--error)] tabular-nums">{result.failed.toLocaleString()}</p>
          </div>
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-[var(--muted-foreground)] font-medium">Completion</span>
            <span className="font-bold text-[var(--foreground)] tabular-nums">{pct}%</span>
          </div>
          <div className="progress-track" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
            <div className={`progress-fill ${pct >= 100 ? "progress-fill-success" : ""}`} style={{ width: `${pct}%` }} />
          </div>
          <p className="text-[11px] text-[var(--muted-foreground)] tabular-nums">{result.processed}/{result.total_records} records</p>
        </div>
      </div>
    </section>
  );
}
