"use client";
import Icon from "./Icon";
import DownloadCommand from "./DownloadCommand";
import type { ResultData } from "./types";
import type { MigrationHook } from "./hooks/useMigration";

type Props = Pick<MigrationHook, "multiResults" | "apiBase">;

export default function MultiBankResults({ multiResults, apiBase }: Props) {
  if (multiResults.length === 0) return null;

  return (
    <section className="space-y-4 animate-scale-in" aria-label="Multi-bank migration results">
      <div className="flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-lg bg-[var(--success-light)] flex items-center justify-center">
          <Icon name="check" className="w-4 h-4 text-[var(--success)]" />
        </div>
        <h3 className="text-sm font-semibold text-[var(--foreground)]">Multi-Bank Migration Completed</h3>
      </div>
      <div className="grid gap-4">
        {multiResults.map((r: ResultData, idx: number) => (
          <div key={idx} className={`card-elevated ${r.success ? "border-[var(--success)]/20" : "border-[var(--error)]/20"}`}>
            <div className="px-5 py-3.5 border-b border-[var(--border)] flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-6 h-6 rounded-md flex items-center justify-center ${r.success ? "bg-[var(--success-light)]" : "bg-[var(--error-light)]"}`}>
                  {r.success ? <Icon name="check" className="w-3.5 h-3.5 text-[var(--success)]" /> : <Icon name="xmark" className="w-3.5 h-3.5 text-[var(--error)]" />}
                </div>
                <div>
                  <p className="text-sm font-semibold text-[var(--foreground)]">Bank {idx + 1}</p>
                  {r.output_path && <p className="text-[11px] text-[var(--muted-foreground)] font-mono mt-0.5">{r.output_path.split("/").pop()}</p>}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {r.success && r.output_path && (
                  <>
                    <a href={`${apiBase}/download/${r.output_path.split("/").pop()}`} className="text-[11px] font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)] flex items-center gap-1 transition-colors" download>
                      <Icon name="download" className="w-3 h-3" />Download
                    </a>
                    <DownloadCommand filename={r.output_path.split("/").pop()!} apiBase={apiBase} type="sh-curl" />
                  </>
                )}
                <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md ${r.success ? "bg-[var(--success-light)] text-[var(--success)]" : "bg-[var(--error-light)] text-[var(--error)]"}`}>
                  {r.success ? "Success" : "Failed"}
                </span>
              </div>
            </div>
            <div className="p-4 grid grid-cols-3 gap-4">
              <div><p className="text-[11px] text-[var(--muted-foreground)]">Total</p><p className="text-lg font-bold text-[var(--foreground)] tabular-nums">{r.total_records}</p></div>
              <div><p className="text-[11px] text-[var(--muted-foreground)]">Processed</p><p className="text-lg font-bold text-[var(--success)] tabular-nums">{r.processed}</p></div>
              <div><p className="text-[11px] text-[var(--muted-foreground)]">Failed</p><p className="text-lg font-bold text-[var(--error)] tabular-nums">{r.failed}</p></div>
            </div>
            {r.error && (
              <div className="px-4 pb-4">
                <p className="text-[11px] text-[var(--error)] bg-[var(--error-light)] px-2 py-1 rounded">Error: {r.error}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
