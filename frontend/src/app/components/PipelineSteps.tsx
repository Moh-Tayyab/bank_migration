import Icon from "./Icon";

export default function PipelineSteps({ current }: { current?: string }) {
  const steps = [
    { key: "upload", label: "Upload", icon: "upload" },
    { key: "config", label: "Configure", icon: "settings" },
    { key: "migrate", label: "Migrate", icon: "arrow" },
    { key: "result", label: "Results", icon: "check" },
  ];
  const activeIdx = steps.findIndex((s) => s.key === current);
  return (
    <div className="flex items-center gap-1">
      {steps.map((step, i) => (
        <div key={step.key} className="flex items-center">
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all ${
            i <= activeIdx ? "bg-[var(--primary-light)] text-[var(--primary)]" : "text-[var(--muted-foreground)]"
          }`}>
            <Icon name={step.icon} className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{step.label}</span>
          </div>
          {i < steps.length - 1 && (
            <div className={`w-4 h-px mx-0.5 ${i < activeIdx ? "bg-[var(--primary)]" : "bg-[var(--border)]"}`} />
          )}
        </div>
      ))}
    </div>
  );
}
