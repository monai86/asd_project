import { Check, Circle } from "lucide-react";

type WorkflowStepStatus = "complete" | "current" | "pending";

export type WorkflowStepItem = {
  id: string;
  title: string;
  helper?: string;
  status: WorkflowStepStatus;
};

const statusClasses: Record<WorkflowStepStatus, string> = {
  complete: "border-[color:var(--color-success-border)] bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]",
  current: "border-[color:var(--color-accent-subtle)] bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]",
  pending: "border-[color:var(--color-border-strong)] bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-muted)]"
};

export function WorkflowStepper({ steps }: { steps: WorkflowStepItem[] }) {
  return (
    <ol
      className="grid gap-3 md:grid-cols-3"
      aria-label="Workflow progress"
      role="list"
    >
      {steps.map((step) => (
        <li
          key={step.id}
          className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4 shadow-soft"
          aria-current={step.status === "current" ? "step" : undefined}
        >
          <div className="flex items-start gap-3">
            <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-2xl border ${statusClasses[step.status]}`}>
              {step.status === "complete" ? <Check size={18} aria-hidden="true" /> : <Circle size={16} aria-hidden="true" fill="currentColor" />}
            </span>
            <div>
              <p className="font-semibold text-[color:var(--color-text-strong)]">{step.title}</p>
              {step.helper ? <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">{step.helper}</p> : null}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
