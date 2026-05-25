import { useState } from "react";
import Icon from "./Icon";
import { toast } from "./Toast";

export default function DownloadCommand({ filename, apiBase }: { filename: string; apiBase: string }) {
  const [copied, setCopied] = useState(false);
  const cmd = `curl -O ${apiBase}/download/${filename}`;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(cmd);
      setCopied(true);
      toast("success", "Command copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch { toast("error", "Failed to copy"); }
  };
  return (
    <button onClick={copy} className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-[var(--muted)] border border-[var(--border)] text-[10px] font-mono text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:border-[var(--primary)] transition-all cursor-pointer" title={cmd}>
      <Icon name={copied ? "check" : "download"} className="w-3 h-3" />
      {copied ? "Copied" : "Copy cmd"}
    </button>
  );
}
