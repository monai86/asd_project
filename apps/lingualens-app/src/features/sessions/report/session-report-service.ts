import { ApiError } from "@/lib/api";
import {
  exportBackendReport,
  exportReviewedCha,
  finalizeBackendReport,
  generateBackendReport,
  getBackendCase,
  getBackendReport,
  getBackendSession,
  getBackendTranscript,
  updateBackendReport,
} from "@/lib/workflow";

export type SessionReportLocator = {
  caseId?: string;
  sessionId?: string;
  transcriptId?: string;
  reportId?: string;
};

export const sessionReportService = {
  async load({ caseId, sessionId, transcriptId, reportId }: SessionReportLocator) {
    const session = sessionId ? await getBackendSession(sessionId) : undefined;
    const resolvedReportId = reportId ?? session?.report_id;
    if (!resolvedReportId) throw new ApiError(404, "Report not found.");

    const resolvedTranscriptId = transcriptId ?? session?.transcript_id;
    const [report, transcript] = await Promise.all([
      getBackendReport(resolvedReportId),
      resolvedTranscriptId ? getBackendTranscript(resolvedTranscriptId) : Promise.resolve(undefined),
    ]);
    const resolvedCaseId = caseId ?? report.case_id ?? session?.case_id;
    const childCase = resolvedCaseId ? await getBackendCase(resolvedCaseId) : undefined;

    return { session, report, transcript, childCase, resolvedReportId, resolvedCaseId };
  },

  generate: generateBackendReport,
  save: updateBackendReport,
  export: exportBackendReport,
  exportReviewedTranscript: exportReviewedCha,
  finalize: finalizeBackendReport,
  createRevision: updateBackendReport,
};
