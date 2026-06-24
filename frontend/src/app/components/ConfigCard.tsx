"use client";
import { useRef } from "react";
import Icon from "./Icon";
import type { MigrationHook } from "./hooks/useMigration";

type Props = Pick<MigrationHook,
  "outputFormat" |
  "file" | "targetFile" | "loading" | "pollingTask" | "pollingBanks" |
  "targetDragOver" | "targetPreview" | "targetPreviewLoading" |
  "customMappings" |
  "setOutputFormat" | "setTargetDragOver" | "setTargetFile" | "setTargetPreview" | "setCustomMappings" |
  "handleMigrate" | "onTargetDrop" | "onTargetFileSelect"
>;

export default function ConfigCard({
  outputFormat, file, targetFile, loading,
  pollingTask, pollingBanks, targetDragOver, targetPreview, targetPreviewLoading, customMappings,
  setOutputFormat, setTargetDragOver, setTargetFile, setTargetPreview, setCustomMappings,
  handleMigrate: onMigrate, onTargetDrop, onTargetFileSelect,
}: Props) {
  const targetInputRef = useRef<HTMLInputElement>(null);
  const canMigrate = !!file && !!targetFile && !loading && !pollingTask;

  return (
    <section className="card-elevated animate-slide-up delay-100" aria-label="Migration configuration">
      <div className="px-5 py-3.5 border-b border-[var(--border)] flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-lg bg-[var(--primary-light)] flex items-center justify-center">
          <Icon name="settings" className="w-3.5 h-3.5 text-[var(--primary)]" />
        </div>
        <h2 className="text-sm font-semibold text-[var(--foreground)]">Target Schema</h2>
      </div>
      <div className="p-5 space-y-4">
        {/* Target File Upload */}
        <div>
          <p className="text-[11px] text-[var(--muted-foreground)] mb-2">
            Upload a sample target file to auto-detect schema
          </p>
          {!targetFile ? (
            <div
              onDragOver={(e) => { e.preventDefault(); setTargetDragOver(true); }}
              onDragLeave={() => setTargetDragOver(false)}
              onDrop={onTargetDrop}
              className={`dropzone ${targetDragOver ? "active" : ""}`}
            >
              <input
                ref={targetInputRef}
                type="file"
                accept=".csv,.xlsx,.xls,.json,.xml"
                onChange={onTargetFileSelect}
                className="hidden"
              />
              <div className="w-10 h-10 rounded-lg bg-[var(--primary-light)] flex items-center justify-center mb-3 mx-auto">
                <Icon name="upload" className="w-5 h-5 text-[var(--primary)]" />
              </div>
              <p className="text-xs font-medium text-[var(--foreground)] mb-1">Drop target file here</p>
              <p className="text-[10px] text-[var(--muted-foreground)] mb-3">CSV, Excel, JSON, XML</p>
              <button
                onClick={() => targetInputRef.current?.click()}
                className="btn-secondary text-[11px]"
                type="button"
              >
                Select Target File
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center gap-3 p-2.5 rounded-lg bg-[var(--muted)]">
                <Icon name="file" className="w-4 h-4 text-[var(--primary)]" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-[var(--foreground)] truncate">{targetFile.name}</p>
                  <p className="text-[10px] text-[var(--muted-foreground)]">{(targetFile.size / 1024).toFixed(1)} KB</p>
                </div>
                <button
                  onClick={() => { setTargetFile(null); setTargetPreview(null); setCustomMappings([]); }}
                  className="text-[10px] text-[var(--muted-foreground)] hover:text-[var(--error)]"
                  type="button"
                >
                  Remove
                </button>
              </div>
              {targetPreviewLoading && (
                <div className="p-2.5 rounded-lg bg-[var(--muted)] flex items-center gap-2">
                  <span className="w-3 h-3 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
                  <span className="text-[11px] text-[var(--muted-foreground)]">Auto-parsing schema...</span>
                </div>
              )}
              {targetPreview && (
                <div className="p-2.5 rounded-lg bg-[var(--success-light)] border border-[var(--success)]/30">
                  <div className="flex items-center gap-2 mb-1.5">
                    <Icon name="check-circle" className="w-3.5 h-3.5 text-[var(--success)]" />
                    <span className="text-[11px] font-semibold text-[var(--success)]">Schema auto-detected</span>
                  </div>
                  <p className="text-[10px] text-[var(--success)]/80">{targetPreview.columns.length} columns</p>
                  {customMappings.length > 0 && (
                    <p className="text-[10px] text-[var(--success)]/80 mt-0.5">{customMappings.length} fields mapped</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Mapped Fields */}
        {customMappings.length > 0 && (
          <div>
            <label className="block text-[11px] font-semibold text-[var(--muted-foreground)] mb-1.5 uppercase tracking-wider">
              Mapped Fields ({customMappings.length})
            </label>
            <div className="max-h-32 overflow-y-auto space-y-1">
              {customMappings.map((m, i) => (
                <div key={i} className="flex items-center gap-2 text-[10px]">
                  <span className="px-1.5 py-0.5 rounded bg-[var(--primary-light)] text-[var(--primary)] font-medium truncate max-w-[100px]">
                    {m.source}
                  </span>
                  <Icon name="arrow" className="w-2.5 h-2.5 text-[var(--muted-foreground)] shrink-0" />
                  <span className="px-1.5 py-0.5 rounded bg-[var(--success-light)] text-[var(--success)] font-medium truncate max-w-[100px]">
                    {m.target}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Output Format */}
        <div>
          <label className="block text-[11px] font-semibold text-[var(--muted-foreground)] mb-1.5 uppercase tracking-wider">
            Output Format
          </label>
          <div className="grid grid-cols-5 gap-1.5" role="radiogroup" aria-label="Output format">
            {["json", "csv", "docx", "xlsx", "html"].map((f) => (
              <button key={f} onClick={() => setOutputFormat(f)} className={`format-btn ${outputFormat === f ? "active" : ""}`} id={`format-${f}`} type="button" role="radio" aria-checked={outputFormat === f}>
                {f.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {/* Migrate Button */}
        <button
          onClick={onMigrate}
          disabled={!canMigrate}
          className="btn-primary w-full h-11 text-sm flex items-center justify-center gap-2 cursor-pointer"
          id="migrate-btn" type="button"
        >
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
    </section>
  );
}
