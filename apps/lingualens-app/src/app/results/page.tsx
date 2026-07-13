import { redirect } from "next/navigation";

import { resolveLegacySessionHref } from "@/features/sessions/state/session-view";

type ResultsSearchParams = {
  session_id?: string;
};

export default async function ResultsPage({ searchParams }: {
  searchParams?: any;
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams as ResultsSearchParams | undefined);

  redirect(resolveLegacySessionHref("findings", resolvedSearchParams?.session_id));
}
