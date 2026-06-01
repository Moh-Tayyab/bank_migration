"use client";
import { useState, useEffect } from "react";
import Icon from "./Icon";
import { apiHeaders } from "./types";

interface SchemaPreviewProps {
  sourceBank: string;
  targetBanks: string[];
  sourceColumns: string[];
  banks: string[];
  apiBase: string;
}

interface MappingInfo {
  sourceField: string;
  targetField: string;
  transform?: string;
  isDefault: boolean;
}

function normalizeMapping(m: Record<string, unknown>): MappingInfo {
  return {
    sourceField: (m.sourceField || m.source_field || "") as string,
    targetField: (m.targetField || m.target_field || "") as string,
    transform: (m.transform || undefined) as string | undefined,
    isDefault: Boolean(m.default),
  };
}

export default function SchemaPreview({ sourceBank, targetBanks, sourceColumns, banks, apiBase }: SchemaPreviewProps) {
  const [mappings, setMappings] = useState<Record<string, MappingInfo[]>>({});
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    if (targetBanks.length === 0) return;
    setLoading(true);
    const fetchMappings = async () => {
      const result: Record<string, MappingInfo[]> = {};
      for (const target of targetBanks) {
        try {
          const res = await fetch(`${apiBase}/schema/${sourceBank}/${target}`, { headers: apiHeaders() });
          if (res.ok) {
            const data = await res.json();
            const raw = data.mappings || [];
            result[target] = raw.map(normalizeMapping);
          } else {
            result[target] = sourceColumns.map((col) => ({ sourceField: col, targetField: col, isDefault: false }));
          }
        } catch { result[target] = sourceColumns.map((col) => ({ sourceField: col, targetField: col, isDefault: false })); }
      }
      setMappings(result); setLoading(false);
    };
    fetchMappings();
  }, [sourceBank, targetBanks, apiBase, sourceColumns]);

  if (targetBanks.length === 0 || sourceColumns.length === 0) return null;

  return (
    <div className="card-elevated animate-scale-in">
      <div className="px-5 py-3.5 border-b border-[var(--border)] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-[var(--primary-light)] flex items-center justify-center">
            <Icon name="layers" className="w-3.5 h-3.5 text-[var(--primary)]" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--foreground)]">Schema Mapping</h3>
            <p className="text-[11px] text-[var(--muted-foreground)]">
              {sourceBank} &rarr; {targetBanks.join(", ")} &middot; {sourceColumns.length} columns
            </p>
          </div>
        </div>
        <button onClick={() => setExpanded(!expanded)} className="text-[11px] font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)] transition-colors cursor-pointer">
          {expanded ? "Collapse" : "Expand"}
        </button>
      </div>
      {expanded && (
        <div className="p-5 space-y-4 max-h-96 overflow-y-auto">
          {targetBanks.map((target) => {
            const bankMappings = mappings[target] || [];
            return (
              <div key={target} className="space-y-1.5">
                <h4 className="text-[11px] font-bold uppercase tracking-wider text-[var(--primary)]">{target}</h4>
                <div className="grid gap-1">
                  {bankMappings.length > 0 ? (
                    bankMappings.map((m, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg bg-[var(--muted)]/50">
                        <span className="font-mono text-[var(--foreground)] font-medium">{m.sourceField}</span>
                        {m.transform && (
                          <span className="px-1.5 py-0.5 rounded bg-[var(--primary-light)] text-[var(--primary)] text-[10px] font-bold">{m.transform}</span>
                        )}
                        <Icon name="arrow-right" className="w-3 h-3 text-[var(--muted-foreground)]" />
                        <span className={`font-mono font-medium ${m.isDefault ? "text-[var(--warning)]" : "text-[var(--foreground)]"}`}>
                          {m.targetField}
                        </span>
                        {m.isDefault && (
                          <span className="px-1.5 py-0.5 rounded bg-[var(--warning-light)] text-[var(--warning)] text-[10px] font-bold">default</span>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg bg-[var(--muted)]/50">
                      {sourceColumns.map((col) => (
                        <div key={col} className="flex items-center gap-2">
                          <span className="font-mono text-[var(--foreground)] font-medium">{col}</span>
                          <Icon name="arrow-right" className="w-3 h-3 text-[var(--muted-foreground)]" />
                          <span className="font-mono text-[var(--foreground)] font-medium">{col}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          {loading && (
            <div className="flex items-center gap-2 text-sm text-[var(--muted-foreground)]">
              <span className="w-4 h-4 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
              Loading mappings...
            </div>
          )}
        </div>
      )}
    </div>
  );
}
