import Link from "next/link";

import { AppShell } from "@/components/app-shell";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { cases } from "@/lib/mock-data";

export default function CaseDetailPage({ params }: { params: { caseId: string } }) {
  const row = cases.find((item) => item.id === params.caseId) ?? cases[0];
  return (
    <AppShell>
      <PageHeader
        title={`Case ${row.childCode}`}
        description="Case detail keeps consent, sessions, progress, and latest review support together before entering a session workspace."
      />
      <p className="demo-note mb-4 rounded-md px-3 py-2 text-xs">
        Local demo data: this case detail is seeded mock content for workflow demonstration only.
      </p>
      <section className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <aside className="clinical-card rounded-md p-4">
          <h2 className="font-semibold">Child profile summary</h2>
          <dl className="mt-4 grid gap-3 text-sm">
            <div><dt className="text-slate-600">Nickname</dt><dd>{row.nickname}</dd></div>
            <div><dt className="text-slate-600">Age</dt><dd>{row.age}</dd></div>
            <div><dt className="text-slate-600">Language</dt><dd>{row.language}</dd></div>
            <div><dt className="text-slate-600">Consent status</dt><dd>{row.consentStatus}</dd></div>
            <div><dt className="text-slate-600">Review Priority</dt><dd className="capitalize">{row.reviewPriority}</dd></div>
          </dl>
          <Link href="/record" className="mt-5 inline-flex w-full justify-center rounded-md bg-clinical px-4 py-2 text-sm font-semibold text-white">
            Create new session
          </Link>
        </aside>
        <div className="grid gap-4">
          <section className="clinical-card rounded-md p-4">
            <h2 className="font-semibold">Session timeline</h2>
            <div className="mt-4 border-l border-line pl-4">
              <div className="mb-4">
                <p className="font-medium">{row.latestSessionDate}</p>
                <p className="text-sm text-slate-600">Therapy session transcript awaiting review</p>
                <div className="mt-2"><StatusBadge status={row.latestSessionStatus} /></div>
              </div>
            </div>
          </section>
          <section className="clinical-card rounded-md p-4">
            <h2 className="font-semibold">Progress overview</h2>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded border border-line p-3"><p className="text-xs text-slate-600">MLU trend</p><p className="font-semibold">Stable</p></div>
              <div className="rounded border border-line p-3"><p className="text-xs text-slate-600">NDW trend</p><p className="font-semibold">Needs more reviewed sessions</p></div>
              <div className="rounded border border-line p-3"><p className="text-xs text-slate-600">Report status</p><StatusBadge status={row.latestReportStatus} /></div>
            </div>
          </section>
          <section className="grid gap-4 lg:grid-cols-2">
            <div className="clinical-card rounded-md p-4">
              <h2 className="font-semibold">Therapy goal progress</h2>
              <div className="mt-4 grid gap-3 text-sm">
                <div className="rounded-md border border-line bg-field p-3">
                  <p className="font-medium">Increase reciprocal turns</p>
                  <p className="mt-1 text-slate-600">Tracked across reviewed sessions; therapist interpretation required.</p>
                </div>
                <div className="rounded-md border border-line bg-field p-3">
                  <p className="font-medium">Expand spontaneous comments</p>
                  <p className="mt-1 text-slate-600">Awaiting another attested transcript before progress summary.</p>
                </div>
              </div>
            </div>
            <div className="clinical-card rounded-md p-4">
              <h2 className="font-semibold">Before / after comparison</h2>
              <div className="mt-4 grid gap-3 text-sm">
                <div className="rounded-md border border-line bg-field p-3">
                  <p className="text-xs text-slate-600">Previous reviewed session</p>
                  <p className="font-medium">Baseline language sample recorded</p>
                </div>
                <div className="rounded-md border border-line bg-field p-3">
                  <p className="text-xs text-slate-600">Current reviewed session</p>
                  <p className="font-medium">Comparison remains descriptive until therapist signs report</p>
                </div>
              </div>
            </div>
          </section>
          <section className="clinical-card rounded-md p-4">
            <h2 className="font-semibold">Latest AI-assisted review summary</h2>
            <p className="mt-2 text-sm text-slate-700">
              Summary is pending therapist transcript attestation. AI-assisted text must be edited or rejected before report sign-off.
            </p>
          </section>
        </div>
      </section>
    </AppShell>
  );
}
