import { AppShell } from "@/components/app-shell";
import { PageHeader } from "@/components/page-header";
import { SettingsWorkspaceClient } from "@/components/settings-workspace-client";

type SettingsPageProps = {
  searchParams?: {
    scope?: string;
  };
};

export default function SettingsPage({ searchParams }: SettingsPageProps) {
  const initialScope = searchParams?.scope === "admin" ? "admin" : "therapist";

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
