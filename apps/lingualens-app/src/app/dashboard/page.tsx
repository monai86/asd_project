import { AppShell } from "@/components/app-shell";
import { PracticeDashboardView } from "@/features/dashboard/components/practice-dashboard-view";
import { getDashboardSummary } from "@/lib/workflow";

// The practice summary is live backend data — never statically cache it.
export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  let summary;
  try {
    summary = await getDashboardSummary();
  } catch {
    summary = undefined;
  }

  return (
    <AppShell active="Dashboard">
      {summary ? (
        <PracticeDashboardView summary={summary} />
      ) : (
        <main className="mx-auto flex min-h-dvh w-full max-w-3xl items-center px-4 py-10 sm:px-6">
          <section className="w-full rounded-2xl border border-slate-200 bg-white p-6 shadow-xl text-slate-900" role="alert">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Dashboard unavailable</p>
            <h1 className="mt-3 text-3xl font-semibold text-slate-900">Practice summary could not be loaded</h1>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              The backend summary endpoint did not respond. Your existing case and session views remain available.
            </p>
            <a
              href="/today"
              className="mt-5 inline-flex min-h-11 items-center rounded-lg bg-slate-900 px-4 text-sm font-semibold text-white transition hover:bg-slate-700"
            >
              Back to Today
            </a>
          </section>
        </main>
      )}
    </AppShell>
  );
}
