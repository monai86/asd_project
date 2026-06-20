import { AlertTriangle, CheckCircle2, Circle, ClipboardCheck } from "lucide-react";

import { sessionSteps } from "@/lib/mock-data";
import { StatusBadge } from "@/components/status-badge";

export function SessionStepper() {
  return (
    <ol className="grid gap-3">
      {sessionSteps.map((step, index) => {
        const status = step.status as string;
        const Icon = status === "Ready" || status === "Attested" ? CheckCircle2 : status === "Needs Review" ? AlertTriangle : Circle;
        return (
          <li key={step.name} className="clinical-card rounded-md p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <span className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-md border border-line bg-field text-clinical">
                  <Icon size={18} aria-hidden="true" />
                </span>
                <div>
                  <h2 className="text-base font-semibold">{index + 1}. {step.name}</h2>
                  <p className="mt-1 text-sm text-slate-600">{step.action}</p>
                  <p className="mt-2 flex items-start gap-2 text-xs text-safety">
                    <ClipboardCheck size={14} aria-hidden="true" />
                    {step.warning}
                  </p>
                </div>
              </div>
              <StatusBadge status={step.status} />
            </div>
            <p className="mt-4 text-sm font-medium text-clinical">Next action: {step.action}</p>
          </li>
        );
      })}
    </ol>
  );
}
