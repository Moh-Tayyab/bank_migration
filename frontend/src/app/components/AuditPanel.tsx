"use client";
import Icon from "./Icon";
import StatusBadge from "./StatusBadge";
import type { MigrationHook } from "./hooks/useMigration";

type Props = Pick<MigrationHook, "auditTrail" | "showAudit" | "setShowAudit" | "handleExportAudit">;

export default function AuditPanel({ auditTrail, showAudit, setShowAudit, handleExportAudit }: Props) {
  if (auditTrail.length === 0) return null;

  return (
    <section className="card-elevated animate-slide-up" aria-label="Audit trail">
      <div className="px-5 py-3.5 border-b border-[var(--border)] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-[var(--primary-light)] flex items-center justify-center">
            <Icon name="audit" className="w-3.5 h-3.5 text-[var(--primary)]" />
          </div>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Audit Trail</h3>
          <span className="px-1.5 py-0.5 rounded-md bg-[var(--primary-light)] text-[var(--primary)] text-[10px] font-bold">{auditTrail.length}</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleExportAudit} className="text-[11px] font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)] transition-colors flex items-center gap-1 cursor-pointer" aria-label="Export audit trail as CSV">
            <Icon name="download" className="w-3 h-3" />Export
          </button>
          <button onClick={() => setShowAudit(!showAudit)} className="text-[11px] font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)] transition-colors cursor-pointer" id="toggle-audit" aria-expanded={showAudit}>
            {showAudit ? "Collapse" : "Expand"}
          </button>
        </div>
      </div>
      <div className={showAudit ? "" : "max-h-64 overflow-y-auto"}>
        <table className="audit-table">
          <thead>
            <tr><th>Event</th><th>Record ID</th><th className="hidden sm:table-cell">Details</th><th className="hidden md:table-cell">Timestamp</th></tr>
          </thead>
          <tbody>
            {auditTrail.map((e, i) => (
              <tr key={i}>
                <td><StatusBadge status={e.event} /></td>
                <td className="text-xs font-mono text-[var(--muted-foreground)]">{e.record_id || "—"}</td>
                <td className="hidden sm:table-cell text-xs text-[var(--muted-foreground)] max-w-[220px] truncate">{e.details}</td>
                <td className="hidden md:table-cell text-xs text-[var(--muted-foreground)] whitespace-nowrap">
                  {new Date(e.timestamp).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
