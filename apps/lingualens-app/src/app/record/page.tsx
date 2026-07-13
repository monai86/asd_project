import { redirect } from "next/navigation";

import { resolveLegacySessionHref } from "@/features/sessions/state/session-view";

type RecordSearchParams = {
  session_id?: string;
};

export default async function RecordPage({ searchParams }: {
  searchParams?: any;
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams as RecordSearchParams | undefined);

  redirect(resolveLegacySessionHref("intake", resolvedSearchParams?.session_id));
}
