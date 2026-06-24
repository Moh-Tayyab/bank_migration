"use client";
import { useState } from "react";
import Icon from "./components/Icon";
import { ToastProvider } from "./components/Toast";
import FilePreview from "./components/FilePreview";
import { useSqlLoader } from "./components/hooks/useSqlLoader";

function MigrationPageInner() {
  const s = useSqlLoader();
  const [addSelections, setAddSelections] = useState<Record<string, string>>({});

  const usedTargets = s.customMappings.map((m) => m.target);
  const unmatchedSource = s.sourceColumns.filter(
    (c) => !s.customMappings.some((m) => m.source === c)
  );
  const availableTargets = s.targetColumns.filter((t) => !usedTargets.includes(t));
  const showMappingCard = !!s.targetPreview && s.sourceColumns.length > 0;

  return (
    <div className="min-h-screen flex flex-col">
      <main className="flex-1 max-w-[1280px] mx-auto w-full px-4 lg:px-6 py-5">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <div className="lg:col-span-5 space-y-4">
            <div className="card p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className={`step-number ${s.file ? "done" : "active"}`}>
                    {s.file ? <Icon name="check" className="w-2.5 h-2.5" /> : "1"}
                  </span>
                  <h3 className="text-sm font-semibold text-[var(--foreground)]">Source File</h3>
                </div>
                {s.file && (
                  <button onClick={s.handleReset} className="text-[10px] text-[var(--muted-foreground)] hover:text-[var(--error)] cursor-pointer" type="button">Clear</button>
                )}
              </div>

              {!s.file ? (
                <div
                  onDragOver={(e) => { e.preventDefault(); s.setDragOver(true); }}
                  onDragLeave={() => s.setDragOver(false)}
                  onDrop={s.onDrop}
                  className={`dropzone ${s.dragOver ? "active" : ""}`}
                >
                  <input ref={s.inputRef} type="file" accept=".csv,.xlsx,.xls,.json,.xml" onChange={s.onFileSelect} className="hidden" />
                  <div className="w-9 h-9 rounded-lg bg-[var(--primary-light)] flex items-center justify-center mb-3 mx-auto">
                    <Icon name="upload" className="w-4 h-4 text-[var(--primary)]" />
                  </div>
                  <p className="text-xs font-medium text-[var(--foreground)] mb-0.5">Upload source data</p>
                  <p className="text-[11px] text-[var(--muted-foreground)] mb-3">CSV, Excel, JSON, XML</p>
                  <button onClick={() => s.inputRef.current?.click()} className="btn-secondary" type="button">Select File</button>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex items-center gap-2.5 p-2.5 rounded-lg bg-[var(--muted)]">
                    <Icon name="file" className="w-4 h-4 text-[var(--primary)] shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-[var(--foreground)] truncate">{s.file.name}</p>
                      <p className="text-[10px] text-[var(--muted-foreground)]">{(s.file.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <Icon name="check" className="w-3.5 h-3.5 text-[var(--success)] shrink-0" />
                  </div>
                  {s.previewLoading && (
                    <div className="flex items-center gap-2 text-[11px] text-[var(--muted-foreground)]">
                      <span className="w-3 h-3 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
                      Reading columns...
                    </div>
                  )}
                  {s.preview && (
                    <div className="flex items-center gap-1.5 text-[11px] text-[var(--success)]">
                      <Icon name="check-circle" className="w-3 h-3" />
                      {s.preview.columns.length} columns &middot; {s.preview.row_count} rows
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="card p-4">
              <div className="flex items-center gap-2 mb-3">
                <span className={`step-number ${s.targetFile ? "done" : ""}`}>
                  {s.targetFile ? <Icon name="check" className="w-2.5 h-2.5" /> : "2"}
                </span>
                <h3 className="text-sm font-semibold text-[var(--foreground)]">Target Schema</h3>
              </div>

              {!s.targetFile ? (
                <div
                  onDragOver={(e) => { e.preventDefault(); s.setTargetDragOver(true); }}
                  onDragLeave={() => s.setTargetDragOver(false)}
                  onDrop={s.onTargetDrop}
                  className={`dropzone ${s.targetDragOver ? "active" : ""}`}
                >
                  <input ref={s.targetInputRef} type="file" accept=".csv,.xlsx,.xls,.json,.xml" onChange={s.onTargetFileSelect} className="hidden" />
                  <div className="w-9 h-9 rounded-lg bg-[var(--primary-light)] flex items-center justify-center mb-3 mx-auto">
                    <Icon name="upload" className="w-4 h-4 text-[var(--primary)]" />
                  </div>
                  <p className="text-xs font-medium text-[var(--foreground)] mb-0.5">Upload target format</p>
                  <p className="text-[11px] text-[var(--muted-foreground)] mb-3">Sample file of desired output</p>
                  <button onClick={() => s.targetInputRef.current?.click()} className="btn-secondary" type="button">Select File</button>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex items-center gap-2.5 p-2.5 rounded-lg bg-[var(--muted)]">
                    <Icon name="file" className="w-4 h-4 text-[var(--primary)] shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-[var(--foreground)] truncate">{s.targetFile.name}</p>
                      <p className="text-[10px] text-[var(--muted-foreground)]">{(s.targetFile.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button onClick={() => { s.setTargetFile(null); s.setTargetPreview(null); s.setCustomMappings([]); }} className="text-[10px] text-[var(--muted-foreground)] hover:text-[var(--error)] cursor-pointer" type="button">
                      Remove
                    </button>
                  </div>
                  {s.targetPreviewLoading && (
                    <div className="flex items-center gap-2 text-[11px] text-[var(--muted-foreground)]">
                      <span className="w-3 h-3 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
                      Parsing & mapping...
                    </div>
                  )}
                  {s.targetPreview && (
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-1.5 text-[11px] text-[var(--success)]">
                        <Icon name="check-circle" className="w-3 h-3" />
                        {s.targetPreview.columns.length} target columns
                      </div>
                      {s.customMappings.length > 0 && (
                        <div className="flex items-center gap-1.5 text-[11px] text-[var(--info)]">
                          <Icon name="layers" className="w-3 h-3" />
                          {s.customMappings.length} fields auto-mapped
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

              {showMappingCard && (
              <div className="card p-4">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-[var(--primary-light)] flex items-center justify-center">
                      <Icon name="layers" className="w-4 h-4 text-[var(--primary)]" />
                    </div>
                    <h3 className="text-sm font-semibold text-[var(--foreground)]">CUSTOM Field Mapping Review</h3>
                  </div>
                  <span className="text-[10px] font-bold text-[var(--muted-foreground)] uppercase tracking-wider bg-[var(--muted)] px-2 py-1 rounded">
                    {s.customMappings.length} / {s.sourceColumns.length} Mapped
                  </span>
                </div>

                <div className="space-y-3">
                  {s.customMappings.map((m, i) => {
                    const opts = s.targetColumns.filter((t) => t === m.target || !usedTargets.includes(t));
                    return (
                      <div key={`${m.source}__${i}`} className="flex items-center gap-2 p-2 rounded-lg bg-[var(--muted)]/50 border border-[var(--border)]">
                        <span className="text-[11px] font-mono font-medium text-[var(--foreground)] truncate flex-1" title={m.source}>{m.source}</span>
                        <Icon name="arrow-right" className="w-3 h-3 text-[var(--muted-foreground)] shrink-0" />
                        <select
                          value={m.target}
                          onChange={(e) => s.changeMappingTarget(i, e.target.value)}
                          className="flex-[2] min-w-0 px-2 py-1 rounded bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] text-[11px] focus:border-[var(--primary)] outline-none cursor-pointer"
                        >
                          {opts.map((t) => (
                            <option key={t} value={t}>{t}</option>
                          ))}
                        </select>
                        <button
                          type="button"
                          onClick={() => s.removeMapping(i)}
                          className="p-1.5 rounded hover:bg-[var(--error-light)] text-[var(--muted-foreground)] hover:text-[var(--error)] transition-colors"
                          title="Remove mapping"
                        >
                          <Icon name="xmark" className="w-3 h-3" />
                        </button>
                      </div>
                    );
                  })}
                </div>

                {unmatchedSource.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-[var(--border)]">
                    <p className="text-[10px] font-bold text-[var(--muted-foreground)] uppercase tracking-wider mb-2">
                      Add New Mapping
                    </p>
                    <div className="space-y-2">
                      {unmatchedSource.map((src) => {
                        const opts = availableTargets;
                        const sel = opts.includes(addSelections[src]) ? addSelections[src] : opts[0];
                        const disabled = opts.length === 0;
                        return (
                          <div key={src} className="flex items-center gap-2">
                            <span className="text-[11px] font-medium text-[var(--muted-foreground)] truncate flex-1" title={src}>{src}</span>
                            <select
                              value={sel ?? ""}
                              disabled={disabled}
                              onChange={(e) => setAddSelections((p) => ({ ...p, [src]: e.target.value }))}
                              className="w-full px-2 py-1 rounded bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] text-[11px] outline-none"
                            >
                              {disabled ? <option value="">No targets</option> : opts.map((t) => <option key={t} value={t}>{t}</option>)}
                            </select>
                            <button
                              type="button"
                              disabled={disabled || !sel}
                              onClick={() => sel && s.addMapping(src, sel)}
                              className="px-2 py-1 rounded bg-[var(--primary)] text-[var(--primary-foreground)] text-[11px] font-bold"
                            >
                              +
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="card p-4">
              <label className="block text-[11px] font-semibold text-[var(--muted-foreground)] mb-2 uppercase tracking-wider">
                Output Format
              </label>
              <div className="grid grid-cols-4 gap-1.5" role="radiogroup" aria-label="Output format">
                {(["csv", "json", "html", "xlsx"] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => s.setOutputFormat(f)}
                    className={`format-btn ${s.outputFormat === f ? "active" : ""}`}
                    type="button"
                    role="radio"
                    aria-checked={s.outputFormat === f}
                  >
                    {f.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={s.handleGenerateScript}
              disabled={!s.file || !s.targetFile || s.loading}
              className="btn-primary w-full h-10"
              type="button"
            >
              {s.loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Generating...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Icon name="terminal" className="w-3.5 h-3.5" />
                  Generate Script
                </span>
              )}
            </button>
          </div>

          <div className="lg:col-span-7 space-y-4">
            {s.errMsg && (
              <div className="border border-[var(--error)]/30 rounded-lg animate-scale-in" style={{ background: "var(--error-light)" }} role="alert">
                <div className="p-4 flex items-start gap-3">
                  <div className="shrink-0">
                    <Icon name="xmark" className="w-5 h-5 text-[var(--error)]" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-[var(--error)]">Error</p>
                    <p className="text-xs text-[var(--error)]/80 mt-0.5">{s.errMsg}</p>
                  </div>
                </div>
              </div>
            )}

            {s.preview && (
              <FilePreview
                filename={s.file?.name || ""} format={s.file?.name.split(".").pop() || "csv"}
                columns={s.preview.columns} rows={s.preview.rows}
                rowCount={s.preview.row_count} onClose={() => s.setPreview(null)}
              />
            )}

            {(function() {
              const r = s.result;
              if (!r) return null;
              const copyCmd = (cmd: string) => (e: React.MouseEvent<HTMLDivElement>) => {
                const sel = window.getSelection();
                if (sel) { sel.selectAllChildren(e.currentTarget); navigator.clipboard?.writeText(cmd); }
              };
              return (
                <div className="card p-5 animate-slide-up">
                  <div className="flex items-center gap-2.5 mb-4 pb-4 border-b border-[var(--border)]">
                    <div className="w-7 h-7 rounded-lg bg-[var(--success-light)] flex items-center justify-center">
                      <Icon name="check-circle" className="w-4 h-4 text-[var(--success)]" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-[var(--foreground)]">Script Generated</h3>
                      {r.mappings_applied > 0 && (
                        <p className="text-[11px] text-[var(--muted-foreground)]">{r.mappings_applied} fields mapped &middot; {r.records_count} records</p>
                      )}
                    </div>
                  </div>

                  <div className="mb-3">
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <Icon name="command" className="w-3.5 h-3.5 text-[var(--muted-foreground)]" />
                      <span className="text-[11px] font-medium text-[var(--muted-foreground)]">Windows (PowerShell)</span>
                    </div>
                    <div className="relative">
                      <div className="terminal-box select-all cursor-pointer hover:opacity-90" onClick={(e) => { const sel = window.getSelection(); if (sel) { sel.selectAllChildren(e.currentTarget); navigator.clipboard?.writeText(r.cmd_windows); } }}>
                        {r.cmd_windows}
                      </div>
                      <button
                        onClick={() => navigator.clipboard?.writeText(r.cmd_windows)}
                        className="absolute right-2 top-2 p-1.5 rounded bg-[var(--muted)] hover:bg-[var(--muted-foreground)]/20 cursor-pointer transition-colors"
                        title="Copy command"
                      >
                        <svg className="w-3.5 h-3.5 text-[var(--muted-foreground)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 5H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v4"/>
                        </svg>
                      </button>
                    </div>
                  </div>

                  <div className="mb-4">
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <Icon name="terminal" className="w-3.5 h-3.5 text-[var(--muted-foreground)]" />
                      <span className="text-[11px] font-medium text-[var(--muted-foreground)]">Mac / Linux (Terminal)</span>
                    </div>
                    <div className="relative">
                      <div className="terminal-box select-all cursor-pointer hover:opacity-90" onClick={(e) => { const sel = window.getSelection(); if (sel) { sel.selectAllChildren(e.currentTarget); navigator.clipboard?.writeText(r.cmd_linux); } }}>
                        {r.cmd_linux}
                      </div>
                      <button
                        onClick={() => navigator.clipboard?.writeText(r.cmd_linux)}
                        className="absolute right-2 top-2 p-1.5 rounded bg-[var(--muted)] hover:bg-[var(--muted-foreground)]/20 cursor-pointer transition-colors"
                        title="Copy command"
                      >
                        <svg className="w-3.5 h-3.5 text-[var(--muted-foreground)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 5H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v4"/>
                        </svg>
                      </button>
                    </div>
                  </div>

                  <p className="text-[11px] text-[var(--muted-foreground)]">Click the command or copy button to copy, then paste in terminal.</p>
                </div>
              );
            })()}

            {!s.result && !s.errMsg && (
              <div className="card p-8 flex flex-col items-center justify-center text-center min-h-[280px] animate-fade-in">
                <div className="w-12 h-12 rounded-xl bg-[var(--primary-light)] flex items-center justify-center mb-4">
                  <Icon name="terminal" className="w-6 h-6 text-[var(--primary)]" />
                </div>
                <h2 className="text-sm font-semibold text-[var(--foreground)] mb-1">Ready to Migrate</h2>
                <p className="text-xs text-[var(--muted-foreground)] max-w-sm leading-relaxed">
                  Upload a source data file and a target schema sample. The system will auto-map fields and generate terminal commands to run the migration.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>

      <footer className="border-t border-[var(--border)] bg-[var(--card)]/80">
        <div className="max-w-[1280px] mx-auto px-4 lg:px-6 py-3 flex items-center justify-between text-[11px] text-[var(--muted-foreground)]">
          <span>&copy; {new Date().getFullYear()} UN Wallet</span>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--success)]" />
            Operational
          </span>
        </div>
      </footer>
    </div>
  );
}

export default function MigrationPage() {
  return (
    <ToastProvider>
      <MigrationPageInner />
    </ToastProvider>
  );
}
