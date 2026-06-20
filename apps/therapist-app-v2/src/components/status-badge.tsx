import type { Status } from "@/lib/mock-data";

const styles: Record<Status, string> = {
  Draft: "border-slate-300 bg-white text-slate-700",
  "Needs Review": "border-amber-300 bg-amber-50 text-amber-900",
  Attested: "border-teal-300 bg-teal-50 text-teal-900",
  Processing: "border-sky-300 bg-sky-50 text-sky-900",
  Failed: "border-red-300 bg-red-50 text-red-900",
  Ready: "border-emerald-300 bg-emerald-50 text-emerald-900",
  "Signed Off": "border-moss bg-moss text-white"
};

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span className={`inline-flex min-h-7 min-w-24 items-center justify-center rounded-md border px-2.5 py-1 text-xs font-semibold ${styles[status]}`}>
      {status}
    </span>
  );
}
