import { redirect } from "next/navigation";

import { resolveLegacySessionHref } from "@/features/sessions/state/session-view";

type ReportSummarySearchParams = {
  session_id?: string;
};

export default async function ReportSummaryPage({ searchParams }: {
  searchParams?: any;
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams as ReportSummarySearchParams | undefined);

  redirect(resolveLegacySessionHref("report", resolvedSearchParams?.session_id));
}
