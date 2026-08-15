import {
  createBackendCase,
  getBackendCase,
  listBackendCases,
  type BackendCase,
} from "@/lib/workflow";
import type { CreateCaseFormValues } from "@/features/cases/schemas/create-case-schema";

export const casesAdapter = {
  list: (signal: AbortSignal) => listBackendCases({ signal }),
  get: (caseId: string, signal: AbortSignal) => getBackendCase(caseId, { signal }),
  create: (payload: CreateCaseFormValues): Promise<BackendCase> => createBackendCase({
    ...payload,
    nickname: payload.nickname || undefined,
    notes: payload.notes || "",
    consent_status: "pending",
  }),
};
