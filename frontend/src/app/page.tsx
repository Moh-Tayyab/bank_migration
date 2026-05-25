"use client";
import { useState, useRef, useCallback, useEffect } from "react";
import Icon from "./components/Icon";
import { toast, ToastProvider } from "./components/Toast";
import ConfirmationDialog from "./components/ConfirmationDialog";
import FilePreview from "./components/FilePreview";
import SchemaPreview from "./components/SchemaPreview";
import MigrationHistory from "./components/MigrationHistory";
import StatusBadge from "./components/StatusBadge";
import DownloadCommand from "./components/DownloadCommand";
import PipelineSteps from "./components/PipelineSteps";
import { API_BASE, MAX_FILE_SIZE, HISTORY_KEY, fmt } from "./components/types";
import type { AuditEntry, ResultData, PreviewData, HistoryEntry } from "./components/types";

function loadHistory(): HistoryEntry[] {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); } catch { return []; }
}

function saveHistory(history: HistoryEntry[]) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 50)));
}

function MigrationPageInner() {
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
  const [dark, setDark] = useState(false);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [pollingTask, setPollingTask] = useState<string | null>(null);
  const [pollingBanks, setPollingBanks] = useState<number>(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
    fetch(`${API_BASE}/banks`).then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    }).then((d) => setBanks(d.banks || [])).catch(() => {
      toast("warning", "Could not connect to API server");
    });
    setHistory(loadHistory());
    return () => { if (pollTimerRef.current) clearTimeout(pollTimerRef.current); if (abortRef.current) abortRef.current.abort(); };
  }, []);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest("#target-banks-select") && !target.closest("#target-banks-dropdown")) setShowTargetDropdown(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const toggleTheme = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
  }, []);

  const onFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      const f = e.target.files[0];
      if (f.size > MAX_FILE_SIZE) { toast("error", `File too large: ${(f.size / 1024 / 1024).toFixed(1)}MB. Max: ${MAX_FILE_SIZE / 1024 / 1024}MB`); return; }
      setFile(f); setPreview(null);
      toast("info", `File selected: ${f.name} (${(f.size / 1024).toFixed(1)}KB)`);
    }
  };

  const handlePreview = async () => {
    if (!file) return;
    setPreviewLoading(true); setPreview(null);
    const form = new FormData(); form.append("file", file); form.append("row_limit", "10");
    try {
      const res = await fetch(`${API_BASE}/preview`, { method: "POST", body: form });
      if (!res.ok) { const errData = await res.json().catch(() => null); toast("error", errData?.detail || `Preview failed: HTTP ${res.status}`); return; }
      const data = await res.json();
      if (data.rows) { setPreview(data); toast("success", `Preview loaded: ${data.row_count} rows, ${data.total_columns} columns`); }
    } catch { toast("error", "Failed to preview file"); } finally { setPreviewLoading(false); }
  };

  const toggleTargetBank = (bank: string) => {
    setTargetBanks((prev) => prev.includes(bank) ? prev.filter((b) => b !== bank) : [...prev, bank]);
  };

  const pollTaskStatus = useCallback(async (taskId: string, bankCount: number) => {
    const MAX_POLLS = 150; let attempts = 0;
    abortRef.current = new AbortController(); const signal = abortRef.current.signal;
    const poll = async () => {
      if (signal.aborted) return; attempts++;
      if (attempts > MAX_POLLS) { setPollingTask(null); setUploadProgress(null); toast("error", "Migration polling timed out."); return; }
      try {
        const res = await fetch(`${API_BASE}/status/${taskId}`, { signal });
        if (!res.ok) throw new Error(`HTTP ${res.status}`); const data = await res.json();
        if (data.status === "SUCCESS") {
          setPollingTask(null); setUploadProgress(null); const r = data.result;
          if (bankCount > 1 && r.results) { setMultiResults(r.results); setResult(null); } else { setResult(r); setMultiResults([]); }
          if (r.success) toast("success", `Migration completed: ${r.processed} records processed`);
          else { toast("error", `Migration failed: ${r.error || "Unknown error"}`); setErrMsg(r.error || "Migration failed"); }
          const entry: HistoryEntry = { id: taskId, timestamp: new Date().toISOString(), sourceBank, targetBanks, outputFormat, totalRecords: r.total_records || 0, processed: r.processed || 0, failed: r.failed || 0, success: r.success, outputPaths: bankCount > 1 && r.results ? r.results.map((x: ResultData) => x.output_path || "").filter(Boolean) : [r.output_path].filter(Boolean) };
          setHistory((prev) => { const h = [entry, ...prev].slice(0, 50); saveHistory(h); return h; }); return;
        }
        if (data.status === "FAILURE") { setPollingTask(null); setUploadProgress(null); setErrMsg(data.result?.error || "Background task failed"); toast("error", "Background migration task failed"); return; }
        if (data.status === "PENDING" || data.status === "STARTED") { setUploadProgress(30); pollTimerRef.current = setTimeout(poll, 2000); }
      } catch (err) { if (signal.aborted) return; pollTimerRef.current = setTimeout(poll, 3000); }
    };
    setPollingTask(taskId); setPollingBanks(bankCount); poll();
  }, [sourceBank, targetBanks, outputFormat]);

  const executeMigration = async () => {
    if (!file || targetBanks.length === 0) return;
    setLoading(true); setResult(null); setMultiResults([]); setAuditTrail([]); setErrMsg(""); setPreview(null);
    const form = new FormData();
    form.append("file", file); form.append("source_bank", sourceBank);
    form.append("target_banks", JSON.stringify(targetBanks)); form.append("output_format", outputFormat);
    try {
      const res = await fetch(`${API_BASE}/migrate/upload`, { method: "POST", body: form });
      if (!res.ok) { const errData = await res.json().catch(() => null); toast("error", errData?.detail || `Upload failed: HTTP ${res.status}`); return; }
      const data = await res.json();
      if (data.task_id) { toast("info", "Migration queued. Polling for results..."); pollTaskStatus(data.task_id, targetBanks.length); }
      else {
        if (data.results) setMultiResults(data.results);
        if (data.audit_trail) setAuditTrail(data.audit_trail);
        if (data.success) {
          toast("success", `Migration completed: ${data.processed} records processed`);
          const entry: HistoryEntry = { id: Date.now().toString(), timestamp: new Date().toISOString(), sourceBank, targetBanks, outputFormat, totalRecords: data.total_records || 0, processed: data.processed || 0, failed: data.failed || 0, success: data.success, outputPaths: data.results ? data.results.map((x: ResultData) => x.output_path || "").filter(Boolean) : [data.output_path].filter(Boolean) };
          const newHistory = [entry, ...history].slice(0, 50); setHistory(newHistory); saveHistory(newHistory);
        } else { toast("error", data.error || "Migration failed"); setErrMsg(data.error || "Migration failed"); }
        setResult(data);
      }
    } catch (e: unknown) { toast("error", e instanceof Error ? e.message : "Connection failed"); setErrMsg(e instanceof Error ? e.message : "Connection failed. Ensure the API server is running."); }
    finally { setLoading(false); }
  };

  const handleMigrate = () => { if (!file || targetBanks.length === 0) return; setShowConfirm(true); };
  const handleRetry = (entry: HistoryEntry) => { setSourceBank(entry.sourceBank); setTargetBanks(entry.targetBanks); setOutputFormat(entry.outputFormat); toast("info", "Configuration restored from history. Please re-select the source file."); };
  const handleClearHistory = () => { setHistory([]); saveHistory([]); toast("info", "Migration history cleared"); };

  const handleExportAudit = async () => {
    if (auditTrail.length === 0) return;
    const migrationId = Date.now().toString();
    try {
      const res = await fetch(`${API_BASE}/audit/${migrationId}/export`); const blob = await res.blob();
      const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = `audit_${migrationId}.csv`; a.click(); URL.revokeObjectURL(url);
      toast("success", "Audit trail exported as CSV");
    } catch {
      const escapeCsv = (v: string) => `"${v.replace(/"/g, '""')}"`;
      const csvContent = "timestamp,event,record_id,bank_pair,details\n" + auditTrail.map((e) => [e.timestamp, e.event, e.record_id, e.bank_pair, e.details].map(escapeCsv).join(",")).join("\n");
      const blob = new Blob([csvContent], { type: "text/csv" }); const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = `audit_${migrationId}.csv`; a.click(); URL.revokeObjectURL(url);
      toast("success", "Audit trail exported as CSV");
    }
  };

  const pct = result && result.total_records > 0 ? Math.round((result.processed / result.total_records) * 100) : pollingTask ? 50 : 0;
  const sourceColumns = preview?.columns || [];
  const pipelineStage = result ? "result" : pollingTask ? "migrate" : file ? "config" : "upload";

  return (
    <>
      <ConfirmationDialog open={showConfirm} title="Start Migration?" message={`Migrating from ${fmt(sourceBank)} to ${targetBanks.length} target bank(s) (${targetBanks.map(fmt).join(", ")}). Output format: ${outputFormat.toUpperCase()}. This action cannot be undone.`} confirmLabel="Start Migration" cancelLabel="Cancel" variant="warning" onConfirm={() => { setShowConfirm(false); executeMigration(); }} onCancel={() => setShowConfirm(false)} />

      <div className="min-h-screen relative overflow-hidden flex flex-col">
        <div className="orb orb-1" aria-hidden="true" />
        <div className="orb orb-2" aria-hidden="true" />

        {/* ── Header ─────────────────────────────────────────────── */}
        <header className="sticky top-0 z-30 bg-[var(--card)]/90 backdrop-blur-md border-b border-[var(--border)]">
          <div className="max-w-[1440px] mx-auto h-14 flex items-center justify-between px-4 lg:px-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-[var(--primary)] flex items-center justify-center text-white font-bold text-xs tracking-tight">
                UW
              </div>
              <div className="hidden sm:block">
                <h1 className="text-sm font-semibold text-[var(--foreground)] leading-tight">Data Migration</h1>
                <p className="text-[10px] text-[var(--muted-foreground)]">Secure multi-bank ETL pipeline</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <PipelineSteps current={pipelineStage} />
              <div className="w-px h-5 bg-[var(--border)] hidden sm:block" />
              <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--muted)] border border-[var(--border)] transition-all">
                <Icon name="external" className="w-3 h-3" />API Docs
              </a>
              <button onClick={toggleTheme} className="p-2 rounded-lg transition-all hover:bg-[var(--muted)] text-[var(--muted-foreground)] cursor-pointer" aria-label="Toggle theme">
                <div className={`transition-transform duration-200 ${dark ? "rotate-180" : "rotate-0"}`}>
                  {dark ? <Icon name="sun" className="w-4 h-4" /> : <Icon name="moon" className="w-4 h-4" />}
                </div>
              </button>
            </div>
          </div>
        </header>

        {/* ── Connected Banks Bar ────────────────────────────────── */}
        {banks.length > 0 && (
          <div className="border-b border-[var(--border)] bg-[var(--card)]/50">
            <div className="max-w-[1440px] mx-auto px-4 lg:px-6 py-2 flex items-center gap-3 text-[11px] text-[var(--muted-foreground)] overflow-x-auto">
              <span className="inline-flex items-center gap-1.5 shrink-0 font-semibold">
                <Icon name="database" className="w-3.5 h-3.5 text-[var(--primary)]" />
                Connected
              </span>
              {banks.map((b) => (
                <span key={b} className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-[var(--muted)] border border-[var(--border)] whitespace-nowrap text-[var(--foreground)] font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-[var(--success)]" />
                  {fmt(b)}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* ── Main Content ───────────────────────────────────────── */}
        <main className="flex-1 max-w-[1440px] mx-auto w-full px-4 lg:px-6 py-6">
          <MigrationHistory history={history} onClear={handleClearHistory} onRetry={handleRetry} />

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mt-6">
            {/* ── Left Column: Upload + Config ──────────────────── */}
            <div className="lg:col-span-4 space-y-5">
              {/* Upload Card */}
              <div className="card-elevated">
                <div className="px-5 py-3.5 border-b border-[var(--border)] flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-lg bg-[var(--primary-light)] flex items-center justify-center">
                    <Icon name="upload" className="w-3.5 h-3.5 text-[var(--primary)]" />
                  </div>
                  <h2 className="text-sm font-semibold text-[var(--foreground)]">Upload Data</h2>
                </div>
                <div className="p-5">
                  <div onDragOver={(e) => { e.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)} onDrop={onDrop} onClick={() => inputRef.current?.click()} className={`dropzone ${dragOver ? "active" : ""} ${file ? "has-file" : ""}`} id="file-dropzone">
                    <input ref={inputRef} type="file" onChange={onFileSelect} className="hidden" accept=".csv,.json,.docx,.xlsx,.xml,.txt" id="file-input" />
                    <div className="flex flex-col items-center gap-2.5">
                      <div className={`p-3 rounded-xl transition-all ${file ? "text-[var(--success)]" : dragOver ? "text-[var(--primary)]" : "text-[var(--muted-foreground)]"}`}>
                        {file ? <Icon name="check" className="w-6 h-6" /> : <Icon name="upload" className="w-6 h-6" />}
                      </div>
                      {file ? (
                        <div className="text-center">
                          <p className="text-sm font-semibold text-[var(--foreground)]">{file.name}</p>
                          <p className="text-[11px] text-[var(--muted-foreground)] mt-0.5">{(file.size / 1024).toFixed(1)} KB</p>
                        </div>
                      ) : (
                        <div className="text-center">
                          <p className="text-sm text-[var(--muted-foreground)]">
                            <span className="text-[var(--primary)] font-semibold cursor-pointer">Click to upload</span> or drag & drop
                          </p>
                          <p className="text-[11px] text-[var(--muted-foreground)] mt-0.5">CSV, JSON, DOCX, XLSX, XML, TXT</p>
                        </div>
                      )}
                    </div>
                  </div>
                  {file && (
                    <div className="mt-3 flex gap-2">
                      <button onClick={handlePreview} disabled={previewLoading} className="btn-secondary px-3 py-1.5 text-xs flex items-center gap-1.5 cursor-pointer" type="button">
                        <Icon name="search" className="w-3.5 h-3.5" />
                        {previewLoading ? "Loading..." : "Preview"}
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Config Card */}
              <div className="card-elevated">
                <div className="px-5 py-3.5 border-b border-[var(--border)] flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-lg bg-[var(--primary-light)] flex items-center justify-center">
                    <Icon name="settings" className="w-3.5 h-3.5 text-[var(--primary)]" />
                  </div>
                  <h2 className="text-sm font-semibold text-[var(--foreground)]">Configuration</h2>
                </div>
                <div className="p-5 space-y-4">
                  <div>
                    <label className="block text-[11px] font-semibold text-[var(--muted-foreground)] mb-1.5 uppercase tracking-wider">Source Bank</label>
                    <div className="relative">
                      <select value={sourceBank} onChange={(e) => setSourceBank(e.target.value)} className="select-field" id="source-bank-select">
                        {banks.length > 0 ? banks.map((b) => <option key={b} value={b}>{fmt(b)}</option>) : <option value="source_bank">Source Bank</option>}
                      </select>
                      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
                        <Icon name="chevron" className="w-4 h-4 text-[var(--muted-foreground)]" />
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-[var(--muted-foreground)] mb-1.5 uppercase tracking-wider">Target Banks</label>
                    <div className="relative">
                      <button onClick={() => setShowTargetDropdown(!showTargetDropdown)} className="select-field text-left flex items-center justify-between w-full" id="target-banks-select" type="button">
                        <span className={targetBanks.length === 0 ? "text-[var(--muted-foreground)]" : ""}>
                          {targetBanks.length === 0 ? "Select target banks..." : `${targetBanks.length} bank(s) selected`}
                        </span>
                        <Icon name="chevron" className={`w-4 h-4 text-[var(--muted-foreground)] transition-transform ${showTargetDropdown ? "rotate-180" : ""}`} />
                      </button>
                      {showTargetDropdown && (
                        <div id="target-banks-dropdown" className="absolute z-20 mt-1 w-full rounded-xl bg-[var(--card)] border border-[var(--border)] shadow-lg p-1.5 space-y-0.5 max-h-48 overflow-y-auto">
                          {(banks.length > 0 ? banks : ["source_bank", "target_bank"]).map((b) => (
                            <label key={b} className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-[var(--muted)] cursor-pointer transition-colors">
                              <input type="checkbox" checked={targetBanks.includes(b)} onChange={() => toggleTargetBank(b)} className="w-4 h-4 rounded border-[var(--border)] text-[var(--primary)] focus:ring-[var(--primary)]" />
                              <span className="text-sm font-medium text-[var(--foreground)]">{fmt(b)}</span>
                            </label>
                          ))}
                        </div>
                      )}
                    </div>
                    {targetBanks.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {targetBanks.map((b) => (
                          <span key={b} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[var(--primary-light)] text-[var(--primary)] text-[11px] font-semibold">
                            {fmt(b)}
                            <button onClick={() => toggleTargetBank(b)} className="hover:opacity-70 cursor-pointer">
                              <Icon name="close" className="w-2.5 h-2.5" />
                            </button>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-[var(--muted-foreground)] mb-1.5 uppercase tracking-wider">Output Format</label>
                    <div className="grid grid-cols-5 gap-1.5">
                      {["json", "csv", "docx", "xlsx", "html"].map((f) => (
                        <button key={f} onClick={() => setOutputFormat(f)} className={`format-btn ${outputFormat === f ? "active" : ""}`} id={`format-${f}`} type="button">
                          {f.toUpperCase()}
                        </button>
                      ))}
                    </div>
                  </div>

                  <button onClick={handleMigrate} disabled={!file || targetBanks.length === 0 || loading} className="btn-primary w-full h-11 text-sm flex items-center justify-center gap-2 cursor-pointer" id="migrate-btn" type="button">
                    {loading ? (
                      <span className="flex items-center gap-2">
                        <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>{pollingTask ? `Polling (${pollingBanks} bank(s))` : "Migrating..."}</span>
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <Icon name="arrow" className="w-4 h-4" />
                        Migrate Data
                      </span>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* ── Right Column: Results ─────────────────────────── */}
            <div className="lg:col-span-8 space-y-5">
              {errMsg && (
                <div className="card border-[var(--error)]/30 animate-scale-in" style={{ background: "var(--error-light)" }}>
                  <div className="p-4 flex items-start gap-3">
                    <div className="p-1.5 rounded-lg bg-[var(--error)]/10 shrink-0">
                      <Icon name="xmark" className="w-4 h-4 text-[var(--error)]" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-[var(--error)]">Migration Error</p>
                      <p className="text-xs text-[var(--error)]/80 mt-0.5 leading-relaxed">{errMsg}</p>
                    </div>
                  </div>
                </div>
              )}

              {pollingTask && (
                <div className="card-elevated animate-scale-in">
                  <div className="px-5 py-3.5 border-b border-[var(--border)] flex items-center gap-3">
                    <span className="w-4 h-4 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
                    <div>
                      <h3 className="text-sm font-semibold text-[var(--foreground)]">Processing in Background</h3>
                      <p className="text-[11px] text-[var(--muted-foreground)]">Polling for task completion...</p>
                    </div>
                  </div>
                  <div className="p-5 space-y-3">
                    <div className="progress-track">
                      <div className="progress-fill animate-pulse" style={{ width: `${uploadProgress || 30}%` }} />
                    </div>
                    <p className="text-[11px] text-[var(--muted-foreground)] font-mono">Task: {pollingTask}</p>
                  </div>
                </div>
              )}

              {preview && (
                <FilePreview filename={preview.filename} format={preview.format} columns={preview.columns} rows={preview.rows} rowCount={preview.row_count} onClose={() => setPreview(null)} />
              )}

              {sourceColumns.length > 0 && targetBanks.length > 0 && (
                <SchemaPreview sourceBank={sourceBank} targetBanks={targetBanks} sourceColumns={sourceColumns} banks={banks} apiBase={API_BASE} />
              )}

              {/* Multi-Bank Results */}
              {multiResults.length > 0 && (
                <div className="space-y-4 animate-scale-in">
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded-lg bg-[var(--success-light)] flex items-center justify-center">
                      <Icon name="check" className="w-4 h-4 text-[var(--success)]" />
                    </div>
                    <h3 className="text-sm font-semibold text-[var(--foreground)]">Multi-Bank Migration Completed</h3>
                  </div>
                  <div className="grid gap-4">
                    {multiResults.map((r, idx) => (
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
                                <a href={`${API_BASE}/download/${r.output_path.split("/").pop()}`} className="text-[11px] font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)] flex items-center gap-1 transition-colors" download>
                                  <Icon name="download" className="w-3 h-3" />Download
                                </a>
                                <DownloadCommand filename={r.output_path.split("/").pop()!} apiBase={API_BASE} />
                              </>
                            )}
                            <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md ${r.success ? "bg-[var(--success-light)] text-[var(--success)]" : "bg-[var(--error-light)] text-[var(--error)]"}`}>
                              {r.success ? "Success" : "Failed"}
                            </span>
                          </div>
                        </div>
                        <div className="p-4 grid grid-cols-3 gap-4">
                          <div><p className="text-[11px] text-[var(--muted-foreground)]">Total</p><p className="text-lg font-bold text-[var(--foreground)]">{r.total_records}</p></div>
                          <div><p className="text-[11px] text-[var(--muted-foreground)]">Processed</p><p className="text-lg font-bold text-[var(--success)]">{r.processed}</p></div>
                          <div><p className="text-[11px] text-[var(--muted-foreground)]">Failed</p><p className="text-lg font-bold text-[var(--error)]">{r.failed}</p></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Single Result */}
              {result && multiResults.length === 0 && (
                <div className="card-elevated animate-scale-in" key={result.success ? "success" : "fail"}>
                  <div className="px-5 py-3.5 border-b border-[var(--border)] flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${result.success ? "bg-[var(--success-light)]" : "bg-[var(--error-light)]"}`}>
                        {result.success ? <Icon name="check" className="w-4 h-4 text-[var(--success)]" /> : <Icon name="xmark" className="w-4 h-4 text-[var(--error)]" />}
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-[var(--foreground)]">Migration {result.success ? "Completed" : "Failed"}</h3>
                        {result.success && result.output_path && <p className="text-[11px] text-[var(--muted-foreground)] font-mono mt-0.5">{result.output_path.split("/").pop()}</p>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {result.success && result.output_path && (
                        <>
                          <a href={`${API_BASE}/download/${result.output_path.split("/").pop()}`} className="text-[11px] font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)] flex items-center gap-1 transition-colors" download>
                            <Icon name="download" className="w-3 h-3" />Download
                          </a>
                          <DownloadCommand filename={result.output_path.split("/").pop()!} apiBase={API_BASE} />
                        </>
                      )}
                      {result.success && <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-[var(--success-light)] text-[var(--success)]">Success</span>}
                    </div>
                  </div>
                  <div className="p-5 space-y-5">
                    <div className="grid grid-cols-3 gap-3">
                      <div className="stat-card">
                        <p className="text-[11px] text-[var(--muted-foreground)] font-medium mb-1">Total Records</p>
                        <p className="text-xl font-bold text-[var(--foreground)]">{result.total_records.toLocaleString()}</p>
                      </div>
                      <div className="stat-card">
                        <p className="text-[11px] text-[var(--muted-foreground)] font-medium mb-1">Processed</p>
                        <p className="text-xl font-bold text-[var(--success)]">{result.processed.toLocaleString()}</p>
                      </div>
                      <div className="stat-card">
                        <p className="text-[11px] text-[var(--muted-foreground)] font-medium mb-1">Failed</p>
                        <p className="text-xl font-bold text-[var(--error)]">{result.failed.toLocaleString()}</p>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-[var(--muted-foreground)] font-medium">Completion</span>
                        <span className="font-bold text-[var(--foreground)]">{pct}%</span>
                      </div>
                      <div className="progress-track">
                        <div className="progress-fill" style={{ width: `${pct}%` }} />
                      </div>
                      <p className="text-[11px] text-[var(--muted-foreground)]">{result.processed}/{result.total_records} records</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Audit Trail */}
              {auditTrail.length > 0 && (
                <div className="card-elevated animate-slide-up">
                  <div className="px-5 py-3.5 border-b border-[var(--border)] flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-lg bg-[var(--primary-light)] flex items-center justify-center">
                        <Icon name="audit" className="w-3.5 h-3.5 text-[var(--primary)]" />
                      </div>
                      <h3 className="text-sm font-semibold text-[var(--foreground)]">Audit Trail</h3>
                      <span className="px-1.5 py-0.5 rounded-md bg-[var(--primary-light)] text-[var(--primary)] text-[10px] font-bold">{auditTrail.length}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button onClick={handleExportAudit} className="text-[11px] font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)] transition-colors flex items-center gap-1 cursor-pointer">
                        <Icon name="download" className="w-3 h-3" />Export
                      </button>
                      <button onClick={() => setShowAudit(!showAudit)} className="text-[11px] font-semibold text-[var(--primary)] hover:text-[var(--primary-hover)] transition-colors cursor-pointer" id="toggle-audit">
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
                            <td className="hidden md:table-cell text-xs text-[var(--muted-foreground)] whitespace-nowrap">{new Date(e.timestamp).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" })}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Empty State */}
              {!result && !errMsg && !pollingTask && (
                <div className="card-elevated p-10 flex flex-col items-center justify-center text-center min-h-[380px]">
                  <div className="w-14 h-14 rounded-2xl bg-[var(--primary-light)] flex items-center justify-center mb-5">
                    <Icon name="layers" className="w-7 h-7 text-[var(--primary)]" />
                  </div>
                  <h3 className="text-base font-semibold text-[var(--foreground)]">Ready to Migrate</h3>
                  <p className="text-sm text-[var(--muted-foreground)] max-w-sm mt-2 leading-relaxed">
                    Upload a data file, configure source and target banks, then click <span className="font-semibold text-[var(--foreground)]">Migrate Data</span> to start the pipeline.
                  </p>
                  <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
                    {[
                      { icon: "zap", label: "400 rec/s" },
                      { icon: "shield", label: "AES-256" },
                      { icon: "audit", label: "ACID rollback" },
                    ].map((f) => (
                      <span key={f.label} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[var(--muted)] border border-[var(--border)] text-[11px] text-[var(--muted-foreground)] font-medium">
                        <Icon name={f.icon} className="w-3 h-3 text-[var(--primary)]" />
                        {f.label}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </main>

        {/* ── Footer ─────────────────────────────────────────────── */}
        <footer className="border-t border-[var(--border)] bg-[var(--card)]/50 mt-auto">
          <div className="max-w-[1440px] mx-auto px-4 lg:px-6 py-3 flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px] text-[var(--muted-foreground)]">
            <span className="font-medium">&copy; {new Date().getFullYear()} UN Wallet — Multi-Bank Data Migration Platform v1.0.0</span>
            <div className="flex items-center gap-3">
              <span className="inline-flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--success)]" />
                <span className="font-semibold">Operational</span>
              </span>
              <span className="hidden sm:inline text-[var(--border)]">|</span>
              <span className="hidden sm:inline">Phase 1 — Confidential</span>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
}

export default function MigrationPage() {
  return (
    <ToastProvider>
      <MigrationPageInner />
    </ToastProvider>
  );
}
