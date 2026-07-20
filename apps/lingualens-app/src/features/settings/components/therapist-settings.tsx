import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Bell,
  Download,
  HelpCircle,
  LockKeyhole,
  ShieldCheck,
  SlidersHorizontal,
  UserRound,
} from "lucide-react";

import { StatusTile } from "@/features/settings/components/settings-presentational";

export function TherapistSettings() {
  return (
    <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_330px]">
      <div className="grid gap-4 md:grid-cols-2">
        <SettingsCard icon={UserRound} title="Profile" description="Therapist workspace identity for the local pilot interface.">
          <SettingLine label="Name" value="Demo Therapist" />
          <SettingLine label="Role" value="Speech therapist / clinician" />
          <SettingLine label="Organization" value="Pilot organization workspace" />
          <SettingLine label="Data mode" value="Demo mode" />
        </SettingsCard>

        <SettingsCard icon={SlidersHorizontal} title="Preferences" description="Local interface defaults only; backend workflow records remain authoritative.">
          <SettingLine label="Workspace start page" value="Work Queue" />
          <SettingLine label="Sample data" value="Anonymized local demo data only" />
          <SettingLine label="Product font" value="Noto Sans Thai / Noto Sans" />
          <SettingLine label="Accessibility mode" value="Optional accessibility mode not enabled" tone="muted" />
          <SettingLine label="Language sample workflow" value="Transcript review first" />
          <SettingLine label="Experimental audio" value="Clearly labeled" />
        </SettingsCard>

        <SettingsCard icon={Bell} title="Notification preferences" description="Operational notification support is intentionally limited in this prototype.">
          <SettingLine label="In-app reminders" value="Available" />
          <SettingLine label="Email delivery" value="Not configured" tone="muted" />
          <SettingLine label="Caregiver messages" value="Not configured" tone="muted" />
          <SettingLine label="Clinical content in alerts" value="Not allowed" tone="warning" />
        </SettingsCard>

        <SettingsCard icon={Download} title="Export/report preferences" description="Exports stay gated by transcript review, report validation, and sign-off.">
          <SettingLine label="Markdown export" value="Configured after sign-off" />
          <SettingLine label="HTML export" value="Configured after sign-off" />
          <SettingLine label="PDF export" value="Not configured" tone="muted" />
          <SettingLine label="Caregiver share status" value="Local/demo only" />
        </SettingsCard>

        <SettingsCard icon={LockKeyhole} title="Security" description="Shows actual configured state; no production compliance claims are made here.">
          <SettingLine label="Authentication" value="Demo workspace" />
          <SettingLine label="Credentials" value="Managed by the active authentication mode" />
          <SettingLine label="Production MFA" value="Not configured" tone="muted" />
          <SettingLine label="Secure messaging" value="Not configured" tone="muted" />
          <SettingLine label="Session storage" value="UI cache only" />
        </SettingsCard>

        <section className="rounded-[1.5rem] border border-amber-200 bg-amber-50 p-5 text-amber-950">
          <div className="flex items-start gap-3">
            <ShieldCheck size={22} aria-hidden="true" className="mt-0.5 shrink-0" />
            <div>
              <h2 className="text-lg font-bold">Privacy & consent reminder</h2>
              <p className="mt-2 text-sm leading-6">
                Consent status must be checked per case before transcript review, feature extraction, report drafting, or export.
              </p>
              <p className="mt-2 text-sm leading-6">
                No HIPAA compliance claim is made by this prototype workspace.
              </p>
              <section className="mt-4 rounded-[var(--radius-card)] border border-amber-200 bg-[color:var(--color-surface-reading)] p-3" aria-labelledby="owned-privacy-requests-title">
                <h3 id="owned-privacy-requests-title" className="text-sm font-bold">Owned privacy requests</h3>
                <p className="mt-1 text-sm font-semibold">Unavailable in demo mode</p>
                <p className="mt-1 text-xs leading-5">
                  Production request history must come from a backend-confirmed authenticated identity; this screen does not infer an empty history.
                </p>
              </section>
            </div>
          </div>
        </section>
      </div>

      <aside className="space-y-4 xl:sticky xl:top-24 xl:self-start">
        <section className="clinical-card rounded-[1.5rem] p-5">
          <div className="flex h-11 w-11 items-center justify-center rounded-[var(--radius-panel)] bg-cyan-50 text-cyan-700">
            <HelpCircle size={22} aria-hidden="true" />
          </div>
          <h2 className="mt-4 text-lg font-bold text-ink">Help & guidance</h2>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            Use the session intake, transcript review, results, and report screens in order. Backend records are the source of truth when IDs exist.
          </p>
          <div className="mt-4 grid gap-3">
            <StatusTile label="Transcript gate" value="Quality attestation required" />
            <StatusTile label="Report export" value="Sign-off required" />
            <StatusTile label="Clinical boundary" value="Decision-support only" />
          </div>
        </section>

        <section className="rounded-[1.5rem] border border-cyan-100 bg-cyan-50 p-5">
          <h2 className="text-base font-bold text-cyan-950">Therapist pilot workspace</h2>
          <p className="mt-2 text-sm leading-6 text-cyan-950">
            This local path is for exploring the workspace with anonymized demo data. It does not create production accounts or production delivery channels.
          </p>
        </section>
      </aside>
    </section>
  );
}

function SettingsCard({
  children,
  description,
  icon: Icon,
  title,
}: {
  children: ReactNode;
  description: string;
  icon: LucideIcon;
  title: string;
}) {
  return (
    <section className="clinical-card rounded-[1.5rem] p-5">
      <div className="flex items-start gap-3">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-[var(--radius-panel)] bg-cyan-50 text-cyan-700">
          <Icon size={21} aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-lg font-bold text-ink">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p>
        </div>
      </div>
      <div className="mt-4 divide-y divide-line/70 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)]">
        {children}
      </div>
    </section>
  );
}

function SettingLine({ label, tone = "default", value }: { label: string; tone?: "default" | "muted" | "warning"; value: string }) {
  const valueClassName = tone === "warning" ? "text-amber-800" : tone === "muted" ? "text-slate-600" : "text-ink";
  return (
    <div className="grid gap-1 px-4 py-3 text-sm sm:grid-cols-[150px_1fr]">
      <span className="font-semibold text-slate-600">{label}</span>
      <span className={`font-bold ${valueClassName}`}>{value}</span>
    </div>
  );
}
