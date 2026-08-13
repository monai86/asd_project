import { redirect } from "next/navigation";

import { resolveLegacySessionHref } from "@/features/sessions/state/session-view";

type ReviewTranscriptSearchParams = {
  session_id?: string;
};

export default async function ReviewTranscriptPage({ searchParams }: {
  searchParams?: any;
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams as ReviewTranscriptSearchParams | undefined);

  redirect(resolveLegacySessionHref("transcript", resolvedSearchParams?.session_id));
}
