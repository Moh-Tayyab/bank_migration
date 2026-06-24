"use client";
import Icon from "./Icon";
import type { MigrationHook } from "./hooks/useMigration";

type Props = Pick<MigrationHook, "file" | "dragOver" | "previewLoading" | "inputRef" | "onDrop" | "onFileSelect" | "setDragOver">;

export default function UploadCard({ file, dragOver, previewLoading, inputRef, onDrop, onFileSelect, setDragOver }: Props) {
  return (
    <section className="card-elevated animate-slide-up delay-75" aria-label="Upload data file">
      <div className="px-5 py-3.5 border-b border-[var(--border)] flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-lg bg-[var(--primary-light)] flex items-center justify-center">
          <Icon name="upload" className="w-3.5 h-3.5 text-[var(--primary)]" />
        </div>
        <h2 className="text-sm font-semibold text-[var(--foreground)]">Upload Data</h2>
      </div>
      <div className="p-5">
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`dropzone ${dragOver ? "active" : ""} ${file ? "has-file" : ""}`}
          role="button"
          tabIndex={0}
          aria-label={file ? `File selected: ${file.name}` : "Click or drag to upload a file"}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") inputRef.current?.click(); }}
        >
          <input ref={inputRef} type="file" onChange={onFileSelect} className="hidden" accept=".csv,.json,.docx,.xlsx,.xml,.txt" />
          <div className="flex flex-col items-center gap-2.5">
            <div className={`p-3 rounded-xl transition-all ${file ? "text-[var(--success)]" : dragOver ? "text-[var(--primary)]" : "text-[var(--muted-foreground)]"}`}>
              {file ? <Icon name="check" className="w-6 h-6" /> : <Icon name="upload" className="w-6 h-6" />}
            </div>
            {file ? (
              <div className="text-center">
                <p className="text-sm font-semibold text-[var(--foreground)]">{file.name}</p>
                <p className="text-[11px] text-[var(--muted-foreground)] mt-0.5">{(file.size / 1024).toFixed(1)} KB</p>
                {previewLoading && (
                  <p className="text-[10px] text-[var(--primary)] mt-1 flex items-center gap-1 justify-center">
                    <span className="w-2.5 h-2.5 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
                    Auto-previewing...
                  </p>
                )}
              </div>
            ) : (
              <div className="text-center">
                <p className="text-sm text-[var(--muted-foreground)]">
                  <span className="text-[var(--primary)] font-semibold cursor-pointer">Click to upload</span>{" or drag & drop"}
                </p>
                <p className="text-[11px] text-[var(--muted-foreground)] mt-0.5">CSV, JSON, DOCX, XLSX, XML, TXT</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
