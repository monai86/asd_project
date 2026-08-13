import { redirect } from "next/navigation";

import { resolveLegacySessionHref } from "@/features/sessions/state/session-view";

type TranscriptSearchParams = {
  session_id?: string;
};

export default async function TranscriptPage({ searchParams }: {
  searchParams?: any;
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams as TranscriptSearchParams | undefined);

  redirect(resolveLegacySessionHref("transcript", resolvedSearchParams?.session_id));
}
