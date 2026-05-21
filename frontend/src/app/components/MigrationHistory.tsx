"use client";
import { useState } from "react";
import Icon from "./Icon";

interface HistoryEntry {
  id: string;
  timestamp: string;
  sourceBank: string;
  targetBanks: string[];
  outputFormat: string;
  totalRecords: number;
  processed: number;
  failed: number;
  success: boolean;
  outputPaths: string[];
}

interface MigrationHistoryProps {
  history: HistoryEntry[];
  onClear: () => void;
  onRetry: (entry: HistoryEntry) => void;
}

export default function MigrationHistory({ history, onClear, onRetry }: MigrationHistoryProps) {
  const [expanded, setExpanded] = useState(false);

  if (history.length === 0) return null;

  return (
    <div className="card-elevated animate-slide-up">
      <div className="px-5 py-3.5 border-b border-[var(--border)] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-[var(--primary-light)] flex items-center justify-center">
            <Icon name="clock" className="w-3.5 h-3.5 text-[var(--primary)]" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--foreground)]">Migration History</h3>
            <p className="text-[11px] text-[var(--muted-foreground)]">{history.length} recent migration{history.length !== 1 ? "s" : ""}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setExpanded(!expanded)} className="text-[11px] font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)] transition-colors cursor-pointer">
            {expanded ? "Collapse" : "Expand"}
          </button>
          <button onClick={onClear} className="text-[11px] text-[var(--error)] hover:opacity-80 font-semibold transition-colors cursor-pointer">
            Clear
          </button>
        </div>
      </div>
      {(expanded ? history : history.slice(0, 3)).map((entry) => (
        <div key={entry.id} className="px-5 py-3 border-b border-[var(--border)] last:border-b-0 flex items-center justify-between hover:bg-[var(--muted)]/30 transition-colors">
          <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full shrink-0 ${entry.success ? "bg-[var(--success)]" : "bg-[var(--error)]"}`} />
            <div>
              <p className="text-xs font-medium text-[var(--foreground)]">
                {entry.sourceBank} &rarr; {entry.targetBanks.join(", ")}
              </p>
              <p className="text-[10px] text-[var(--muted-foreground)]">
                {new Date(entry.timestamp).toLocaleString()} &middot; {entry.outputFormat.toUpperCase()} &middot; {entry.processed}/{entry.totalRecords} records
              </p>
            </div>
          </div>
          {!entry.success && (
            <button onClick={() => onRetry(entry)} className="text-[11px] font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)] flex items-center gap-1 transition-colors cursor-pointer">
              <Icon name="refresh" className="w-3 h-3" />Retry
            </button>
          )}
        </div>
      ))}
      {!expanded && history.length > 3 && (
        <div className="px-5 py-2 text-center">
          <button onClick={() => setExpanded(true)} className="text-[11px] font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)] transition-colors cursor-pointer">
            Show {history.length - 3} more
          </button>
        </div>
      )}
    </div>
  );
}
