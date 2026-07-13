import {
  getBackendCase,
  listBackendCases,
} from "@/lib/workflow";

export const casesAdapter = {
  list: (signal: AbortSignal) => listBackendCases({ signal }),
  get: (caseId: string, signal: AbortSignal) => getBackendCase(caseId, { signal }),
};
