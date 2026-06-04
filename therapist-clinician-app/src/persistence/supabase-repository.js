import { supabase as defaultSupabase } from "../services/supabase-client.js";

export const SUPABASE_REPOSITORY_TABLES = [
  "users",
  "child_cases",
  "sessions",
  "consent_records",
  "transcripts",
  "transcript_lines",
  "audio_files",
  "processing_jobs",
  "extracted_features",
  "ai_screening_outputs",
  "therapy_goals",
  "therapist_notes",
  "reports",
  "clinical_signoffs",
  "privacy_operations"
];

export class SupabaseRepositoryConfigurationError extends Error {
  constructor(message) {
    super(message);
    this.name = "SupabaseRepositoryConfigurationError";
  }
}

export class SupabaseRepositoryRequestError extends Error {
  constructor(message, { table, operation, cause } = {}) {
    super(message);
    this.name = "SupabaseRepositoryRequestError";
    this.table = table;
    this.operation = operation;
    this.cause = cause;
  }
}

function assertClient(client) {
  if (!client?.from) {
    throw new SupabaseRepositoryConfigurationError(
      "Supabase data mode requires VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY."
    );
  }
  return client;
}

function uuid() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `pilot-${Math.random().toString(36).slice(2)}-${Date.now().toString(36)}`;
}

async function execute(query, { table, operation }) {
  const { data, error } = await query;
  if (error) {
    throw new SupabaseRepositoryRequestError(error.message || `Supabase ${operation} failed.`, {
      table,
      operation,
      cause: error
    });
  }
  return data;
}

async function selectRows(client, table, { orderBy = "created_at", ascending = false } = {}) {
  let query = client.from(table).select("*");
  if (orderBy && typeof query.order === "function") {
    query = query.order(orderBy, { ascending });
  }
  return execute(query, { table, operation: "select" }).then(rows => rows || []);
}

async function selectCurrentUser(client, authUser) {
  if (!authUser?.id) return null;
  const query = client.from("users").select("*").eq("user_id", authUser.id).maybeSingle?.()
    || client.from("users").select("*").eq("user_id", authUser.id).single();
  const profile = await execute(query, { table: "users", operation: "select current user" }).catch(() => null);
  if (profile) return profile;

  const metadata = authUser.user_metadata || {};
  const appMetadata = authUser.app_metadata || {};
  return {
    user_id: authUser.id,
    email: authUser.email,
    name: metadata.name || authUser.email || "Clinical User",
    role: appMetadata.role || metadata.role || "therapist",
    organization: metadata.organization || "",
    credentials: metadata.credentials || "",
    last_login: new Date().toISOString()
  };
}

function rowsBySessionId(rows, idField) {
  return Object.fromEntries((rows || []).map(row => [row.session_id || row[idField], row]));
}

function linesBySessionId(rows) {
  return (rows || []).reduce((acc, row) => {
    const sessionId = row.session_id;
    if (!sessionId) return acc;
    acc[sessionId] = [...(acc[sessionId] || []), row];
    return acc;
  }, {});
}

function emptySnapshot(currentUser) {
  return {
    users: currentUser ? [currentUser] : [],
    child_cases: [],
    sessions: [],
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
    privacy_operations: [],
    audit_logs: [],
    therapist_thai_summaries: {}
  };
}

export function createSupabaseRepository({ client = defaultSupabase } = {}) {
  const activeClient = assertClient(client);

  async function getAuthUser() {
    if (!activeClient.auth?.getUser) return null;
    const { data, error } = await activeClient.auth.getUser();
    if (error) {
      throw new SupabaseRepositoryRequestError(error.message || "Supabase auth user lookup failed.", {
        table: "auth.users",
        operation: "getUser",
        cause: error
      });
    }
    return data?.user || null;
  }

  async function currentUser() {
    return selectCurrentUser(activeClient, await getAuthUser());
  }

  async function insertRow(table, row) {
    const query = activeClient.from(table).insert(row).select("*").single();
    return execute(query, { table, operation: "insert" });
  }

  async function patchRow(table, idField, id, payload) {
    const query = activeClient.from(table).update({ ...payload, updated_at: new Date().toISOString() }).eq(idField, id).select("*").single();
    return execute(query, { table, operation: "update" });
  }

  return {
    async hydrate() {
      const user = await currentUser();
      const snapshot = emptySnapshot(user);
      if (!user) return snapshot;

      const [
        cases,
        sessions,
        consentRecords,
        transcripts,
        transcriptLines,
        audioFiles,
        processingJobs,
        extractedFeatures,
        aiOutputs,
        therapyGoals,
        therapistNotes,
        reports,
        clinicalSignoffs,
        privacyOperations
      ] = await Promise.all([
        selectRows(activeClient, "child_cases"),
        selectRows(activeClient, "sessions", { orderBy: "session_date", ascending: false }),
        selectRows(activeClient, "consent_records"),
        selectRows(activeClient, "transcripts"),
        selectRows(activeClient, "transcript_lines", { orderBy: "line_number", ascending: true }),
        selectRows(activeClient, "audio_files"),
        selectRows(activeClient, "processing_jobs"),
        selectRows(activeClient, "extracted_features"),
        selectRows(activeClient, "ai_screening_outputs"),
        selectRows(activeClient, "therapy_goals"),
        selectRows(activeClient, "therapist_notes"),
        selectRows(activeClient, "reports"),
        selectRows(activeClient, "clinical_signoffs"),
        selectRows(activeClient, "privacy_operations")
      ]);

      return {
        ...snapshot,
        child_cases: cases,
        sessions,
        consent_records: consentRecords,
        transcripts: rowsBySessionId(transcripts, "transcript_id"),
        transcript_lines: linesBySessionId(transcriptLines),
        audio_files: audioFiles,
        processing_jobs: processingJobs,
        extracted_features: rowsBySessionId(extractedFeatures, "feature_id"),
        ai_screening_outputs: rowsBySessionId(aiOutputs, "output_id"),
        therapy_goals: therapyGoals,
        therapist_notes: therapistNotes,
        reports,
        clinical_signoffs: clinicalSignoffs,
        privacy_operations: privacyOperations,
        audit_logs: []
      };
    },

    async createCase(payload) {
      const user = await currentUser();
      if (!user) throw new SupabaseRepositoryConfigurationError("Cannot create a case without a signed-in Supabase user.");
      return insertRow("child_cases", {
        case_id: uuid(),
        owner_user_id: user.user_id,
        display_label: payload.display_label || payload.anonymized_child_code,
        external_clinical_status: "not_provided",
        notes: "",
        ...payload,
        age_months: Number.parseInt(payload.age_months, 10) || 48
      });
    },

    patchCase(caseId, payload) {
      return patchRow("child_cases", "case_id", caseId, payload);
    },

    async recordConsent(caseId, payload) {
      const user = await currentUser();
      if (!user) throw new SupabaseRepositoryConfigurationError("Cannot record consent without a signed-in Supabase user.");
      const record = await insertRow("consent_records", {
        consent_id: uuid(),
        case_id: caseId,
        owner_user_id: user.user_id,
        recorded_by_user_id: user.user_id,
        consent_type: "clinical_audio_processing",
        guardian_status: "guardian",
        transcript_permission: true,
        notes: "",
        ...payload
      });
      if (payload.audio_permission === true || payload.transcript_permission === true) {
        await patchRow("child_cases", "case_id", caseId, { consent_status: "granted" }).catch(() => null);
      }
      return record;
    },

    async createSession(payload) {
      const user = await currentUser();
      if (!user) throw new SupabaseRepositoryConfigurationError("Cannot create a session without a signed-in Supabase user.");
      return insertRow("sessions", {
        session_id: uuid(),
        owner_user_id: user.user_id,
        processing_status: "not_started",
        feature_extraction_status: "not_started",
        ai_analysis_status: "not_started",
        therapist_review_status: "not_started",
        report_status: "not_started",
        notes: "",
        ...payload
      });
    },

    patchSession(sessionId, payload) {
      return patchRow("sessions", "session_id", sessionId, payload);
    },

    async patchTranscriptLine(transcriptId, lineId, payload) {
      if (payload.expected_version) {
        const existing = await execute(
          activeClient.from("transcript_lines").select("version").eq("line_id", lineId).single(),
          { table: "transcript_lines", operation: "select version" }
        );
        if (existing?.version !== payload.expected_version) {
          throw new SupabaseRepositoryRequestError("Transcript line has changed. Reload before saving.", {
            table: "transcript_lines",
            operation: "update"
          });
        }
      }
      const update = {
        ...payload,
        speaker_code: payload.speaker_code,
        utterance_text: payload.utterance_text || payload.text,
        version: payload.expected_version ? payload.expected_version + 1 : undefined,
        updated_at: new Date().toISOString()
      };
      delete update.text;
      delete update.expected_version;
      Object.keys(update).forEach(key => update[key] === undefined && delete update[key]);
      return execute(
        activeClient.from("transcript_lines").update(update).eq("transcript_id", transcriptId).eq("line_id", lineId).select("*").single(),
        { table: "transcript_lines", operation: "update" }
      );
    },

    async getReferenceComparison() {
      throw new SupabaseRepositoryConfigurationError("Reference Comparison still requires the backend processing API in Supabase pilot mode.");
    },

    async getCaseProgress(caseId) {
      const [features, aiOutputs, reports] = await Promise.all([
        selectRows(activeClient, "extracted_features"),
        selectRows(activeClient, "ai_screening_outputs"),
        selectRows(activeClient, "reports")
      ]);
      return {
        case_id: caseId,
        features: features.filter(row => row.case_id === caseId),
        ai_screening_outputs: aiOutputs.filter(row => row.case_id === caseId),
        reports: reports.filter(row => row.case_id === caseId)
      };
    },

    async createProgressReport(sessionId) {
      const user = await currentUser();
      if (!user) throw new SupabaseRepositoryConfigurationError("Cannot create a report without a signed-in Supabase user.");
      const session = await execute(
        activeClient.from("sessions").select("*").eq("session_id", sessionId).single(),
        { table: "sessions", operation: "select session" }
      );
      return insertRow("reports", {
        report_id: uuid(),
        case_id: session.case_id,
        session_id: sessionId,
        owner_user_id: user.user_id,
        report_type: "progress",
        title: `Progress report for ${session.session_date}`,
        content_markdown: "Supabase pilot report shell. Generate full clinical report through the reviewed report workflow.",
        export_status: "not_started"
      });
    }
  };
}
