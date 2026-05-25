export default function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    INPUT_RECEIVED: "received", VALIDATION: "validation", MAPPING: "mapping",
    TRANSFORM: "transform", SECURITY_MASK: "masked", COMMITTED: "committed",
    ROLLED_BACK: "rolled-back", ERROR: "error", OUTPUT_GENERATED: "output",
  };
  const cls = map[status] || "info";
  return <span className={`badge badge-${cls}`}>{status.replace(/_/g, " ")}</span>;
}
