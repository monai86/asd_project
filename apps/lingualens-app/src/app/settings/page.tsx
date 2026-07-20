import { AppShell } from "@/components/app-shell";
import { PageHeader } from "@/components/page-header";
import { SettingsWorkspaceClient } from "@/components/settings-workspace-client";
import {
  isSettingsSection,
  type SettingsSection,
} from "@/features/settings/services/settings-access";

type SettingsPageProps = {
  searchParams?: Promise<SettingsSearchParams>;
};

type SettingsSearchParams = {
  section?: string | string[];
  scope?: string | string[];
  notice?: string | string[];
  role?: string | string[];
  case_id?: string | string[];
};

export default async function SettingsPage({ searchParams }: SettingsPageProps) {
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const initialSection = resolveRequestedSection(resolvedSearchParams);
  const notice = resolvedSearchParams?.notice === "not-authorized" ? "not-authorized" : undefined;
  const caseId = typeof resolvedSearchParams?.case_id === "string" ? resolvedSearchParams.case_id : undefined;

  return (
    <AppShell active="Settings">
      <PageHeader
        title="Settings"
        description="Therapist settings stay focused on profile, organization, sample data, and owned privacy operations."
      />
      <SettingsWorkspaceClient initialSection={initialSection} notice={notice} caseId={caseId} />
    </AppShell>
  );
}

function resolveRequestedSection(searchParams?: SettingsSearchParams): SettingsSection {
  if (isSettingsSection(searchParams?.section)) return searchParams.section;
  if (searchParams?.section === undefined && searchParams?.scope === "admin") return "team";
  return "profile";
}
