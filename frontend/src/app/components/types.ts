export type AuditEntry = { event: string; record_id: string; bank_pair: string; details: string; timestamp: string };
export type ResultData = { success: boolean; total_records: number; processed: number; failed: number; output_path: string | null; error: string | null };
export type PreviewData = { filename: string; format: string; columns: string[]; rows: Record<string, string | number>[]; row_count: number };
export type HistoryEntry = { id: string; timestamp: string; sourceBank: string; targetBanks: string[]; outputFormat: string; totalRecords: number; processed: number; failed: number; success: boolean; outputPaths: string[] };

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";
export const MAX_FILE_SIZE = 50 * 1024 * 1024;
export const HISTORY_KEY = "migration_history";

export const fmt = (name: string) => name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export function apiHeaders(): Record<string, string> {
  const key = process.env.NEXT_PUBLIC_API_KEY || "";
  const headers: Record<string, string> = {};
  if (key) headers["X-API-Key"] = key;
  return headers;
}
