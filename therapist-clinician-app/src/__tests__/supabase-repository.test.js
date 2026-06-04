import { describe, expect, it } from "vitest";
import { createSupabaseRepository } from "../persistence/supabase-repository.js";

function createQuery({ table, db, op = "select" }) {
  const state = {
    table,
    op,
    filters: [],
    orderBy: null,
    payload: null,
    single: false,
    maybeSingle: false
  };

  const query = {
    select() {
      return query;
    },
    order(field, options = {}) {
      state.orderBy = { field, ascending: options.ascending !== false };
      return query;
    },
    eq(field, value) {
      state.filters.push({ field, value });
      return query;
    },
    insert(payload) {
      state.op = "insert";
      state.payload = Array.isArray(payload) ? payload : [payload];
      return query;
    },
    update(payload) {
      state.op = "update";
      state.payload = payload;
      return query;
    },
    single() {
      state.single = true;
      return query;
    },
    maybeSingle() {
      state.maybeSingle = true;
      return query;
    },
    then(resolve, reject) {
      return Promise.resolve(runQuery(state, db)).then(resolve, reject);
    }
  };

  return query;
}

function runQuery(state, db) {
  const rows = db[state.table] || [];
  if (state.op === "insert") {
    db[state.table] = [...rows, ...state.payload];
    return { data: state.single || state.maybeSingle ? state.payload[0] : state.payload, error: null };
  }
  if (state.op === "update") {
    const updated = rows.map(row => {
      const match = state.filters.every(filter => row[filter.field] === filter.value);
      return match ? { ...row, ...state.payload } : row;
    });
    db[state.table] = updated;
    const matches = updated.filter(row => state.filters.every(filter => row[filter.field] === filter.value));
    return { data: state.single || state.maybeSingle ? matches[0] || null : matches, error: null };
  }
  let selected = rows.filter(row => state.filters.every(filter => row[filter.field] === filter.value));
  if (state.orderBy) {
    const direction = state.orderBy.ascending ? 1 : -1;
    selected = [...selected].sort((a, b) => String(a[state.orderBy.field] || "").localeCompare(String(b[state.orderBy.field] || "")) * direction);
  }
  return { data: state.single || state.maybeSingle ? selected[0] || null : selected, error: null };
}

function createClient(seed = {}) {
  const db = {
    users: [{ user_id: "therapist_a", email: "a@example.test", role: "therapist", name: "Therapist A" }],
    child_cases: [{ case_id: "CASE-A", owner_user_id: "therapist_a", anonymized_child_code: "CHI-A", created_at: "2026-01-01" }],
    sessions: [{ session_id: "SESSION-A", case_id: "CASE-A", owner_user_id: "therapist_a", session_date: "2026-01-02" }],
    consent_records: [],
    transcripts: [{ transcript_id: "TRANSCRIPT-A", session_id: "SESSION-A", case_id: "CASE-A", owner_user_id: "therapist_a" }],
    transcript_lines: [{ line_id: "LINE-A", transcript_id: "TRANSCRIPT-A", session_id: "SESSION-A", case_id: "CASE-A", owner_user_id: "therapist_a", line_number: 1, version: 1 }],
    audio_files: [],
    processing_jobs: [],
    extracted_features: [{ feature_id: "FEATURE-A", session_id: "SESSION-A", case_id: "CASE-A", owner_user_id: "therapist_a" }],
    ai_screening_outputs: [{ output_id: "AI-A", session_id: "SESSION-A", case_id: "CASE-A", owner_user_id: "therapist_a" }],
    therapy_goals: [],
    therapist_notes: [],
    reports: [],
    clinical_signoffs: [],
    privacy_operations: [],
    ...seed
  };
  return {
    db,
    auth: {
      async getUser() {
        return { data: { user: { id: "therapist_a", email: "a@example.test", user_metadata: { role: "therapist", name: "Therapist A" } } }, error: null };
      }
    },
    from(table) {
      return createQuery({ table, db });
    }
  };
}

describe("Supabase repository boundary", () => {
  it("hydrates RLS-visible clinical collections without exposing audit logs", async () => {
    const client = createClient();
    const repository = createSupabaseRepository({ client });

    const snapshot = await repository.hydrate();

    expect(snapshot.users).toEqual([{ user_id: "therapist_a", email: "a@example.test", role: "therapist", name: "Therapist A" }]);
    expect(snapshot.child_cases).toHaveLength(1);
    expect(snapshot.sessions).toHaveLength(1);
    expect(snapshot.transcripts["SESSION-A"].transcript_id).toBe("TRANSCRIPT-A");
    expect(snapshot.transcript_lines["SESSION-A"]).toHaveLength(1);
    expect(snapshot.extracted_features["SESSION-A"].feature_id).toBe("FEATURE-A");
    expect(snapshot.ai_screening_outputs["SESSION-A"].output_id).toBe("AI-A");
    expect(snapshot.audit_logs).toEqual([]);
  });

  it("creates anonymized cases, consent records, sessions, and optimistic transcript line updates", async () => {
    const client = createClient();
    const repository = createSupabaseRepository({ client });

    const childCase = await repository.createCase({
      anonymized_child_code: "CHI-B",
      age_months: "50",
      sex: "not_specified",
      primary_concerns: "language sample review",
      consent_status: "pending",
      anonymization_status: "anonymized"
    });
    const consent = await repository.recordConsent(childCase.case_id, { audio_permission: true });
    const session = await repository.createSession({
      case_id: childCase.case_id,
      session_date: "2026-06-04",
      session_type: "therapy_session",
      notes: "pilot"
    });
    const line = await repository.patchTranscriptLine("TRANSCRIPT-A", "LINE-A", {
      text: "updated utterance",
      reviewed: true,
      expected_version: 1
    });

    expect(childCase.owner_user_id).toBe("therapist_a");
    expect(consent.recorded_by_user_id).toBe("therapist_a");
    expect(session.case_id).toBe(childCase.case_id);
    expect(line.utterance_text).toBe("updated utterance");
    expect(line.version).toBe(2);
  });
});
