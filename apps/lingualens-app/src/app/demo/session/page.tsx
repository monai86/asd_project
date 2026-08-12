import { AppShell } from "@/components/app-shell";
import { SessionChatWorkspace } from "@/features/sessions/components/session-chat-workspace";

export default function DemoSessionPage() {
  return (
    <AppShell active="Session" activeSessionId="demo-001">
      <SessionChatWorkspace
        sessionId="demo-001"
        caseLabel="น้องออโต้ (Nong Auto) — 3 ปี 4 เดือน"
        childAge="3y 4m"
        status="transcript"
      />
    </AppShell>
  );
}
