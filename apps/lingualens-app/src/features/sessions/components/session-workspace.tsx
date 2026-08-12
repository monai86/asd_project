"use client";

import dynamic from "next/dynamic";
import { resolveWorkspaceFeature, type SessionView } from "@/features/sessions/state/session-view";
import { SessionChatWorkspace } from "@/features/sessions/components/session-chat-workspace";
import { ClinicalPdfReport } from "@/features/reports/components/clinical-pdf-report";

const SessionReportView = dynamic(
  () => import("@/features/sessions/report/session-report-view").then((module) => module.SessionReportView),
  { loading: SessionWorkspaceLoading },
);

export type SessionWorkspaceProps = {
  sessionId?: string;
  caseId?: string;
  transcriptId?: string;
  reportId?: string;
  view?: SessionView;
  mode?: string;
};

export function SessionWorkspace({ view = "intake", sessionId = "session-001", caseId }: SessionWorkspaceProps) {
  if (view === "report") {
    return (
      <ClinicalPdfReport
        data={{
          childName: "น้องออโต้ (Nong Auto)",
          childCode: caseId || "CASE-001",
          age: "3 ปี 4 เดือน",
          gender: "ชาย",
          evaluator: "อ.สมศรี รักภาษา, นักอรรถบำบัด",
          date: new Date().toLocaleDateString("th-TH", { year: "numeric", month: "long", day: "numeric" }),
          location: "คลินิกภาษาและการสื่อสาร",
          talkBankScore: 0.82,
          receptiveScore: 0.78,
          expressiveScore: 0.71,
          receptiveSummary: "เข้าใจคำสั่ง 2 ขั้นตอนได้ดี ชี้วัตถุตามคำสั่งได้ถูกต้องประมาณ 80% ของชุดทดสอบ",
          expressiveSummary: "พูดเป็นประโยค 3-4 คำได้ ใช้คำเชื่อมอย่างง่ายได้ มีการออกเสียงพยัญชนะต้น ร/ล ไม่ชัดเจนตามวัย",
          pragmaticsSummary: "สบตาได้ตามวัย ตอบสนองเมื่อถูกเรียกชื่อ มีข้อจำกัดในการเริ่มบทสนทนาด้วยตนเอง",
          behavioralObservations: "ร่วมมือดีตลอดการประเมิน มีช่วงสมาธิสั้นเมื่อกิจกรรมเปลี่ยน ต้องให้คำชมเชยเป็นระยะ",
          recommendations: [
            "ฝึกการเล่าเรื่องตามลำดับเหตุการณ์ (Story Sequencing)",
            "เพิ่มกิจกรรมเล่นสมมติ (Pretend Play)",
            "ฝึกการออกเสียง ร/ล ผ่านกิจกรรมเลียนเสียง",
            "ใช้เทคนิค Expansion ขยายประโยคของเด็กให้ยาวขึ้น",
          ],
          signedAt: new Date().toISOString(),
          hash: "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890",
          reportVersion: "1.0",
        }}
      />
    );
  }

  return (
    <SessionChatWorkspace
      sessionId={sessionId}
      caseLabel={caseId ? `Child Case: ${caseId}` : "น้องออโต้ (Nong Auto) — 3y 4m"}
      childAge="3y 4m"
      status={view}
    />
  );
}

function SessionWorkspaceLoading() {
  return (
    <div
      className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm"
      role="status"
      aria-live="polite"
    >
      Loading session workspace…
    </div>
  );
}

export { resolveWorkspaceFeature };
