"use client";
import { useState } from "react";
import Icon from "./Icon";

interface FilePreviewProps {
  filename: string;
  format: string;
  columns: string[];
  rows: Record<string, string | number>[];
  rowCount: number;
  onClose: () => void;
}

export default function FilePreview({ filename, format, columns, rows, rowCount, onClose }: FilePreviewProps) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="card animate-scale-in">
      <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-[var(--primary-light)] flex items-center justify-center">
            <Icon name="file" className="w-3.5 h-3.5 text-[var(--primary)]" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--foreground)]">{filename}</h3>
            <p className="text-[11px] text-[var(--muted-foreground)]">{format.toUpperCase()} &middot; {rowCount} rows &middot; {columns.length} columns</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setExpanded(!expanded)} className="text-[11px] font-medium text-[var(--primary)] hover:text-[var(--primary-hover)] cursor-pointer">
            {expanded ? "Collapse" : "Expand"}
          </button>
          <button onClick={onClose} className="text-[var(--muted-foreground)] hover:text-[var(--foreground)] cursor-pointer">
            <Icon name="close" className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      {expanded && (
        <div className="overflow-x-auto max-h-64 overflow-y-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-[var(--card)] z-10">
              <tr>
                <th className="text-left px-3 py-2 font-medium text-[var(--muted-foreground)] border-b border-[var(--border)]">#</th>
                {columns.map((col) => (
                  <th key={col} className="text-left px-3 py-2 font-medium text-[var(--muted-foreground)] border-b border-[var(--border)] whitespace-nowrap">{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} className="hover:bg-[var(--muted)]/50 transition-colors">
                  <td className="px-3 py-2 text-[var(--muted-foreground)] font-mono">{i + 1}</td>
                  {columns.map((col) => (
                    <td key={col} className="px-3 py-2 text-[var(--foreground)] whitespace-nowrap max-w-[200px] truncate" title={String(row[col] ?? "")}>
                      {row[col] !== undefined && row[col] !== null ? String(row[col]) : <span className="text-[var(--muted-foreground)] italic">null</span>}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
