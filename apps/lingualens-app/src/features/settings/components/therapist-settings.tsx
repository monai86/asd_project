import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Bell,
  Building2,
  Download,
  Eye,
  HelpCircle,
  LockKeyhole,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import type { SharedSettingsSection } from "@/features/settings/services/settings-access";

export function TherapistSettings({ section }: { section: SharedSettingsSection }) {
  switch (section) {
    case "organization":
      return (
        <SettingsCard icon={Building2} title="Organization" description="Your current workspace context and authoritative data mode.">
          <SettingLine label="Organization" value="Pilot organization workspace" />
          <SettingLine label="Data mode" value="Demo mode" />
          <SettingLine label="Care team" value="Read-only summaries appear only for authorized cases" />
          <SettingLine label="Administration" value="Available only to organization admins" tone="muted" />
        </SettingsCard>
      );
    case "accessibility":
      return (
        <SettingsCard icon={Eye} title="Accessibility & Display" description="Readable defaults for Thai–Latin clinical work and touch interaction.">
          <SettingLine label="Product font" value="Noto Sans Thai / Noto Sans" />
          <SettingLine label="Accessibility mode" value="Optional accessibility mode not enabled" tone="muted" />
          <SettingLine label="Motion" value="Reduced motion follows your device preference" />
          <SettingLine label="Touch targets" value="44 px minimum on touch devices" />
        </SettingsCard>
      );
    case "notifications":
      return (
        <SettingsCard icon={Bell} title="Notifications" description="Operational notifications remain intentionally limited in this prototype.">
          <SettingLine label="In-app reminders" value="Available" />
          <SettingLine label="Email delivery" value="Not configured" tone="muted" />
          <SettingLine label="Caregiver messages" value="Not configured" tone="muted" />
          <SettingLine label="Clinical content in alerts" value="Not allowed" tone="warning" />
        </SettingsCard>
      );
    case "privacy":
      return (
        <div className="grid gap-4">
          <SettingsCard icon={LockKeyhole} title="Privacy & Security" description="Configured state only; this prototype makes no production-compliance claim.">
            <SettingLine label="Authentication" value="Demo workspace" />
            <SettingLine label="Credentials" value="Managed by the active authentication mode" />
            <SettingLine label="Production MFA" value="Not configured" tone="muted" />
            <SettingLine label="Session storage" value="UI cache only" />
          </SettingsCard>
          <section className="rounded-[var(--radius-card)] border border-amber-200 bg-amber-50 p-5 text-amber-950" aria-labelledby="owned-privacy-requests-title">
            <div className="flex items-start gap-3">
              <ShieldCheck size={22} aria-hidden="true" className="mt-0.5 shrink-0" />
              <div>
                <h2 id="owned-privacy-requests-title" className="text-lg font-semibold">Owned privacy requests</h2>
                <p className="mt-2 text-sm font-semibold">Unavailable in demo mode</p>
                <p className="mt-1 text-sm leading-6">
                  Production request history must come from a backend-confirmed authenticated identity; this screen does not infer an empty history.
                </p>
                <p className="mt-2 text-sm leading-6">No HIPAA compliance claim is made by this prototype workspace.</p>
              </div>
            </div>
          </section>
        </div>
      );
    case "export":
      return (
        <SettingsCard icon={Download} title="Export" description="Exports remain gated by transcript review, report validation, and sign-off.">
          <SettingLine label="Markdown export" value="Configured after sign-off" />
          <SettingLine label="HTML export" value="Configured after sign-off" />
          <SettingLine label="PDF export" value="Not configured" tone="muted" />
          <SettingLine label="Caregiver share status" value="Local/demo only" />
        </SettingsCard>
      );
    case "help":
      return (
        <SettingsCard icon={HelpCircle} title="Help" description="Use the clinical workflow in order and treat backend records as authoritative.">
          <SettingLine label="Transcript gate" value="Quality attestation required" />
          <SettingLine label="Report export" value="Sign-off required" />
          <SettingLine label="Clinical boundary" value="Decision-support only" />
          <SettingLine label="Pilot workspace" value="Anonymized demo data; no production accounts" />
        </SettingsCard>
      );
    case "account":
    default:
      return (
        <SettingsCard icon={UserRound} title="Account" description="Therapist workspace identity for the local pilot interface.">
          <SettingLine label="Name" value="Demo Therapist" />
          <SettingLine label="Role" value="Speech therapist / clinician" />
          <SettingLine label="Workspace start page" value="Today" />
          <SettingLine label="Data mode" value="Demo mode" />
        </SettingsCard>
      );
  }
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
    <section className="rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] p-5">
      <div className="flex items-start gap-3">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-[var(--radius-control)] bg-cyan-50 text-cyan-700">
          <Icon size={21} aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-xl font-semibold text-ink">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p>
        </div>
      </div>
      <div className="mt-5 divide-y divide-line/70 rounded-[var(--radius-control)] border border-line bg-field">
        {children}
      </div>
    </section>
  );
}

function SettingLine({ label, tone = "default", value }: { label: string; tone?: "default" | "muted" | "warning"; value: string }) {
  const valueClassName = tone === "warning" ? "text-amber-800" : tone === "muted" ? "text-slate-600" : "text-ink";
  return (
    <div className="grid gap-1 px-4 py-3 text-sm sm:grid-cols-[180px_1fr]">
      <span className="font-medium text-slate-600">{label}</span>
      <span className={`font-semibold ${valueClassName}`}>{value}</span>
    </div>
  );
}
