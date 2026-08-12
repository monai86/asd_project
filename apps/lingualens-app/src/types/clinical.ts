export interface ClinicalCase {
  id: string;
  childName: string;
  ageYearsMonths: string;
  gender?: string;
  updatedAt: string;
}

export interface ClinicalSession {
  id: string;
  caseId: string;
  status: "intake" | "transcript" | "findings" | "report" | "signed_off";
  createdAt: string;
  transcriptText?: string;
  findings?: Record<string, unknown>;
  reportDraft?: string;
}
