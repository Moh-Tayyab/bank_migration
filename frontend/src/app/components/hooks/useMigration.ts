"use client";
import { useState, useRef, useCallback, useEffect } from "react";
import { toast } from "../Toast";
import { API_BASE, MAX_FILE_SIZE, HISTORY_KEY, apiHeaders } from "../types";
import type { AuditEntry, ResultData, PreviewData, HistoryEntry } from "../types";

function loadHistory(): HistoryEntry[] {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); } catch { return []; }
}

function saveHistory(history: HistoryEntry[]) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 50)));
}

export function useMigration() {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [sourceBank, setSourceBank] = useState("source_bank");
  const [targetBanks, setTargetBanks] = useState<string[]>([]);
  const [detectedTarget, setDetectedTarget] = useState<string | null>(null);
  const [outputFormat, setOutputFormat] = useState("json");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ResultData | null>(null);
  const [multiResults, setMultiResults] = useState<ResultData[]>([]);
  const [auditTrail, setAuditTrail] = useState<AuditEntry[]>([]);
  const [banks, setBanks] = useState<string[]>([]);
  const [banksLoading, setBanksLoading] = useState(true);
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
    setBanksLoading(true);
    fetch(`${API_BASE}/banks`, { headers: apiHeaders() }).then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    }).then((d) => { setBanks(d.banks || []); }).catch(() => {
      toast("warning", "Could not connect to API server");
    }).finally(() => { setBanksLoading(false); });
    setHistory(loadHistory());
    return () => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
      if (abortRef.current) abortRef.current.abort();
    };
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

  const toggleTheme = useCallback(() => {
    setDark((prev) => {
      const next = !prev;
      document.documentElement.classList.toggle("dark", next);
      localStorage.setItem("theme", next ? "dark" : "light");
      return next;
    });
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
  }, []);

  const onFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      const f = e.target.files[0];
      if (f.size > MAX_FILE_SIZE) {
        toast("error", `File too large: ${(f.size / 1024 / 1024).toFixed(1)}MB. Max: ${MAX_FILE_SIZE / 1024 / 1024}MB`);
        return;
      }
      setFile(f);
      setPreview(null);
      toast("info", `File selected: ${f.name} (${(f.size / 1024).toFixed(1)}KB)`);
    }
  }, []);

  const handlePreview = useCallback(async () => {
    if (!file) return;
    setPreviewLoading(true);
    setPreview(null);
    const form = new FormData();
    form.append("file", file);
    form.append("row_limit", "10");
    try {
      const res = await fetch(`${API_BASE}/preview`, { method: "POST", body: form, headers: apiHeaders() });
      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        toast("error", errData?.detail || `Preview failed: HTTP ${res.status}`);
        return;
      }
      const data = await res.json();
      if (data.rows) {
        setPreview(data);
        // Auto-detect target bank
        if (data.detected_target_bank) {
          setDetectedTarget(data.detected_target_bank);
          setTargetBanks([data.detected_target_bank]);
          toast("success", `Preview loaded: ${data.row_count} rows, ${(data.total_columns || data.columns?.length)} columns. Target detected: ${fmt(data.detected_target_bank)}`);
        } else {
          setDetectedTarget(null);
          setTargetBanks([]);
          toast("warning", `Preview loaded, but no matching target bank schema found`);
        }
      }
    } catch {
      toast("error", "Failed to preview file");
    } finally {
      setPreviewLoading(false);
    }
  }, [file]);

  const toggleTargetBank = useCallback((bank: string) => {
    setTargetBanks((prev) => prev.includes(bank) ? prev.filter((b) => b !== bank) : [...prev, bank]);
  }, []);

  const pollTaskStatus = useCallback(async (taskId: string, bankCount: number) => {
    const MAX_POLLS = 150;
    let attempts = 0;
    abortRef.current = new AbortController();
    const signal = abortRef.current.signal;

    const poll = async () => {
      if (signal.aborted) return;
      attempts++;
      if (attempts > MAX_POLLS) {
        setPollingTask(null);
        setUploadProgress(null);
        toast("error", "Migration polling timed out.");
        return;
      }
      try {
        const res = await fetch(`${API_BASE}/status/${taskId}`, { signal, headers: apiHeaders() });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.status === "SUCCESS") {
          setPollingTask(null);
          setUploadProgress(null);
          const r = data.result;
          if (bankCount > 1 && r.results) {
            setMultiResults(r.results);
            setResult(null);
          } else {
            setResult(r);
            setMultiResults([]);
          }
          if (r.success) {
            toast("success", `Migration completed: ${r.processed} records processed`);
          } else {
            toast("error", `Migration failed: ${r.error || "Unknown error"}`);
            setErrMsg(r.error || "Migration failed");
          }
          const entry: HistoryEntry = {
            id: taskId, timestamp: new Date().toISOString(),
            sourceBank, targetBanks, outputFormat,
            totalRecords: r.total_records || 0, processed: r.processed || 0,
            failed: r.failed || 0, success: r.success,
            outputPaths: bankCount > 1 && r.results
              ? r.results.map((x: ResultData) => x.output_path || "").filter(Boolean)
              : [r.output_path].filter(Boolean),
          };
          setHistory((prev) => { const h = [entry, ...prev].slice(0, 50); saveHistory(h); return h; });
          return;
        }
        if (data.status === "FAILURE") {
          setPollingTask(null);
          setUploadProgress(null);
          setErrMsg(data.result?.error || "Background task failed");
          toast("error", "Background migration task failed");
          return;
        }
        if (data.status === "PENDING" || data.status === "STARTED") {
          setUploadProgress(30 + Math.min(attempts * 2, 60));
          pollTimerRef.current = setTimeout(poll, 2000);
        }
      } catch (err) {
        if (signal.aborted) return;
        pollTimerRef.current = setTimeout(poll, 3000);
      }
    };
    setPollingTask(taskId);
    setPollingBanks(bankCount);
    poll();
  }, [sourceBank, targetBanks, outputFormat]);

  const executeMigration = useCallback(async () => {
    if (!file || targetBanks.length === 0) return;
    setLoading(true);
    setResult(null);
    setMultiResults([]);
    setAuditTrail([]);
    setErrMsg("");
    setPreview(null);
    const form = new FormData();
    form.append("file", file);
    form.append("source_bank", sourceBank);
    form.append("target_banks", JSON.stringify(targetBanks));
    form.append("output_format", outputFormat);
    try {
      const res = await fetch(`${API_BASE}/migrate/upload`, { method: "POST", body: form, headers: apiHeaders() });
      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        toast("error", errData?.detail || `Upload failed: HTTP ${res.status}`);
        return;
      }
      const data = await res.json();
      if (data.task_id) {
        toast("info", "Migration queued. Polling for results...");
        pollTaskStatus(data.task_id, targetBanks.length);
      } else {
        const isMulti = Array.isArray(data.results);
        if (isMulti) setMultiResults(data.results);
        if (data.audit_trail) setAuditTrail(data.audit_trail);
        if (data.success) {
          const totalProcessed = isMulti
            ? (data.results as ResultData[]).reduce((sum: number, r: ResultData) => sum + (r.processed || 0), 0)
            : data.processed || 0;
          toast("success", `Migration completed: ${totalProcessed} records processed`);
          const entry: HistoryEntry = {
            id: Date.now().toString(), timestamp: new Date().toISOString(),
            sourceBank, targetBanks, outputFormat,
            totalRecords: data.total_records || (isMulti ? (data.results as ResultData[]).reduce((s: number, r: ResultData) => s + (r.total_records || 0), 0) : 0),
            processed: totalProcessed,
            failed: data.failed || (isMulti ? (data.results as ResultData[]).reduce((s: number, r: ResultData) => s + (r.failed || 0), 0) : 0),
            success: data.success,
            outputPaths: data.results
              ? (data.results as ResultData[]).map((x: ResultData) => x.output_path || "").filter(Boolean)
              : [data.output_path].filter(Boolean),
          };
          const newHistory = [entry, ...history].slice(0, 50);
          setHistory(newHistory);
          saveHistory(newHistory);
        } else {
          toast("error", data.error || "Migration failed");
          setErrMsg(data.error || "Migration failed");
        }
        setResult(isMulti ? null : data);
      }
    } catch (e: unknown) {
      toast("error", e instanceof Error ? e.message : "Connection failed");
      setErrMsg(e instanceof Error ? e.message : "Connection failed. Ensure the API server is running.");
    } finally {
      setLoading(false);
    }
  }, [file, sourceBank, targetBanks, outputFormat, history, pollTaskStatus]);

  const handleMigrate = useCallback(() => {
    if (!file || targetBanks.length === 0) return;
    setShowConfirm(true);
  }, [file, targetBanks]);

  const handleRetry = useCallback((entry: HistoryEntry) => {
    setSourceBank(entry.sourceBank);
    setTargetBanks(entry.targetBanks);
    setOutputFormat(entry.outputFormat);
    toast("info", "Configuration restored from history. Please re-select the source file.");
  }, []);

  const handleClearHistory = useCallback(() => {
    setHistory([]);
    saveHistory([]);
    toast("info", "Migration history cleared");
  }, []);

  const handleExportAudit = useCallback(async () => {
    if (auditTrail.length === 0) return;
    const migrationId = Date.now().toString();
    try {
      const res = await fetch(`${API_BASE}/audit/${migrationId}/export`, { headers: apiHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit_${migrationId}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast("success", "Audit trail exported as CSV");
    } catch {
      const esc = (v: string) => `"${v.replace(/"/g, '""')}"`;
      const csv = "timestamp,event,record_id,bank_pair,details\n" +
        auditTrail.map((e) => [e.timestamp, e.event, e.record_id, e.bank_pair, e.details].map(esc).join(",")).join("\n");
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit_${migrationId}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast("success", "Audit trail exported as CSV");
    }
  }, [auditTrail]);

  const pct = result && result.total_records > 0
    ? Math.round((result.processed / result.total_records) * 100)
    : pollingTask ? 50 : 0;
  const sourceColumns = preview?.columns || [];
  const pipelineStage = result ? "result" : pollingTask ? "migrate" : file ? "config" : "upload";

  return {
    file, dragOver, sourceBank, targetBanks, detectedTarget, outputFormat,
    result, multiResults, auditTrail, preview, banks, banksLoading,
    loading, previewLoading, pollingTask, uploadProgress, pollingBanks,
    errMsg, dark, showAudit, showTargetDropdown, showConfirm, history,
    pipelineStage, sourceColumns, pct,
    inputRef,
    setSourceBank, setOutputFormat, setDragOver, setPreview,
    setShowTargetDropdown, setShowConfirm, setShowAudit,
    onDrop, onFileSelect, handlePreview, toggleTargetBank,
    handleMigrate, executeMigration, handleRetry, handleClearHistory,
    handleExportAudit, toggleTheme,
    apiBase: API_BASE,
  };
}

export type MigrationHook = ReturnType<typeof useMigration>;
