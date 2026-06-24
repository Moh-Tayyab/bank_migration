"use client";
import { useState, useRef, useCallback } from "react";
import { toast } from "../Toast";
import { API_BASE, MAX_FILE_SIZE, apiHeaders } from "../types";

export type SqlLdrResult = {
  success: boolean;
  script_filename: string;
  download_url: string;
  source_columns: string[];
  target_columns: string[];
  mappings_applied: number;
  source_file: string;
  records_count: number;
  cmd_windows: string;
  cmd_linux: string;
};

export type Mapping = { source: string; target: string };

export function useSqlLoader() {
  const [file, setFile] = useState<File | null>(null);
  const [targetFile, setTargetFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [targetDragOver, setTargetDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SqlLdrResult | null>(null);
  const [preview, setPreview] = useState<{ columns: string[]; rows: Record<string, string | number>[]; row_count: number } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [targetPreview, setTargetPreview] = useState<{ columns: string[]; sample_values: Record<string, unknown>; file_id: string } | null>(null);
  const [targetPreviewLoading, setTargetPreviewLoading] = useState(false);
  const [customMappings, setCustomMappings] = useState<Mapping[]>([]);
  const [outputFormat, setOutputFormat] = useState<"csv" | "json" | "html" | "xlsx">("csv");
  const [errMsg, setErrMsg] = useState("");

  const inputRef = useRef<HTMLInputElement>(null);
  const targetInputRef = useRef<HTMLInputElement>(null);

  const autoPreviewFile = useCallback(async (f: File) => {
    setPreviewLoading(true);
    setPreview(null);
    const form = new FormData();
    form.append("file", f);
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
        setPreview({
          columns: data.columns || [],
          rows: data.rows || [],
          row_count: data.row_count || 0,
        });
        toast("success", `Source: ${data.row_count} rows, ${data.total_columns || data.columns?.length} columns`);
      }
    } catch {
      toast("error", "Failed to preview source file");
    } finally {
      setPreviewLoading(false);
    }
  }, []);

  const autoParseTarget = useCallback(async (f: File) => {
    setTargetPreviewLoading(true);
    setTargetPreview(null);
    const form = new FormData();
    form.append("file", f);
    try {
      const res = await fetch(`${API_BASE}/schema/upload-target`, { method: "POST", body: form, headers: apiHeaders() });
      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        toast("error", errData?.detail || `Target parse failed: HTTP ${res.status}`);
        return;
      }
      const data = await res.json();
      setTargetPreview(data);
      toast("success", `Target: ${data.columns.length} columns detected`);

      if (preview?.columns && data.columns.length > 0) {
        const mapForm = new FormData();
        mapForm.append("source_columns", JSON.stringify(preview.columns));
        mapForm.append("target_columns", JSON.stringify(data.columns));
        const mapRes = await fetch(`${API_BASE}/schema/auto-map-custom`, { method: "POST", body: mapForm, headers: apiHeaders() });
        if (mapRes.ok) {
          const mapData = await mapRes.json();
          setCustomMappings(mapData.mappings || []);
          toast("info", `Auto-mapped ${mapData.matched} of ${preview.columns.length} source columns`);
        }
      }
    } catch {
      toast("error", "Failed to parse target file");
    } finally {
      setTargetPreviewLoading(false);
    }
  }, [preview]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files[0]) {
      const f = e.dataTransfer.files[0];
      if (f.size > MAX_FILE_SIZE) {
        toast("error", `File too large: ${(f.size / 1024 / 1024).toFixed(1)}MB. Max: ${MAX_FILE_SIZE / 1024 / 1024}MB`);
        return;
      }
      setFile(f);
      setPreview(null);
      setResult(null);
      setErrMsg("");
      toast("info", `Source: ${f.name} — auto-previewing...`);
      autoPreviewFile(f);
    }
  }, [autoPreviewFile]);

  const onTargetDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setTargetDragOver(false);
    if (e.dataTransfer.files[0]) {
      const f = e.dataTransfer.files[0];
      if (f.size > MAX_FILE_SIZE) {
        toast("error", `File too large: ${(f.size / 1024 / 1024).toFixed(1)}MB. Max: ${MAX_FILE_SIZE / 1024 / 1024}MB`);
        return;
      }
      setTargetFile(f);
      setTargetPreview(null);
      setCustomMappings([]);
      toast("info", `Target: ${f.name} — auto-parsing...`);
      autoParseTarget(f);
    }
  }, [autoParseTarget]);

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
      toast("info", `Source: ${f.name} — auto-previewing...`);
      autoPreviewFile(f);
    }
  }, [autoPreviewFile]);

  const onTargetFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      const f = e.target.files[0];
      if (f.size > MAX_FILE_SIZE) {
        toast("error", `File too large: ${(f.size / 1024 / 1024).toFixed(1)}MB. Max: ${MAX_FILE_SIZE / 1024 / 1024}MB`);
        return;
      }
      setTargetFile(f);
      setTargetPreview(null);
      setCustomMappings([]);
      toast("info", `Target: ${f.name} — auto-parsing...`);
      autoParseTarget(f);
    }
  }, [autoParseTarget]);

  const handleGenerateScript = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    setErrMsg("");

    const form = new FormData();
    form.append("file", file);
    if (targetFile) {
      form.append("target_file", targetFile);
    }
    if (customMappings.length > 0) {
      form.append("mappings", JSON.stringify(customMappings));
    }
    form.append("output_format", outputFormat);

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
        const mapped = data.mappings_applied > 0 ? ` (${data.mappings_applied} fields mapped)` : "";
        toast("success", `Script ready — ${data.records_count} records${mapped}`);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Connection failed";
      toast("error", msg);
      setErrMsg(msg);
    } finally {
      setLoading(false);
    }
  }, [file, targetFile, customMappings, outputFormat]);

  const handleDownloadScript = useCallback(() => {
    if (!result) return;
    const link = document.createElement("a");
    link.href = `${API_BASE}${result.download_url}`;
    link.download = result.script_filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast("success", "Script downloaded");
  }, [result]);

  const handleReset = useCallback(() => {
    setFile(null);
    setTargetFile(null);
    setPreview(null);
    setTargetPreview(null);
    setCustomMappings([]);
    setResult(null);
    setErrMsg("");
    if (inputRef.current) inputRef.current.value = "";
    if (targetInputRef.current) targetInputRef.current.value = "";
  }, []);

  const changeMappingTarget = useCallback((index: number, newTarget: string) => {
    setCustomMappings((prev) =>
      prev.map((m, i) => (i === index ? { ...m, target: newTarget } : m))
    );
  }, []);

  const removeMapping = useCallback((index: number) => {
    setCustomMappings((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const addMapping = useCallback((source: string, target: string) => {
    if (!source || !target) return;
    setCustomMappings((prev) =>
      prev.some((m) => m.source === source) ? prev : [...prev, { source, target }]
    );
  }, []);

  const sourceColumns = preview?.columns ?? [];
  const targetColumns = targetPreview?.columns ?? [];

  return {
    file, targetFile, dragOver, targetDragOver, preview, previewLoading,
    targetPreview, targetPreviewLoading, customMappings,
    sourceColumns, targetColumns,
    outputFormat, setOutputFormat,
    loading, result, errMsg, inputRef, targetInputRef,
    setDragOver, setTargetDragOver, setTargetFile, setTargetPreview, setCustomMappings, setPreview,
    changeMappingTarget, removeMapping, addMapping,
    onDrop, onTargetDrop, onFileSelect, onTargetFileSelect,
    handleGenerateScript, handleDownloadScript, handleReset,
    scriptFilename: result?.script_filename || null,
  };
}
