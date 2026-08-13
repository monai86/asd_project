"use client";

import { SessionWorkspace, type SessionWorkspaceProps } from "@/features/sessions/components/session-workspace";

type SessionWorkspaceClientProps = Omit<SessionWorkspaceProps, "view"> & {
  view?: string;
};

export function SessionWorkspaceClient({ view, ...props }: SessionWorkspaceClientProps) {
  return (
    <SessionWorkspace
      {...props}
      view={view === "transcript" ? "transcript" : view === "results" ? "findings" : "intake"}
    />
  );
}
