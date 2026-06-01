import { useState } from "react";
import Icon from "./Icon";
import { toast } from "./Toast";

type DownloadCommandProps =
  | { filename: string; apiBase: string; type?: "curl" }
  | { scriptName: string; type: "bash" }
  | { filename: string; apiBase: string; type: "sh-curl" };

export default function DownloadCommand(props: DownloadCommandProps) {
  const [copied, setCopied] = useState(false);

  let cmd: string;
  let label: string;

  if (props.type === "bash") {
    cmd = `bash ${props.scriptName}`;
    label = "Copy bash cmd";
  } else if (props.type === "sh-curl") {
    cmd = `curl -o ${props.filename} ${props.apiBase}/download/${props.filename}`;
    label = "Copy .sh cmd";
  } else {
    // default: curl download
    cmd = `curl -O ${props.apiBase}/download/${props.filename}`;
    label = "Copy cmd";
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
