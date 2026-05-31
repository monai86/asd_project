export const API_REPOSITORY_ROUTES = {
  me: "GET /api/me",
  cases: "GET /api/cases",
  createCase: "POST /api/cases",
  patchCase: "PATCH /api/cases/:caseId",
  recordConsent: "POST /api/cases/:caseId/consent",
  sessions: "GET /api/sessions",
  createSession: "POST /api/sessions",
  patchSession: "PATCH /api/sessions/:sessionId",
  patchTranscriptLine: "PATCH /api/transcripts/:transcriptId/lines/:lineId",
  caseProgress: "GET /api/cases/:caseId/progress",
  createProgressReport: "POST /api/sessions/:sessionId/report",
  auditLogs: "GET /api/audit-logs"
};

export function createApiRepository({ apiClient }) {
  if (!apiClient) {
    throw new Error("API repository requires an authenticated apiClient.");
  }

  return {
    async hydrate() {
      const [me, cases, sessions, auditLogs] = await Promise.all([
        apiClient.get("/api/me"),
        apiClient.get("/api/cases"),
        apiClient.get("/api/sessions"),
        apiClient.get("/api/audit-logs").catch(() => [])
      ]);

      const currentUser = me?.user || null;
      return {
        users: currentUser ? [currentUser] : [],
        child_cases: cases || [],
        sessions: sessions || [],
        consent_records: [],
        transcripts: {},
        transcript_lines: {},
        audio_files: [],
        processing_jobs: [],
        extracted_features: {},
        ai_screening_outputs: {},
        therapy_goals: [],
        therapist_notes: [],
        reports: [],
        clinical_signoffs: [],
        audit_logs: auditLogs || []
      };
    },

    createCase(payload) {
      return apiClient.post("/api/cases", payload);
    },

    patchCase(caseId, payload) {
      return apiClient.patch(`/api/cases/${caseId}`, payload);
    },

    recordConsent(caseId, payload) {
      return apiClient.post(`/api/cases/${caseId}/consent`, payload);
    },

    createSession(payload) {
      return apiClient.post("/api/sessions", payload);
    },

    patchSession(sessionId, payload) {
      return apiClient.patch(`/api/sessions/${sessionId}`, payload);
    },

    patchTranscriptLine(transcriptId, lineId, payload) {
      return apiClient.patch(`/api/transcripts/${transcriptId}/lines/${lineId}`, payload);
    },

    getCaseProgress(caseId) {
      return apiClient.get(`/api/cases/${caseId}/progress`);
    },

    createProgressReport(sessionId) {
      return apiClient.post(`/api/sessions/${sessionId}/report`, {});
    }
  };
}
