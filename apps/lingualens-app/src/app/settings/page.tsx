import { AppShell } from "@/components/app-shell";
import { PageHeader } from "@/components/page-header";
import { SettingsWorkspaceClient } from "@/components/settings-workspace-client";

type SettingsPageProps = {
  searchParams?: any;
};

type SettingsSearchParams = {
    scope?: string;
};

export default async function SettingsPage({ searchParams }: SettingsPageProps) {
  const resolvedSearchParams = await Promise.resolve(searchParams as SettingsSearchParams | undefined);
  const initialScope = resolvedSearchParams?.scope === "admin" ? "admin" : "therapist";

  return (
    <AppShell>
      <PageHeader
        title="Settings / Admin"
        description="Therapist settings stay focused on profile, organization, sample data, and owned privacy operations."
      />
      <SettingsWorkspaceClient initialScope={initialScope} />
    </AppShell>
  );
}
