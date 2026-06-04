import { useState } from "react";
import Icon from "./Icon";
import { toast } from "./Toast";

type DownloadCommandProps =
  | { filename: string; apiBase: string; type: "sh-curl" }
  | { scriptName: string; type: "bash" };

export default function DownloadCommand(props: DownloadCommandProps) {
  const [copied, setCopied] = useState(false);

  let cmd: string;
  let label: string;

  if (props.type === "bash") {
    cmd = `bash ${props.scriptName}`;
    label = "Copy bash cmd";
  } else {
    cmd = `curl -s http://localhost:8000/api/download/${props.filename} -o ${props.filename} && powershell -NoProfile -Command "Import-Csv ${props.filename} | Format-Table -AutoSize"`;
    label = "Copy .sh cmd";
  }

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
      {copied ? "Copied" : label}
    </button>
  );
}
