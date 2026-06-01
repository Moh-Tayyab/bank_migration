"use client";
import Icon from "./Icon";
import { fmt } from "./types";
import type { MigrationHook } from "./hooks/useMigration";

type Props = Pick<MigrationHook,
  "sourceBank" | "targetBanks" | "detectedTarget" | "outputFormat" | "banks" |
  "file" | "loading" | "pollingTask" | "pollingBanks" |
  "setSourceBank" | "setOutputFormat" | "handleMigrate"
>;

export default function ConfigCard({
  sourceBank, targetBanks, detectedTarget, outputFormat, banks, file, loading,
  pollingTask, pollingBanks,
  setSourceBank, setOutputFormat, handleMigrate: onMigrate,
}: Props) {
  const canMigrate = !!file && targetBanks.length > 0 && !loading && !pollingTask;

  return (
    <section className="card-elevated animate-slide-up delay-100" aria-label="Migration configuration">
      <div className="px-5 py-3.5 border-b border-[var(--border)] flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-lg bg-[var(--primary-light)] flex items-center justify-center">
          <Icon name="settings" className="w-3.5 h-3.5 text-[var(--primary)]" />
        </div>
        <h2 className="text-sm font-semibold text-[var(--foreground)]">Configuration</h2>
      </div>
      <div className="p-5 space-y-4">
        <div>
          <label htmlFor="source-bank-select" className="block text-[11px] font-semibold text-[var(--muted-foreground)] mb-1.5 uppercase tracking-wider">
            Source Bank
          </label>
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
          <label className="block text-[11px] font-semibold text-[var(--muted-foreground)] mb-1.5 uppercase tracking-wider">
            Target Bank
          </label>
          {detectedTarget ? (
            <div className="p-3 rounded-lg bg-[var(--success-light)] border border-[var(--success)]/30">
              <div className="flex items-center gap-2">
                <Icon name="check-circle" className="w-4 h-4 text-[var(--success)] shrink-0" />
                <div className="flex-1">
                  <p className="text-xs text-[var(--muted-foreground)]">Auto-detected from file columns</p>
                  <p className="text-sm font-semibold text-[var(--foreground)]">{fmt(detectedTarget)}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-3 rounded-lg bg-[var(--muted)] border border-[var(--border)]">
              <div className="flex items-center gap-2">
                <Icon name="info-circle" className="w-4 h-4 text-[var(--muted-foreground)] shrink-0" />
                <p className="text-xs text-[var(--muted-foreground)]">Upload and preview a file to auto-detect target bank</p>
              </div>
            </div>
          )}
        </div>

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

        <button
          onClick={onMigrate}
          disabled={!canMigrate}
          className="btn-primary w-full h-11 text-sm flex items-center justify-center gap-2 cursor-pointer"
          id="migrate-btn" type="button"
          aria-label={canMigrate ? "Start data migration" : "Upload a file and preview to detect target bank"}
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
