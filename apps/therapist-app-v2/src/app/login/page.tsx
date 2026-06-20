import { WorkflowVisual } from "@/components/app-shell";
import { MockLoginFormClient } from "@/components/mock-login-form-client";

export default function LoginPage() {
  return (
    <main className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[1fr_420px]">
        <section>
          <p className="mb-3 inline-flex rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-safety">
            Mock mode: no real clinical data
          </p>
          <h1 className="text-3xl font-semibold tracking-normal text-ink sm:text-4xl">Therapist App v2</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-700">
            Case-centered workspace for transcript review, feature extraction, AI-assisted summaries, and therapist-signed reports.
          </p>
          <div className="mt-6">
            <WorkflowVisual />
          </div>
        </section>
        <MockLoginFormClient />
      </div>
    </main>
  );
}
