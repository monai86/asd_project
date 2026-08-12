import { ClinicalCase, ClinicalSession } from "@/types/clinical";

export type { ClinicalCase, ClinicalSession };

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

const MOCK_CASES: ClinicalCase[] = [
  { id: "case-001", childName: "น้องออโต้ (Nong Auto)", ageYearsMonths: "3y 4m", gender: "M", updatedAt: "2026-08-12" },
  { id: "case-002", childName: "น้องมะลิ (Nong Mali)", ageYearsMonths: "4y 1m", gender: "F", updatedAt: "2026-08-11" }
];

export async function fetchCases(): Promise<ClinicalCase[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/cases`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("FastAPI offline or unreachable, using local fallback cases:", err);
    return MOCK_CASES;
  }
}

export async function fetchSession(sessionId: string): Promise<ClinicalSession> {
  try {
    const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("FastAPI offline, using local fallback session:", err);
    return {
      id: sessionId,
      caseId: "case-001",
      status: "transcript",
      createdAt: new Date().toISOString(),
      transcriptText: "CHI: ช้าง ใหญ่\nINV: ใช่แล้ว ช้างตัวใหญ่มากเลยครับ",
      findings: { talkBankScore: 0.82, riskCue: "moderate_receptive_delay" },
      reportDraft: "ผลการประเมินพัฒนาการทางภาษาและการสื่อสารของเด็ก..."
    };
  }
}
