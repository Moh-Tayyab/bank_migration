"use client";
import { useState } from "react";
import Icon from "./components/Icon";
import { toast, ToastProvider } from "./components/Toast";
import ConfirmationDialog from "./components/ConfirmationDialog";
import FilePreview from "./components/FilePreview";
import SchemaPreview from "./components/SchemaPreview";
import MigrationHistory from "./components/MigrationHistory";
import PipelineSteps from "./components/PipelineSteps";
import UploadCard from "./components/UploadCard";
import ConfigCard from "./components/ConfigCard";
import ResultPanel from "./components/ResultPanel";
import MultiBankResults from "./components/MultiBankResults";
import AuditPanel from "./components/AuditPanel";
import PollingCard from "./components/PollingCard";
import DownloadCommand from "./components/DownloadCommand";
import { BanksBarSkeleton, CardSkeleton } from "./components/Skeleton";
import { fmt } from "./components/types";
import { useMigration } from "./components/hooks/useMigration";
import { useSqlLoader } from "./components/hooks/useSqlLoader";

type AppMode = "migration" | "sqlldr";

function MigrationPageInner() {
  const [mode, setMode] = useState<AppMode>("migration");
  const m = useMigration();
  const s = useSqlLoader();

  const bankNames = m.targetBanks.map(fmt).join(", ");

  return (
    <>
      <ConfirmationDialog
        open={m.showConfirm}
        title="Start Migration?"
        message={`Migrating from ${fmt(m.sourceBank)} to ${fmt(m.detectedTarget || "auto-detected")}. Output format: ${m.outputFormat.toUpperCase()}. This action cannot be undone.`}
        confirmLabel="Start Migration"
        cancelLabel="Cancel"
        variant="warning"
        onConfirm={() => { m.setShowConfirm(false); m.executeMigration(); }}
        onCancel={() => m.setShowConfirm(false)}
      />

      <div className="min-h-screen relative overflow-hidden flex flex-col">
        <div className="orb orb-1" aria-hidden="true" />
        <div className="orb orb-2" aria-hidden="true" />

        {/* Header */}
        <header className="sticky top-0 z-30 bg-[var(--card)]/90 backdrop-blur-md border-b border-[var(--border)]" role="banner">
          <div className="max-w-[1440px] mx-auto h-14 flex items-center justify-between px-4 lg:px-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center text-white font-bold text-xs tracking-tight">
                UW
              </div>
              <div className="hidden sm:block">
                <h1 className="text-sm font-semibold text-[var(--foreground)] leading-tight">Data Migration</h1>
                <p className="text-[10px] text-[var(--muted-foreground)]">Secure multi-bank ETL pipeline</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {/* Mode Switcher */}
              <div className="flex items-center bg-[var(--muted)] rounded-lg p-0.5">
                <button
                  onClick={() => setMode("migration")}
                  className={`px-3 py-1 rounded-md text-[11px] font-medium transition-all ${mode === "migration" ? "bg-[var(--card)] text-[var(--foreground)] shadow-sm" : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"}`}
                >
                  Migration
                </button>
                <button
                  onClick={() => setMode("sqlldr")}
                  className={`px-3 py-1 rounded-md text-[11px] font-medium transition-all ${mode === "sqlldr" ? "bg-[var(--card)] text-[var(--foreground)] shadow-sm" : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"}`}
                >
                  SQL*Loader
                </button>
              </div>
              {mode === "migration" && <PipelineSteps current={m.pipelineStage} />}
              <div className="w-px h-5 bg-[var(--border)] hidden sm:block" />
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--muted)] border border-[var(--border)] transition-all"
              >
                <Icon name="external" className="w-3 h-3" />API Docs
              </a>
              <button
                onClick={m.toggleTheme}
                className="p-2 rounded-lg transition-all hover:bg-[var(--muted)] text-[var(--muted-foreground)] cursor-pointer"
                aria-label={m.dark ? "Switch to light mode" : "Switch to dark mode"}
              >
                <div className={`transition-transform duration-200 ${m.dark ? "rotate-180" : "rotate-0"}`}>
                  {m.dark ? <Icon name="sun" className="w-4 h-4" /> : <Icon name="moon" className="w-4 h-4" />}
                </div>
              </button>
            </div>
          </div>
        </header>

        {/* Connected Banks Bar - Only for migration mode */}
        {mode === "migration" && (m.banksLoading ? (
          <BanksBarSkeleton />
        ) : m.banks.length > 0 ? (
          <div className="border-b border-[var(--border)] bg-[var(--card)]/50 animate-fade-in">
            <div className="max-w-[1440px] mx-auto px-4 lg:px-6 py-2 flex items-center gap-3 text-[11px] text-[var(--muted-foreground)] overflow-x-auto">
              <span className="inline-flex items-center gap-1.5 shrink-0 font-semibold">
                <Icon name="database" className="w-3.5 h-3.5 text-[var(--primary)]" />
                Connected
              </span>
              {m.banks.map((b) => (
                <span key={b} className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-[var(--muted)] border border-[var(--border)] whitespace-nowrap text-[var(--foreground)] font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-[var(--success)] animate-pulse-dot" />
                  {fmt(b)}
                </span>
              ))}
            </div>
          </div>
        ) : null)}

        {/* Main Content */}
        <main id="main-content" className="flex-1 max-w-[1440px] mx-auto w-full px-4 lg:px-6 py-6" tabIndex={-1}>
          {mode === "migration" ? (
            <>
              <MigrationHistory history={m.history} onClear={m.handleClearHistory} onRetry={m.handleRetry} />

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mt-6">
                {/* Left Column: Upload + Config */}
                <div className="lg:col-span-4 space-y-5">
                  <UploadCard
                    file={m.file} dragOver={m.dragOver} previewLoading={m.previewLoading}
                    inputRef={m.inputRef} onDrop={m.onDrop} onFileSelect={m.onFileSelect}
                    setDragOver={m.setDragOver} handlePreview={m.handlePreview}
                  />
                  <ConfigCard
                    sourceBank={m.sourceBank} targetBanks={m.targetBanks} detectedTarget={m.detectedTarget} outputFormat={m.outputFormat}
                    banks={m.banks} file={m.file} loading={m.loading}
                    pollingTask={m.pollingTask} pollingBanks={m.pollingBanks}
                    setSourceBank={m.setSourceBank}
                    setOutputFormat={m.setOutputFormat}
                    handleMigrate={m.handleMigrate}
                  />
                </div>

                {/* Right Column: Results */}
                <div className="lg:col-span-8 space-y-5">
                  {/* Error */}
                  {m.errMsg && (
                    <div className="card border-[var(--error)]/30 animate-scale-in" style={{ background: "var(--error-light)" }} role="alert">
                      <div className="p-4 flex items-start gap-3">
                        <div className="p-1.5 rounded-lg bg-[var(--error)]/10 shrink-0">
                          <Icon name="xmark" className="w-4 h-4 text-[var(--error)]" />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-semibold text-[var(--error)]">Migration Error</p>
                          <p className="text-xs text-[var(--error)]/80 mt-0.5 leading-relaxed">{m.errMsg}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Polling */}
                  <PollingCard pollingTask={m.pollingTask} uploadProgress={m.uploadProgress} pollingBanks={m.pollingBanks} />

                  {/* Preview */}
                  {m.preview && (
                    <FilePreview
                      filename={m.preview.filename} format={m.preview.format}
                      columns={m.preview.columns} rows={m.preview.rows}
                      rowCount={m.preview.row_count} onClose={() => m.setPreview(null)}
                    />
                  )}

                  {/* Schema Preview */}
                  {m.sourceColumns.length > 0 && m.targetBanks.length > 0 && (
                    <SchemaPreview
                      sourceBank={m.sourceBank} targetBanks={m.targetBanks}
                      sourceColumns={m.sourceColumns} banks={m.banks} apiBase={m.apiBase}
                    />
                  )}

                  {/* Multi-Bank Results */}
                  <MultiBankResults multiResults={m.multiResults} apiBase={m.apiBase} />

                  {/* Single Result */}
                  {m.result && m.multiResults.length === 0 && (
                    <ResultPanel result={m.result} pct={m.pct} apiBase={m.apiBase} />
                  )}

                  {/* Audit Trail */}
                  <AuditPanel
                    auditTrail={m.auditTrail} showAudit={m.showAudit}
                    setShowAudit={m.setShowAudit} handleExportAudit={m.handleExportAudit}
                  />

                  {/* Empty State */}
                  {!m.result && !m.errMsg && !m.pollingTask && (
                    <div className="card-elevated p-10 flex flex-col items-center justify-center text-center min-h-[380px] animate-fade-in">
                      <div className="w-14 h-14 rounded-2xl bg-[var(--primary-light)] flex items-center justify-center mb-5 animate-success-check">
                        <Icon name="layers" className="w-7 h-7 text-[var(--primary)]" />
                      </div>
                      <h2 className="text-base font-semibold text-[var(--foreground)]">Ready to Migrate</h2>
                      <p className="text-sm text-[var(--muted-foreground)] max-w-sm mt-2 leading-relaxed">
                        Upload a data file and preview it to auto-detect the target bank, then click{" "}
                        <span className="font-semibold text-[var(--foreground)]">Migrate Data</span> to start the pipeline.
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

                      {/* Step Guide */}
                      <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4 text-left w-full max-w-lg">
                        {[
                          { step: "1", title: "Upload", desc: "Drop a CSV, JSON, or spreadsheet file" },
                          { step: "2", title: "Preview", desc: "Auto-detects target bank schema" },
                          { step: "3", title: "Migrate", desc: "One click starts the pipeline" },
                        ].map((s) => (
                          <div key={s.step} className="flex items-start gap-3">
                            <span className="w-6 h-6 rounded-full bg-[var(--primary)] text-[var(--primary-foreground)] text-[11px] font-bold flex items-center justify-center shrink-0">
                              {s.step}
                            </span>
                            <div>
                              <p className="text-xs font-semibold text-[var(--foreground)]">{s.title}</p>
                              <p className="text-[11px] text-[var(--muted-foreground)] mt-0.5">{s.desc}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Mobile Bottom Action Bar - Migration */}
              <div className="mobile-action-bar">
                <button
                  onClick={m.handleMigrate}
                  disabled={!m.file || m.targetBanks.length === 0 || m.loading}
                  className="btn-primary w-full h-11 text-sm flex items-center justify-center gap-2 cursor-pointer"
                  type="button"
                >
                  {m.loading ? (
                    <span className="flex items-center gap-2">
                      <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      {m.pollingTask ? `Polling...` : "Migrating..."}
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <Icon name="arrow" className="w-4 h-4" />
                      Migrate Data
                    </span>
                  )}
                </button>
              </div>
            </>
          ) : (
            <>
              {/* SQL*Loader Mode */}
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-[var(--foreground)] mb-2">SQL*Loader Script Generator</h2>
                <p className="text-sm text-[var(--muted-foreground)]">Upload your bank data file to generate an Oracle SQL*Loader script. The target bank can run this script to load data into their database.</p>
              </div>

              {/* SQL*Loader Upload Card */}
              <div className="card p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-[var(--foreground)]">1. Upload File</h3>
                  {s.file && (
                    <button
                      onClick={s.handleReset}
                      className="text-[11px] text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
                    >
                      Clear
                    </button>
                  )}
                </div>

                {!s.file ? (
                  <div
                    onDragOver={(e) => { e.preventDefault(); s.setDragOver(true); }}
                    onDragLeave={() => s.setDragOver(false)}
                    onDrop={s.onDrop}
                    className={`dropzone ${s.dragOver ? "active" : ""}`}
                  >
                    <input
                      ref={s.inputRef}
                      type="file"
                      accept=".csv,.xlsx,.xls,.json"
                      onChange={s.onFileSelect}
                      className="hidden"
                    />
                    <div className="w-12 h-12 rounded-xl bg-[var(--primary-light)] flex items-center justify-center mb-4 mx-auto">
                      <Icon name="upload" className="w-6 h-6 text-[var(--primary)]" />
                    </div>
                    <p className="text-sm font-medium text-[var(--foreground)] mb-1">Drop your CSV or Excel file here</p>
                    <p className="text-[11px] text-[var(--muted-foreground)] mb-4">or click to browse</p>
                    <button
                      onClick={() => s.inputRef.current?.click()}
                      className="btn-secondary text-xs"
                    >
                      Select File
                    </button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-center gap-3 p-3 rounded-lg bg-[var(--muted)]">
                      <Icon name="file" className="w-5 h-5 text-[var(--primary)]" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-[var(--foreground)] truncate">{s.file.name}</p>
                        <p className="text-[11px] text-[var(--muted-foreground)]">{(s.file.size / 1024).toFixed(1)} KB</p>
                      </div>
                      <Icon name="check" className="w-5 h-5 text-[var(--success)]" />
                    </div>
                  </div>
                )}
              </div>

              {/* SQL*Loader Preview & Generate */}
              {s.file && (
                <div className="card p-6 mt-5">
                  <h3 className="text-sm font-semibold text-[var(--foreground)] mb-4">2. Preview & Generate</h3>

                  {s.preview ? (
                    <div className="space-y-4">
                      {/* Columns detected */}
                      <div>
                        <p className="text-[11px] text-[var(--muted-foreground)] mb-2">Columns detected ({s.preview.columns.length}):</p>
                        <div className="flex flex-wrap gap-1.5">
                          {s.preview.columns.map((col) => (
                            <span key={col} className="px-2 py-0.5 rounded-md bg-[var(--primary-light)] text-[var(--primary)] text-[11px] font-medium">
                              {col}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Table name */}
                      {s.result && (
                        <div className="p-3 rounded-lg bg-[var(--muted)]">
                          <p className="text-[11px] text-[var(--muted-foreground)]">Target table name:</p>
                          <p className="text-sm font-semibold text-[var(--foreground)]">{s.result.table_name}</p>
                        </div>
                      )}

                      {/* Action buttons */}
                      <div className="flex items-center gap-3">
                        <button
                          onClick={s.handleGenerateScript}
                          disabled={s.loading}
                          className="btn-primary text-sm"
                        >
                          {s.loading ? (
                            <span className="flex items-center gap-2">
                              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                              Generating...
                            </span>
                          ) : (
                            <span className="flex items-center gap-2">
                              <Icon name="terminal" className="w-4 h-4" />
                              Generate Script
                            </span>
                          )}
                        </button>

                        {s.result && (
                          <>
                            <button
                              onClick={s.handleDownloadScript}
                              className="btn-secondary text-sm"
                            >
                              <Icon name="download" className="w-4 h-4" />
                              Download .sh
                            </button>
                            <DownloadCommand scriptName={s.result.script_filename} type="bash" />
                          </>
                        )}
                      </div>

                      {/* Result */}
                      {s.result && (
                        <div className="p-4 rounded-lg bg-[var(--success-light)] border border-[var(--success)]/30">
                          <div className="flex items-start gap-3">
                            <Icon name="check-circle" className="w-5 h-5 text-[var(--success)] shrink-0" />
                            <div>
                              <p className="text-sm font-semibold text-[var(--success)]">Script generated successfully!</p>
                              <p className="text-[11px] text-[var(--success)] mt-0.5">
                                {s.result.records_count} records • {s.result.columns.length} columns • Table: {s.result.table_name}
                              </p>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <button
                      onClick={s.handlePreview}
                      disabled={s.previewLoading}
                      className="btn-secondary text-sm w-full"
                    >
                      {s.previewLoading ? (
                        <span className="flex items-center gap-2">
                          <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                          Previewing...
                        </span>
                      ) : (
                        <span className="flex items-center gap-2">
                          <Icon name="eye" className="w-4 h-4" />
                          Preview Columns
                        </span>
                      )}
                    </button>
                  )}
                </div>
              )}

              {/* SQL*Loader Instructions */}
              <div className="card p-6 mt-5">
                <h3 className="text-sm font-semibold text-[var(--foreground)] mb-3">Instructions for Target Bank</h3>
                <ol className="space-y-2 text-xs text-[var(--muted-foreground)]">
                  <li className="flex gap-2">
                    <span className="font-semibold text-[var(--primary)]">1.</span>
                    Download the generated .sh script
                  </li>
                  <li className="flex gap-2">
                    <span className="font-semibold text-[var(--primary)]">2.</span>
                    Update database connection details in the script (DB_USER, DB_PASS, DB_CONNECT)
                  </li>
                  <li className="flex gap-2">
                    <span className="font-semibold text-[var(--primary)]">3.</span>
                    Run the script: <code className="px-1.5 py-0.5 rounded bg-[var(--muted)] text-[var(--foreground)]">bash script_name.sh</code>
                  </li>
                  <li className="flex gap-2">
                    <span className="font-semibold text-[var(--primary)]">4.</span>
                    Check migration.log and migration.bad for any issues
                  </li>
                </ol>
              </div>
            </>
          )}
        </main>

        {/* Footer */}
        <footer className="border-t border-[var(--border)] bg-[var(--card)]/50 mt-auto" role="contentinfo">
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
