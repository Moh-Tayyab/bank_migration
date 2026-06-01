"use client";
import { useState, useRef, useCallback, useEffect } from "react";
import { toast } from "../Toast";
import { API_BASE, MAX_FILE_SIZE, apiHeaders } from "../types";

export type SqlLdrResult = {
  success: boolean;
  script_filename: string;
  download_url: string;
  table_name: string;
  records_count: number;
  columns: string[];
  source_file: string;
};

export function useSqlLoader() {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SqlLdrResult | null>(null);
  const [preview, setPreview] = useState<{ columns: string[]; rows: Record<string, unknown>[]; row_count: number } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [errMsg, setErrMsg] = useState("");

  const inputRef = useRef<HTMLInputElement>(null);

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
      setResult(null);
      setErrMsg("");
      toast("info", `File selected: ${f.name} (${(f.size / 1024).toFixed(1)}KB)`);
    }
  }, []);

  const handlePreview = useCallback(async () => {
    if (!file) return;
    setPreviewLoading(true);
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
      setPreview({
        columns: data.columns || [],
        rows: data.rows || [],
        row_count: data.row_count || 0,
      });
      toast("success", `Preview loaded: ${data.row_count} rows, ${data.columns?.length || 0} columns`);
    } catch {
      toast("error", "Failed to preview file");
    } finally {
      setPreviewLoading(false);
    }
  }, [file]);

  const handleGenerateScript = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    setErrMsg("");

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/sqlldr/generate`, { method: "POST", body: form, headers: apiHeaders() });
      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        toast("error", errData?.detail || `Generation failed: HTTP ${res.status}`);
        setErrMsg(errData?.detail || `Generation failed: HTTP ${res.status}`);
        return;
      }
      const data = await res.json();
      if (data.success) {
        setResult(data);
        toast("success", `SQL*Loader script generated: ${data.table_name} (${data.records_count} records)`);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Connection failed";
      toast("error", msg);
      setErrMsg(msg);
    } finally {
      setLoading(false);
    }
  }, [file]);

  const handleDownloadScript = useCallback(() => {
    if (!result) return;
    const link = document.createElement("a");
    link.href = `${API_BASE}${result.download_url}`;
    link.download = result.script_filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast("success", "Script downloaded successfully");
  }, [result]);

  const handleReset = useCallback(() => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setErrMsg("");
    if (inputRef.current) inputRef.current.value = "";
  }, []);

  return {
    file, dragOver, preview, previewLoading, loading, result, errMsg, inputRef,
    setDragOver, onDrop, onFileSelect, handlePreview, handleGenerateScript, handleDownloadScript, handleReset,
    scriptFilename: result?.script_filename || null,
  };
}
