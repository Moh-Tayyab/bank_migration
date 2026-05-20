"use client";
import { useState, useRef, useCallback, useEffect } from "react";
import Icon from "./components/Icon";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

type AuditEntry = { event: string; record_id: string; bank_pair: string; details: string; timestamp: string };
type ResultData = { success: boolean; total_records: number; processed: number; failed: number; output_path: string | null; error: string | null };

const fmt = (name: string) => name.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    INPUT_RECEIVED: "received",
    VALIDATION: "validation",
    MAPPING: "mapping",
    TRANSFORM: "transform",
    SECURITY_MASK: "masked",
    COMMITTED: "committed",
    ROLLED_BACK: "rolled-back",
    ERROR: "error",
    OUTPUT_GENERATED: "output",
  };
  const cls = map[status] || "info";
  return <span className={`badge badge-${cls}`}>{status.replace(/_/g, " ")}</span>;
}

function StatCard({ value, label, icon, trend }: { value: number | string; label: string; icon: string; trend?: { value: string; positive: boolean } }) {
  return (
    <div className="dashboard-card group">
      <div className="flex items-start justify-between mb-4">
        <div className="w-10 h-10 rounded-xl bg-[var(--primary-light)] flex items-center justify-center text-[var(--primary)] group-hover:scale-110 transition-transform duration-300">
          <Icon name={icon} className="w-5 h-5" />
        </div>
        {trend && (
          <span className={`inline-flex items-center gap-0.5 text-[11px] font-semibold px-2 py-0.5 rounded-full ${trend.positive ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500"}`}>
            <Icon name={trend.positive ? "arrow" : "arrow"} className={`w-2.5 h-2.5 ${trend.positive ? "" : "rotate-180"}`} />
            {trend.value}
          </span>
        )}
      </div>
      <p className="text-2xl font-bold tracking-tight text-[var(--foreground)]">{typeof value === "number" ? value.toLocaleString() : value}</p>
      <p className="text-xs text-[var(--muted-foreground)] mt-1 font-medium">{label}</p>
    </div>
  );
}

function SectionHeader({ icon, title, description }: { icon: string; title: string; description?: string }) {
  return (
    <div className="flex items-start gap-3.5 mb-8">
      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--primary-light)] to-[var(--accent)] flex items-center justify-center text-[var(--primary)] shadow-sm shrink-0">
        <Icon name={icon} className="w-5 h-5" />
      </div>
      <div>
        <h2 className="text-xl font-bold text-[var(--foreground)] tracking-tight">{title}</h2>
        {description && <p className="text-sm text-[var(--muted-foreground)] mt-0.5">{description}</p>}
      </div>
    </div>
  );
}

function DashboardHome({ banks }: { banks: string[] }) {
  return (
    <div className="space-y-8 animate-fade-in">
      <SectionHeader icon="dashboard" title="Dashboard" description="Overview of the data migration platform" />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard value={banks.length} label="Connected Banks" icon="banks" trend={{ value: "12%", positive: true }} />
        <StatCard value={0} label="Migrations Today" icon="migration" />
        <StatCard value={"99.9%"} label="System Uptime" icon="shield" trend={{ value: "0.2%", positive: true }} />
        <StatCard value={0} label="Records Processed" icon="database" trend={{ value: "8.1%", positive: true }} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 glass-card-elevated p-6">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-sm font-bold text-[var(--foreground)]">Connected Banks</h3>
            <span className="text-[11px] font-semibold text-[var(--muted-foreground)]">{banks.length} total</span>
          </div>
          {banks.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {banks.map(b => (
                <div key={b} className="flex items-center gap-3 p-3 rounded-xl bg-[var(--muted)] border border-[var(--border)] hover:border-[var(--border-hover)] transition-all group">
                  <span className="relative flex w-2.5 h-2.5">
                    <span className="absolute inset-0 rounded-full bg-emerald-500 animate-pulse-dot d1" />
                    <span className="relative rounded-full bg-emerald-500 w-2.5 h-2.5" />
                  </span>
                  <span className="text-sm font-semibold text-[var(--foreground)] group-hover:text-[var(--primary)] transition-colors">{fmt(b)}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center py-8 text-center">
              <div className="p-3 rounded-xl bg-[var(--accent)] mb-3">
                <Icon name="database" className="w-6 h-6 text-[var(--muted-foreground)]" />
              </div>
              <p className="text-sm text-[var(--muted-foreground)]">No banks connected yet</p>
              <p className="text-xs text-[var(--muted-foreground)]/60 mt-0.5">Start the API server to see connected banks</p>
            </div>
          )}
        </div>

        <div className="glass-card-elevated p-6">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-sm font-bold text-[var(--foreground)]">Platform Status</h3>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-500 text-[10px] font-bold">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Online
            </span>
          </div>
          <div className="space-y-3.5">
            {[
              { label: "API Gateway", status: "operational", icon: "shield" },
              { label: "Database", status: "operational", icon: "database" },
              { label: "Migration Engine", status: "operational", icon: "migration" },
              { label: "Audit Service", status: "operational", icon: "audit" },
            ].map(s => (
              <div key={s.label} className="flex items-center justify-between p-2.5 rounded-xl bg-[var(--muted)]">
                <div className="flex items-center gap-2.5">
                  <Icon name={s.icon} className="w-3.5 h-3.5 text-[var(--muted-foreground)]" />
                  <span className="text-xs font-medium text-[var(--foreground)]">{s.label}</span>
                </div>
                <span className="text-[10px] font-bold text-emerald-500 uppercase tracking-wider">{s.status}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function MigrationSection() {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [sourceBank, setSourceBank] = useState("source_bank");
  const [targetBanks, setTargetBanks] = useState<string[]>([]);
  const [outputFormat, setOutputFormat] = useState("json");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ResultData | null>(null);
  const [multiResults, setMultiResults] = useState<ResultData[]>([]);
  const [auditTrail, setAuditTrail] = useState<AuditEntry[]>([]);
  const [banks, setBanks] = useState<string[]>([]);
  const [showAudit, setShowAudit] = useState(false);
  const [errMsg, setErrMsg] = useState("");
  const [showTargetDropdown, setShowTargetDropdown] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch(`${API_BASE}/banks`).then(r => r.json()).then(d => setBanks(d.banks || [])).catch(() => {});
  }, []);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest("#target-banks-select") && !target.closest("#target-banks-dropdown")) {
        setShowTargetDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
  }, []);

  const onFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) setFile(e.target.files[0]);
  };

  const toggleTargetBank = (bank: string) => {
    setTargetBanks(prev => prev.includes(bank) ? prev.filter(b => b !== bank) : [...prev, bank]);
  };

  const handleMigrate = async () => {
    if (!file || targetBanks.length === 0) return;
    setLoading(true); setResult(null); setMultiResults([]); setAuditTrail([]); setErrMsg("");
    const form = new FormData();
    form.append("file", file); form.append("source_bank", sourceBank);
    form.append("target_banks", JSON.stringify(targetBanks)); form.append("output_format", outputFormat);
    try {
      const res = await fetch(`${API_BASE}/migrate/upload`, { method: "POST", body: form });
      const data = await res.json();
      if (data.task_id) {
        setResult({ success: true, total_records: 0, processed: 0, failed: 0, output_path: null, error: null });
        setErrMsg(`Migration queued. Task ID: ${data.task_id}. ${data.message || ""}`);
      } else {
        setResult(data);
        if (data.results) setMultiResults(data.results);
        if (data.audit_trail) setAuditTrail(data.audit_trail);
        if (!data.success) setErrMsg(data.error || "Migration failed");
      }
    } catch (e: unknown) {
      setErrMsg(e instanceof Error ? e.message : "Connection failed. Ensure the API server is running.");
    } finally { setLoading(false); }
  };

  const pct = result && result.total_records > 0 ? Math.round((result.processed / result.total_records) * 100) : 0;

  return (
    <div className="space-y-6 animate-fade-in">
      <SectionHeader icon="migration" title="Data Migration" description="Upload source data, configure the ETL pipeline, and execute secure multi-bank migrations" />

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-card-elevated">
            <div className="px-6 py-4 border-b border-[var(--border)] flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg bg-[var(--primary-light)]">
                <Icon name="upload" className="w-4 h-4 text-[var(--primary)]" />
              </div>
              <h3 className="text-sm font-bold text-[var(--foreground)]">Upload Data</h3>
            </div>
            <div className="p-6">
              <div
                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={onDrop}
                onClick={() => inputRef.current?.click()}
                className={`dropzone ${dragOver ? "active" : ""} ${file ? "has-file" : ""}`}
                id="file-dropzone"
              >
                <input ref={inputRef} type="file" onChange={onFileSelect} className="hidden" accept=".csv,.json,.docx,.xlsx,.xml,.txt" id="file-input" />
                <div className="flex flex-col items-center gap-3">
                  <div className={`p-3.5 rounded-2xl transition-all duration-300 ${file ? "bg-[var(--primary)]/10 text-[var(--primary)] shadow-[var(--shadow-glow)]" : dragOver ? "bg-[var(--primary)]/10 text-[var(--primary)]" : "bg-[var(--muted)] text-[var(--muted-foreground)]"}`}>
                    {file ? <Icon name="file" className="w-7 h-7" /> : <Icon name="upload" className="w-7 h-7" />}
                  </div>
                  {file ? (
                    <div className="space-y-1 text-center">
                      <p className="text-sm font-semibold text-[var(--foreground)]">{file.name}</p>
                      <p className="text-xs text-[var(--muted-foreground)]">{(file.size / 1024).toFixed(1)} KB — Click to change</p>
                    </div>
                  ) : (
                    <div className="space-y-1 text-center">
                      <p className="text-sm font-medium text-[var(--muted-foreground)]">
                        <span className="text-[var(--primary)] font-semibold">Click to upload</span> or drag and drop
                      </p>
                      <p className="text-xs text-[var(--muted-foreground)]">CSV, JSON, DOCX, XLSX, XML, TXT up to 10MB</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="glass-card-elevated">
            <div className="px-6 py-4 border-b border-[var(--border)] flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg bg-[var(--primary-light)]">
                <Icon name="banks" className="w-4 h-4 text-[var(--primary)]" />
              </div>
              <h3 className="text-sm font-bold text-[var(--foreground)]">Pipeline Configuration</h3>
            </div>
            <div className="p-6 space-y-5">
              <div>
                <label className="block text-xs font-semibold text-[var(--muted-foreground)] mb-2 uppercase tracking-wider">Source Bank</label>
                <div className="relative">
                  <select value={sourceBank} onChange={e => setSourceBank(e.target.value)} className="select-field" id="source-bank-select">
                    {banks.length > 0
                      ? banks.map(b => <option key={b} value={b}>{fmt(b)}</option>)
                      : <option value="source_bank">Source Bank</option>}
                  </select>
                  <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
                    <Icon name="chevron" className="w-4 h-4 text-[var(--muted-foreground)]" />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--muted-foreground)] mb-2 uppercase tracking-wider">Target Banks (select one or more)</label>
                <div className="relative">
                  <button onClick={() => setShowTargetDropdown(!showTargetDropdown)} className="select-field text-left flex items-center justify-between w-full" id="target-banks-select" type="button">
                    <span className={targetBanks.length === 0 ? "text-[var(--muted-foreground)]" : ""}>
                      {targetBanks.length === 0 ? "Select target banks..." : `${targetBanks.length} bank(s) selected`}
                    </span>
                    <Icon name="chevron" className={`w-4 h-4 text-[var(--muted-foreground)] transition-transform ${showTargetDropdown ? "rotate-180" : ""}`} />
                  </button>
                  {showTargetDropdown && (
                    <div id="target-banks-dropdown" className="absolute z-20 mt-1 w-full rounded-xl bg-[var(--card)] border border-[var(--border)] shadow-xl p-2 space-y-0.5 max-h-48 overflow-y-auto">
                      {(banks.length > 0 ? banks : ["source_bank", "target_bank"]).map(b => (
                        <label key={b} className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-[var(--muted)] cursor-pointer transition-colors">
                          <input type="checkbox" checked={targetBanks.includes(b)} onChange={() => toggleTargetBank(b)} className="w-4 h-4 rounded border-[var(--border)] text-[var(--primary)] focus:ring-[var(--primary)]" />
                          <span className="text-sm font-medium text-[var(--foreground)]">{fmt(b)}</span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--muted-foreground)] mb-2 uppercase tracking-wider">Output Format</label>
                <div className="grid grid-cols-5 gap-2">
                  {["json", "csv", "docx", "xlsx", "html"].map(f => (
                    <button key={f} onClick={() => { setOutputFormat(f); }} className={`format-btn ${outputFormat === f ? "active" : ""}`} id={`format-${f}`} type="button">
                      {f.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>

              <button onClick={handleMigrate} disabled={!file || targetBanks.length === 0 || loading} className="btn-primary w-full h-12 text-sm flex items-center justify-center gap-2.5" id="migrate-btn" type="button">
                {loading ? (
                  <span className="flex items-center gap-2.5">
                    <span className="flex gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse-dot d1" />
                      <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse-dot d2" />
                      <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse-dot d3" />
                    </span>
                    <span>Migrating...</span>
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Icon name="arrow" className="w-4 h-4" />
                    <span>Migrate Data</span>
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>

        <div className="lg:col-span-3 space-y-6">
          {errMsg && (
            <div className="glass-card border-red-500/30 dark:border-red-500/20 animate-scale-in" style={{background:"var(--error-light)"}}>
              <div className="p-5 flex items-start gap-3">
                <div className="p-2 rounded-xl bg-red-500/10 shrink-0">
                  <Icon name="xmark" className="w-5 h-5 text-red-500" />
                </div>
                <div>
                  <p className="text-sm font-bold text-red-700 dark:text-red-300">Migration Error</p>
                  <p className="text-xs text-red-600 dark:text-red-400 mt-1 leading-relaxed">{errMsg}</p>
                </div>
              </div>
            </div>
          )}

          {multiResults.length > 0 && (
            <div className="space-y-4 animate-scale-in">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 rounded-xl bg-emerald-500/10"><Icon name="check" className="w-5 h-5 text-emerald-500" /></div>
                <h3 className="text-sm font-bold text-[var(--foreground)]">Multi-Bank Migration Completed</h3>
              </div>
              {multiResults.map((r, idx) => (
                <div key={idx} className={`glass-card-elevated ${r.success ? "border-emerald-500/20" : "border-red-500/20"}`}>
                  <div className="px-6 py-4 border-b border-[var(--border)] flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-xl ${r.success ? "bg-emerald-500/10" : "bg-red-500/10"}`}>
                        {r.success ? <Icon name="check" className="w-5 h-5 text-emerald-500" /> : <Icon name="xmark" className="w-5 h-5 text-red-500" />}
                      </div>
                      <div>
                        <p className="text-sm font-bold text-[var(--foreground)]">Bank {idx + 1}</p>
                        {r.output_path && <p className="text-xs text-[var(--muted-foreground)] mt-0.5 font-mono">{r.output_path.split("/").pop()}</p>}
                      </div>
                    </div>
                    <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full ${r.success ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500"}`}>
                      {r.success ? "Success" : "Failed"}
                    </span>
                  </div>
                  <div className="p-4 grid grid-cols-3 gap-4">
                    <div><p className="text-xs text-[var(--muted-foreground)]">Total</p><p className="text-lg font-bold">{r.total_records}</p></div>
                    <div><p className="text-xs text-[var(--muted-foreground)]">Processed</p><p className="text-lg font-bold text-emerald-500">{r.processed}</p></div>
                    <div><p className="text-xs text-[var(--muted-foreground)]">Failed</p><p className="text-lg font-bold text-red-500">{r.failed}</p></div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {result && multiResults.length === 0 && (
            <div className="glass-card-elevated animate-scale-in" key={result.success ? "success" : "fail"}>
              <div className="px-6 py-4 border-b border-[var(--border)] flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-xl ${result.success ? "bg-emerald-500/10" : "bg-red-500/10"}`}>
                    {result.success
                      ? <Icon name="check" className="w-5 h-5 text-emerald-500" />
                      : <Icon name="xmark" className="w-5 h-5 text-red-500" />}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-[var(--foreground)]">
                      Migration {result.success ? "Completed Successfully" : "Failed"}
                    </h3>
                    {result.success && result.output_path && (
                      <p className="text-xs text-[var(--muted-foreground)] mt-0.5 font-mono">{result.output_path.split("/").pop()}</p>
                    )}
                  </div>
                </div>
                {result.success && (
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-500">Success</span>
                )}
              </div>
              <div className="p-6 space-y-6">
                <div className="grid grid-cols-3 gap-4">
                  <div className="dashboard-card">
                    <p className="text-xs text-[var(--muted-foreground)] font-medium mb-1">Total Records</p>
                    <p className="text-xl font-bold text-[var(--foreground)]">{result.total_records.toLocaleString()}</p>
                  </div>
                  <div className="dashboard-card">
                    <p className="text-xs text-[var(--muted-foreground)] font-medium mb-1">Processed</p>
                    <p className="text-xl font-bold text-emerald-500">{result.processed.toLocaleString()}</p>
                  </div>
                  <div className="dashboard-card">
                    <p className="text-xs text-[var(--muted-foreground)] font-medium mb-1">Failed</p>
                    <p className="text-xl font-bold text-red-500">{result.failed.toLocaleString()}</p>
                  </div>
                </div>
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[var(--muted-foreground)] font-medium">Completion Progress</span>
                    <span className="font-bold text-[var(--foreground)]">{pct}%</span>
                  </div>
                  <div className="progress-track">
                    <div className="progress-fill" style={{ width: `${pct}%` }} />
                  </div>
                  <div className="flex justify-between text-xs text-[var(--muted-foreground)]">
                    <span>{result.processed}/{result.total_records} records</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {auditTrail.length > 0 && (
            <div className="glass-card-elevated animate-slide-up">
              <div className="px-6 py-4 border-b border-[var(--border)] flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 rounded-lg bg-[var(--primary-light)]">
                    <Icon name="audit" className="w-4 h-4 text-[var(--primary)]" />
                  </div>
                  <h3 className="text-sm font-bold text-[var(--foreground)]">Audit Trail</h3>
                  <span className="ml-1 px-2 py-0.5 rounded-full bg-[var(--primary)]/10 text-[var(--primary)] text-[10px] font-bold">{auditTrail.length}</span>
                </div>
                <button onClick={() => setShowAudit(!showAudit)} className="text-xs font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)] transition-colors" id="toggle-audit">
                  {showAudit ? "Collapse" : "Expand All"}
                </button>
              </div>
              <div className={showAudit ? "" : "max-h-64 overflow-y-auto"}>
                <table className="audit-table">
                  <thead>
                    <tr>
                      <th>Event</th>
                      <th>Record ID</th>
                      <th className="hidden sm:table-cell">Details</th>
                      <th className="hidden md:table-cell">Timestamp</th>
                    </tr>
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
            </div>
          )}

          {!result && !errMsg && (
            <div className="glass-card-elevated p-12 flex flex-col items-center justify-center text-center min-h-[400px]">
              <div className="relative mb-6">
                <div className="p-5 rounded-3xl bg-gradient-to-br from-[var(--primary-light)] to-[var(--accent)]">
                  <Icon name="layers" className="w-10 h-10 text-[var(--primary)]" />
                </div>
                <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-[var(--primary)] animate-pulse-dot d1" />
              </div>
              <h3 className="text-lg font-bold text-[var(--foreground)]">Ready to Migrate</h3>
              <p className="text-sm text-[var(--muted-foreground)] max-w-md mt-2 leading-relaxed">
                Upload a data file, configure source and target banks, then click <span className="font-semibold text-[var(--foreground)]">Migrate Data</span> to start the ETL pipeline.
              </p>
              <div className="mt-8 flex flex-wrap items-center justify-center gap-6">
                {[
                  { icon: "zap", label: "400 rec/s throughput" },
                  { icon: "shield", label: "AES-256 encrypted" },
                  { icon: "audit", label: "ACID rollback" },
                ].map(f => (
                  <span key={f.label} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--muted)] border border-[var(--border)] text-xs text-[var(--muted-foreground)] font-medium">
                    <Icon name={f.icon} className="w-3.5 h-3.5 text-[var(--primary)]" />
                    {f.label}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function AuditSection() {
  const [auditLogs, setAuditLogs] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/audit`)
      .then(r => r.json())
      .then(d => setAuditLogs(d.audit_trail || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6 animate-fade-in">
      <SectionHeader icon="audit" title="Audit Trail" description="Complete history of all data migration operations" />

      <div className="glass-card-elevated">
        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-12 flex items-center justify-center">
              <span className="flex gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[var(--primary)] animate-pulse-dot d1" />
                <span className="w-2 h-2 rounded-full bg-[var(--primary)] animate-pulse-dot d2" />
                <span className="w-2 h-2 rounded-full bg-[var(--primary)] animate-pulse-dot d3" />
              </span>
            </div>
          ) : auditLogs.length > 0 ? (
            <table className="audit-table">
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Record ID</th>
                  <th>Bank Pair</th>
                  <th className="hidden sm:table-cell">Details</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((e, i) => (
                  <tr key={i}>
                    <td><StatusBadge status={e.event} /></td>
                    <td className="text-xs font-mono text-[var(--muted-foreground)]">{e.record_id || "—"}</td>
                    <td className="text-xs text-[var(--muted-foreground)]">{e.bank_pair || "—"}</td>
                    <td className="hidden sm:table-cell text-xs text-[var(--muted-foreground)] max-w-[200px] truncate">{e.details}</td>
                    <td className="text-xs text-[var(--muted-foreground)] whitespace-nowrap">
                      {new Date(e.timestamp).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-12 flex flex-col items-center text-center">
              <div className="p-4 rounded-2xl bg-[var(--muted)] mb-4">
                <Icon name="audit" className="w-8 h-8 text-[var(--muted-foreground)]" />
              </div>
              <h3 className="text-sm font-bold text-[var(--foreground)] mb-1">No Audit Records</h3>
              <p className="text-xs text-[var(--muted-foreground)]">Audit logs will appear once migrations are executed</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function BanksSection() {
  const [banks, setBanks] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/banks`)
      .then(r => r.json())
      .then(d => setBanks(d.banks || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6 animate-fade-in">
      <SectionHeader icon="banks" title="Banks" description="Manage connected banking institutions" />

      {loading ? (
        <div className="glass-card-elevated p-12 flex items-center justify-center">
          <span className="flex gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[var(--primary)] animate-pulse-dot d1" />
            <span className="w-2 h-2 rounded-full bg-[var(--primary)] animate-pulse-dot d2" />
            <span className="w-2 h-2 rounded-full bg-[var(--primary)] animate-pulse-dot d3" />
          </span>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {banks.length > 0 ? banks.map(b => (
            <div key={b} className="glass-card-elevated p-5 flex items-center gap-4 group hover:translate-y-[-2px] transition-all duration-300">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[var(--primary-light)] to-[var(--accent)] flex items-center justify-center text-[var(--primary)] font-bold text-lg shadow-sm group-hover:scale-110 transition-transform">
                {b.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-[var(--foreground)] truncate">{fmt(b)}</p>
                <div className="flex items-center gap-1.5 mt-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  <span className="text-[10px] font-medium text-emerald-500">Connected</span>
                </div>
              </div>
            </div>
          )) : (
            <div className="col-span-full glass-card-elevated p-12 flex flex-col items-center text-center">
              <div className="p-4 rounded-2xl bg-[var(--muted)] mb-4">
                <Icon name="database" className="w-8 h-8 text-[var(--muted-foreground)]" />
              </div>
              <h3 className="text-sm font-bold text-[var(--foreground)] mb-1">No Banks Configured</h3>
              <p className="text-xs text-[var(--muted-foreground)]">Start the API server to connect banking institutions</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SettingsSection() {
  return (
    <div className="space-y-6 animate-fade-in">
      <SectionHeader icon="settings" title="Settings" description="Platform configuration and preferences" />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card-elevated p-6">
          <h3 className="text-sm font-bold text-[var(--foreground)] mb-4 flex items-center gap-2">
            <Icon name="shield" className="w-4 h-4 text-[var(--primary)]" />
            Security
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="text-sm font-medium text-[var(--foreground)]">AES-256 Encryption</p>
                <p className="text-xs text-[var(--muted-foreground)]">Data encrypted at rest and in transit</p>
              </div>
              <span className="px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-500 text-[10px] font-bold">Active</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="text-sm font-medium text-[var(--foreground)]">ACID Rollback</p>
                <p className="text-xs text-[var(--muted-foreground)]">Automatic rollback on migration failure</p>
              </div>
              <span className="px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-500 text-[10px] font-bold">Enabled</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="text-sm font-medium text-[var(--foreground)]">Audit Logging</p>
                <p className="text-xs text-[var(--muted-foreground)]">Complete trail of all operations</p>
              </div>
              <span className="px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-500 text-[10px] font-bold">Enabled</span>
            </div>
          </div>
        </div>

        <div className="glass-card-elevated p-6">
          <h3 className="text-sm font-bold text-[var(--foreground)] mb-4 flex items-center gap-2">
            <Icon name="globe" className="w-4 h-4 text-[var(--primary)]" />
            API Configuration
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="text-sm font-medium text-[var(--foreground)]">API Endpoint</p>
                <p className="text-xs text-[var(--muted-foreground)] font-mono">{API_BASE}</p>
              </div>
            </div>
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="text-sm font-medium text-[var(--foreground)]">API Status</p>
                <p className="text-xs text-[var(--muted-foreground)]">Check connection to backend</p>
              </div>
              <span className="px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-500 text-[10px] font-bold">Checking</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [activeSection, setActiveSection] = useState("dashboard");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [banks, setBanks] = useState<string[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/banks`).then(r => r.json()).then(d => setBanks(d.banks || [])).catch(() => {});
  }, []);

  const sectionTitle: Record<string, string> = {
    dashboard: "Dashboard",
    migrate: "Migration",
    audit: "Audit Trail",
    banks: "Banks",
    settings: "Settings",
  };

  const sectionSubtitle: Record<string, string> = {
    dashboard: "Platform overview and key metrics",
    migrate: "Execute multi-bank data migrations",
    audit: "Review migration history and logs",
    banks: "Connected banking institutions",
    settings: "System configuration",
  };

  return (
    <div className="min-h-screen relative overflow-hidden">
      <div className="orb orb-1" aria-hidden="true" />
      <div className="orb orb-2" aria-hidden="true" />

      <Sidebar
        activeSection={activeSection}
        onNavigate={setActiveSection}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />

      <div className={`transition-all duration-300 ${sidebarCollapsed ? "lg:ml-[72px]" : "lg:ml-[260px]"}`}>
        <Header
          title={sectionTitle[activeSection]}
          subtitle={sectionSubtitle[activeSection]}
          collapsed={sidebarCollapsed}
          onMenuToggle={() => setMobileOpen(true)}
        />

        {banks.length > 0 && (
          <div className="border-b border-[var(--border)] bg-[var(--card)]/50">
            <div className="px-4 lg:px-6 py-2 flex items-center gap-4 text-xs text-[var(--muted-foreground)] overflow-x-auto">
              <span className="inline-flex items-center gap-1.5 shrink-0 font-semibold">
                <Icon name="database" className="w-3.5 h-3.5 text-[var(--primary)]" />
                Connected Banks
              </span>
              {banks.map(b => (
                <span key={b} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[var(--muted)] border border-[var(--border)] whitespace-nowrap text-[var(--foreground)] font-medium text-xs">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.4)]" />
                  {fmt(b)}
                </span>
              ))}
            </div>
          </div>
        )}

        <main className="px-4 lg:px-6 py-8 max-w-[1600px]">
          {activeSection === "dashboard" && <DashboardHome banks={banks} />}
          {activeSection === "migrate" && <MigrationSection />}
          {activeSection === "audit" && <AuditSection />}
          {activeSection === "banks" && <BanksSection />}
          {activeSection === "settings" && <SettingsSection />}
        </main>

        <footer className="border-t border-[var(--border)] bg-[var(--card)]/50" id="main-footer">
          <div className="px-4 lg:px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-[var(--muted-foreground)]">
            <span className="font-medium">&copy; {new Date().getFullYear()} UN Wallet — Multi-Bank Data Migration Platform v1.0.0</span>
            <div className="flex items-center gap-4">
              <span className="inline-flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.4)]" />
                <span className="font-semibold">Operational</span>
              </span>
              <span className="hidden sm:inline text-[var(--border)]">|</span>
              <span className="hidden sm:inline">Phase 1 — Confidential</span>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
