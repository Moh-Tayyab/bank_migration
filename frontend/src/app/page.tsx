"use client";
import { useState, useRef, useCallback, useEffect } from "react";
import { Icn } from "./icons";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

type AuditEntry = { event: string; record_id: string; bank_pair: string; details: string; timestamp: string };
type ResultData = { success: boolean; total_records: number; processed: number; failed: number; output_path: string | null; error: string | null };

function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => { setDark(document.documentElement.classList.contains("dark")); }, []);
  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  };
  return (
    <button onClick={toggle} className="relative p-2.5 rounded-xl hover:bg-[var(--accent)] transition-all duration-300 focus:outline-none group" aria-label="Toggle theme" id="theme-toggle">
      <div className={`transition-all duration-500 ${dark ? "rotate-180 scale-110" : "rotate-0"}`}>
        {dark ? <Icn name="sun" className="w-[18px] h-[18px] text-amber-400" /> : <Icn name="moon" className="w-[18px] h-[18px] text-[var(--muted-foreground)] group-hover:text-[var(--primary)]" />}
      </div>
    </button>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; text: string; label: string }> = {
    INPUT_RECEIVED: { bg: "bg-blue-500/10 ring-blue-500/20", text: "text-blue-600 dark:text-blue-400", label: "Received" },
    VALIDATION: { bg: "bg-purple-500/10 ring-purple-500/20", text: "text-purple-600 dark:text-purple-400", label: "Validated" },
    MAPPING: { bg: "bg-indigo-500/10 ring-indigo-500/20", text: "text-indigo-600 dark:text-indigo-400", label: "Mapped" },
    TRANSFORM: { bg: "bg-cyan-500/10 ring-cyan-500/20", text: "text-cyan-600 dark:text-cyan-400", label: "Transformed" },
    SECURITY_MASK: { bg: "bg-amber-500/10 ring-amber-500/20", text: "text-amber-600 dark:text-amber-400", label: "Masked" },
    COMMITTED: { bg: "bg-emerald-500/10 ring-emerald-500/20", text: "text-emerald-600 dark:text-emerald-400", label: "Committed" },
    ROLLED_BACK: { bg: "bg-red-500/10 ring-red-500/20", text: "text-red-600 dark:text-red-400", label: "Rolled Back" },
    ERROR: { bg: "bg-red-500/10 ring-red-500/20", text: "text-red-600 dark:text-red-400", label: "Error" },
    OUTPUT_GENERATED: { bg: "bg-emerald-500/10 ring-emerald-500/20", text: "text-emerald-600 dark:text-emerald-400", label: "Output" },
  };
  const s = map[status] || { bg: "bg-gray-500/10 ring-gray-500/20", text: "text-gray-600 dark:text-gray-400", label: status };
  return <span className={`badge ${s.bg} ${s.text} ring-1 ring-inset`}>{s.label}</span>;
}

function StatCard({ value, label, icon, color }: { value: number; label: string; icon: string; color: string }) {
  return (
    <div className="stat-card">
      <div className={`inline-flex items-center justify-center w-10 h-10 rounded-xl mb-3 ${color.replace("text-", "bg-").replace("600", "500/10").replace("400", "400/10")}`}>
        <Icn name={icon} className={`w-5 h-5 ${color}`} />
      </div>
      <p className={`text-3xl font-bold tracking-tight ${color}`}>{value.toLocaleString()}</p>
      <p className="text-xs text-[var(--muted-foreground)] mt-1 font-medium">{label}</p>
    </div>
  );
}

export default function Dashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [sourceBank, setSourceBank] = useState("source_bank");
  const [targetBank, setTargetBank] = useState("target_bank");
  const [outputFormat, setOutputFormat] = useState("json");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ResultData | null>(null);
  const [auditTrail, setAuditTrail] = useState<AuditEntry[]>([]);
  const [banks, setBanks] = useState<string[]>([]);
  const [showAudit, setShowAudit] = useState(false);
  const [errMsg, setErrMsg] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch(`${API_BASE}/banks`).then(r => r.json()).then(d => setBanks(d.banks || [])).catch(() => {});
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
  }, []);

  const onFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) setFile(e.target.files[0]);
  };

  const handleMigrate = async () => {
    if (!file) return;
    setLoading(true); setResult(null); setAuditTrail([]); setErrMsg("");
    const form = new FormData();
    form.append("file", file); form.append("source_bank", sourceBank);
    form.append("target_bank", targetBank); form.append("output_format", outputFormat);
    try {
      const res = await fetch(`${API_BASE}/migrate/upload`, { method: "POST", body: form });
      const ct = res.headers.get("content-type") || "";
      if (ct.includes("application/json")) {
        const data = await res.json();
        setResult(data);
        if (data.audit_trail) setAuditTrail(data.audit_trail);
        if (!data.success) setErrMsg(data.error || "Migration failed");
      } else if (ct.includes("octet-stream")) {
        const header = res.headers.get("X-Migration-Result");
        if (header) { try { setResult(JSON.parse(header)); } catch {} }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = `migration_${targetBank}.${outputFormat}`; a.click();
        URL.revokeObjectURL(url);
      }
    } catch (e: unknown) {
      setErrMsg(e instanceof Error ? e.message : "Connection failed. Ensure the API server is running.");
    } finally { setLoading(false); }
  };

  const fmt = (name: string) => name.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  const pct = result && result.total_records > 0 ? Math.round((result.processed / result.total_records) * 100) : 0;

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Background orbs */}
      <div className="orb orb-1" aria-hidden="true" />
      <div className="orb orb-2" aria-hidden="true" />

      {/* ── Header ── */}
      <header className="sticky top-0 z-50 border-b border-[var(--border)] glass" id="main-header">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3.5">
              <div className="relative w-10 h-10 rounded-2xl flex items-center justify-center text-white font-bold text-sm overflow-hidden" style={{background: "var(--gradient-brand)"}}>
                <span className="relative z-10">UW</span>
                <div className="absolute inset-0 bg-white/10 animate-spin-slow" style={{background:"conic-gradient(from 0deg, transparent 0%, rgba(255,255,255,0.15) 25%, transparent 50%)"}} />
              </div>
              <div className="hidden sm:block">
                <h1 className="text-sm font-bold leading-tight text-[var(--foreground)] tracking-tight">UN Wallet</h1>
                <p className="text-[11px] text-[var(--muted-foreground)] leading-tight tracking-widest uppercase">Data Migration</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <a href="http://localhost:8000/docs" target="_blank" id="api-docs-link"
                className="hidden sm:inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-xl border border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--accent)] hover:border-[var(--primary)] transition-all duration-300">
                <Icn name="gear" className="w-3.5 h-3.5" /> API Docs
              </a>
              <div className="w-px h-6 bg-[var(--border)] mx-1" />
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      {/* ── Connected Banks Banner ── */}
      {banks.length > 0 && (
        <div className="border-b border-[var(--border)] bg-[var(--card)]/50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5 flex items-center gap-4 text-xs text-[var(--muted-foreground)] overflow-x-auto">
            <Icn name="database" className="w-3.5 h-3.5 shrink-0 text-[var(--primary)]" />
            <span className="shrink-0 font-semibold">Connected:</span>
            {banks.map(b => (
              <span key={b} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[var(--muted)] border border-[var(--border)] whitespace-nowrap text-[var(--foreground)] font-medium">
                <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.4)]" />
                {fmt(b)}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Main ── */}
      <main className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {/* Page title */}
        <div className="mb-10 animate-fade-in">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-xl bg-[var(--primary-light)]">
              <Icn name="sparkle" className="w-5 h-5 text-[var(--primary)]" />
            </div>
            <h2 className="text-2xl font-bold text-[var(--foreground)] tracking-tight">Data Migration</h2>
          </div>
          <p className="text-sm text-[var(--muted-foreground)] ml-[52px]">Upload source data, configure the ETL pipeline, and execute secure multi-bank migrations</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
          {/* ── Left Column ── */}
          <div className="lg:col-span-2 space-y-6">

            {/* Upload Card */}
            <div className="glass-card-elevated animate-slide-up">
              <div className="px-6 py-4 border-b border-[var(--border)] flex items-center gap-2.5">
                <div className="p-1.5 rounded-lg bg-[var(--primary-light)]">
                  <Icn name="upload" className="w-4 h-4 text-[var(--primary)]" />
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
                    <div className={`p-4 rounded-2xl transition-all duration-300 ${file ? "bg-[var(--primary)]/10 text-[var(--primary)] shadow-[var(--shadow-glow)]" : dragOver ? "bg-[var(--primary)]/10 text-[var(--primary)]" : "bg-[var(--muted)] text-[var(--muted-foreground)]"}`}>
                      {file ? <Icn name="file" className="w-8 h-8" /> : <Icn name="upload" className="w-8 h-8" />}
                    </div>
                    {file ? (
                      <div className="space-y-1">
                        <p className="text-sm font-semibold text-[var(--foreground)]">{file.name}</p>
                        <p className="text-xs text-[var(--muted-foreground)]">{(file.size / 1024).toFixed(1)} KB &middot; Click to change</p>
                      </div>
                    ) : (
                      <div className="space-y-1">
                        <p className="text-sm font-medium"><span className="text-[var(--primary)] font-semibold">Click to upload</span> or drag and drop</p>
                        <p className="text-xs text-[var(--muted-foreground)]">CSV, JSON, DOCX, XLSX, XML, TXT &bull; up to 10MB</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Config Card */}
            <div className="glass-card-elevated animate-slide-up stagger-2">
              <div className="px-6 py-4 border-b border-[var(--border)] flex items-center gap-2.5">
                <div className="p-1.5 rounded-lg bg-[var(--primary-light)]">
                  <Icn name="bank" className="w-4 h-4 text-[var(--primary)]" />
                </div>
                <h3 className="text-sm font-bold text-[var(--foreground)]">Pipeline Configuration</h3>
              </div>
              <div className="p-6 space-y-5">
                {/* Source Bank */}
                <div>
                  <label className="block text-xs font-semibold text-[var(--muted-foreground)] mb-2 uppercase tracking-wider">Source Bank</label>
                  <div className="relative">
                    <select value={sourceBank} onChange={e => setSourceBank(e.target.value)} className="select-field" id="source-bank-select">
                      {banks.length > 0
                        ? banks.map(b => <option key={b} value={b}>{fmt(b)}</option>)
                        : <option value="source_bank">Source Bank</option>}
                    </select>
                    <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
                      <Icn name="chevron" className="w-4 h-4 text-[var(--muted-foreground)]" />
                    </div>
                  </div>
                </div>

                {/* Target Bank */}
                <div>
                  <label className="block text-xs font-semibold text-[var(--muted-foreground)] mb-2 uppercase tracking-wider">Target Bank</label>
                  <div className="relative">
                    <select value={targetBank} onChange={e => setTargetBank(e.target.value)} className="select-field" id="target-bank-select">
                      {banks.length > 0
                        ? banks.map(b => <option key={b} value={b}>{fmt(b)}</option>)
                        : <option value="target_bank">Target Bank</option>}
                    </select>
                    <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
                      <Icn name="chevron" className="w-4 h-4 text-[var(--muted-foreground)]" />
                    </div>
                  </div>
                </div>

                {/* Output Format */}
                <div>
                  <label className="block text-xs font-semibold text-[var(--muted-foreground)] mb-2 uppercase tracking-wider">Output Format</label>
                  <div className="grid grid-cols-5 gap-2">
                    {["json", "csv", "docx", "xlsx", "html"].map(f => (
                      <button key={f} onClick={() => setOutputFormat(f)} className={`format-btn ${outputFormat === f ? "active" : ""}`} id={`format-${f}`}>
                        {f.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Migrate Button */}
                <button onClick={handleMigrate} disabled={!file || loading} className="btn-primary w-full h-12 text-sm flex items-center justify-center gap-2.5" id="migrate-btn">
                  {loading ? (
                    <span className="flex items-center gap-2.5">
                      <span className="flex gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse-dot d1" />
                        <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse-dot d2" />
                        <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse-dot d3" />
                      </span>
                      <span>Processing...</span>
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <Icn name="arrow" className="w-4 h-4" />
                      <span>Migrate Data</span>
                    </span>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* ── Right Column ── */}
          <div className="lg:col-span-3 space-y-6">
            {/* Error */}
            {errMsg && (
              <div className="glass-card border-red-500/30 dark:border-red-500/20 animate-scale-in" style={{background:"var(--error-light)"}}>
                <div className="p-5 flex items-start gap-3">
                  <div className="p-2 rounded-xl bg-red-500/10 shrink-0">
                    <Icn name="xmark" className="w-5 h-5 text-red-500" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-red-700 dark:text-red-300">Migration Error</p>
                    <p className="text-xs text-red-600 dark:text-red-400 mt-1 leading-relaxed">{errMsg}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Result */}
            {result && (
              <div className="glass-card-elevated animate-slide-up">
                <div className="px-6 py-4 border-b border-[var(--border)] flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-xl ${result.success ? "bg-emerald-500/10" : "bg-red-500/10"}`}>
                      {result.success
                        ? <Icn name="check" className="w-5 h-5 text-emerald-500" />
                        : <Icn name="xmark" className="w-5 h-5 text-red-500" />}
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-[var(--foreground)]">
                        Migration {result.success ? "Successful" : "Failed"}
                      </h3>
                      {result.success && result.output_path && (
                        <p className="text-xs text-[var(--muted-foreground)] mt-0.5 font-mono">{result.output_path.split("/").pop()}</p>
                      )}
                    </div>
                  </div>
                </div>
                <div className="p-6 space-y-6">
                  <div className="grid grid-cols-3 gap-4">
                    <StatCard value={result.total_records} label="Total Records" icon="database" color="text-indigo-600 dark:text-indigo-400" />
                    <StatCard value={result.processed} label="Processed" icon="check" color="text-emerald-600 dark:text-emerald-400" />
                    <StatCard value={result.failed} label="Failed" icon="xmark" color="text-red-600 dark:text-red-400" />
                  </div>
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-[var(--muted-foreground)] font-medium">Completion</span>
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

            {/* Audit Trail */}
            {result && auditTrail.length > 0 && (
              <div className="glass-card-elevated animate-slide-up stagger-3">
                <div className="px-6 py-4 border-b border-[var(--border)] flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="p-1.5 rounded-lg bg-[var(--primary-light)]">
                      <Icn name="audit" className="w-4 h-4 text-[var(--primary)]" />
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
                        <th>Record</th>
                        <th className="hidden sm:table-cell">Details</th>
                        <th className="hidden md:table-cell">Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditTrail.map((e, i) => (
                        <tr key={i}>
                          <td><StatusBadge status={e.event} /></td>
                          <td className="text-xs font-mono text-[var(--muted-foreground)]">{e.record_id || "\u2014"}</td>
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

            {/* Empty State */}
            {!result && !errMsg && (
              <div className="glass-card-elevated p-14 flex flex-col items-center justify-center text-center animate-fade-in">
                <div className="relative mb-6">
                  <div className="p-5 rounded-3xl bg-gradient-to-br from-[var(--primary-light)] to-[var(--accent)]">
                    <Icn name="layers" className="w-10 h-10 text-[var(--primary)]" />
                  </div>
                  <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-[var(--primary)] animate-pulse-dot d1" />
                </div>
                <h3 className="text-lg font-bold text-[var(--foreground)]">Ready to Migrate</h3>
                <p className="text-sm text-[var(--muted-foreground)] max-w-md mt-2 leading-relaxed">
                  Upload a data file, configure source and target banks, then click <span className="font-semibold text-[var(--foreground)]">Migrate Data</span> to start the ETL pipeline.
                </p>
                <div className="mt-8 flex flex-wrap items-center justify-center gap-6 text-xs text-[var(--muted-foreground)]">
                  {[
                    { icon: "database", label: "400 rec/s throughput", dot: "bg-emerald-500" },
                    { icon: "shield", label: "AES-256 encrypted", dot: "bg-indigo-500" },
                    { icon: "audit", label: "ACID rollback", dot: "bg-amber-500" },
                  ].map(f => (
                    <span key={f.label} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--muted)] border border-[var(--border-subtle)]">
                      <span className={`w-2 h-2 rounded-full ${f.dot} shadow-[0_0_6px_rgba(0,0,0,0.15)]`} />
                      <span className="font-medium">{f.label}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="relative border-t border-[var(--border)] mt-16 bg-[var(--card)]/50" id="main-footer">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-[var(--muted-foreground)]">
          <span className="font-medium">&copy; {new Date().getFullYear()} UN Wallet &mdash; Multi-Bank Data Migration Platform v1.0.0</span>
          <span className="flex items-center gap-4">
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.4)]" />
              <span className="font-semibold">Operational</span>
            </span>
            <span className="hidden sm:inline text-[var(--border)]">|</span>
            <span className="hidden sm:inline">Phase 1 &middot; Confidential</span>
          </span>
        </div>
      </footer>
    </div>
  );
}
