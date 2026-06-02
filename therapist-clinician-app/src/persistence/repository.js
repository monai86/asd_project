import { DATA_MODE, normalizeDataMode } from "../constants.js";

export const PERSISTED_COLLECTIONS = [
  "users",
  "child_cases",
  "sessions",
  "transcripts",
  "transcript_lines",
  "audio_files",
  "consent_records",
  "processing_jobs",
  "extracted_features",
  "ai_screening_outputs",
  "therapy_goals",
  "therapist_notes",
  "reports",
  "clinical_signoffs",
  "privacy_operations",
  "audit_logs",
  "therapist_thai_summaries"
];

export const STORE_COLLECTION_KEYS = {
  users: "users",
  child_cases: "cases",
  sessions: "sessions",
  transcripts: "transcripts",
  transcript_lines: "transcriptLines",
  audio_files: "audioFiles",
  consent_records: "consentRecords",
  processing_jobs: "processingJobs",
  extracted_features: "extractedFeatureOutputs",
  ai_screening_outputs: "aiDecisionOutputs",
  therapy_goals: "goals",
  therapist_notes: "notes",
  reports: "generatedReports",
  clinical_signoffs: "clinicalSignoffs",
  privacy_operations: "privacyOperations",
  audit_logs: "auditLogs",
  therapist_thai_summaries: "therapistThaiSummaries"
};

export const LOCAL_STORAGE_KEY = "asdProject.therapistClinician.repository.v1";

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function hasStorageShape(storage) {
  return storage && typeof storage.getItem === "function" && typeof storage.setItem === "function";
}

export function snapshotFromState(state) {
  return {
    users: state.users || [],
    child_cases: state.cases || [],
    sessions: state.sessions || [],
    transcripts: state.transcripts || {},
    transcript_lines: state.transcriptLines || {},
    audio_files: state.audioFiles || [],
    consent_records: state.consentRecords || [],
    processing_jobs: state.processingJobs || [],
    extracted_features: state.extractedFeatureOutputs || {},
    ai_screening_outputs: state.aiDecisionOutputs || {},
    therapy_goals: state.goals || [],
    therapist_notes: state.notes || [],
    reports: state.generatedReports || [],
    clinical_signoffs: state.clinicalSignoffs || [],
    privacy_operations: state.privacyOperations || [],
    audit_logs: state.auditLogs || [],
    therapist_thai_summaries: state.therapistThaiSummaries || {}
  };
}

export function stateFromSnapshot(snapshot) {
  return {
    users: snapshot.users || [],
    cases: snapshot.child_cases || [],
    sessions: snapshot.sessions || [],
    transcripts: snapshot.transcripts || {},
    transcriptLines: snapshot.transcript_lines || {},
    audioFiles: snapshot.audio_files || [],
    consentRecords: snapshot.consent_records || [],
    processingJobs: snapshot.processing_jobs || [],
    extractedFeatureOutputs: snapshot.extracted_features || {},
    aiDecisionOutputs: snapshot.ai_screening_outputs || {},
    goals: snapshot.therapy_goals || [],
    notes: snapshot.therapist_notes || [],
    generatedReports: snapshot.reports || [],
    clinicalSignoffs: snapshot.clinical_signoffs || [],
    privacyOperations: snapshot.privacy_operations || [],
    auditLogs: snapshot.audit_logs || [],
    therapistThaiSummaries: snapshot.therapist_thai_summaries || {}
  };
}

function isAdmin(user, options = {}) {
  return user?.role === "admin" && options.adminEnabled !== false;
}

function userOwns(row, user) {
  return Boolean(user?.user_id && row?.owner_user_id === user.user_id);
}

class EntityRepository {
  constructor(adapter, collectionName) {
    this.adapter = adapter;
    this.collectionName = collectionName;
  }

  list() {
    return clone(this.adapter.snapshot[this.collectionName] || []);
  }

  listForUser(user, options = {}) {
    const rows = this.list();
    if (this.collectionName === "users") {
      return isAdmin(user, options) ? rows : rows.filter(row => row.user_id === user?.user_id);
    }
    if (this.collectionName === "audit_logs") {
      return isAdmin(user, options) ? rows : [];
    }
    if (isAdmin(user, options)) return rows;
    return rows.filter(row => userOwns(row, user));
  }

  get(idField, id, user, options = {}) {
    const row = this.list().find(item => item[idField] === id);
    if (!row) return null;
    if (isAdmin(user, options) || this.collectionName === "users" || userOwns(row, user)) return clone(row);
    return null;
  }

  save(row, idField) {
    const rows = this.list();
    const index = rows.findIndex(item => item[idField] === row[idField]);
    const nextRows = index >= 0
      ? rows.map(item => (item[idField] === row[idField] ? row : item))
      : [...rows, row];
    this.adapter.replaceCollection(this.collectionName, nextRows);
    return clone(row);
  }
}

class KeyedEntityRepository {
  constructor(adapter, collectionName) {
    this.adapter = adapter;
    this.collectionName = collectionName;
  }

  entries() {
    return clone(this.adapter.snapshot[this.collectionName] || {});
  }

  list() {
    return Object.values(this.entries());
  }

  listForUser(user, options = {}) {
    const rows = this.list();
    if (isAdmin(user, options)) return rows;
    return rows.filter(row => userOwns(row, user));
  }

  getByKey(key, user, options = {}) {
    const row = this.entries()[key];
    if (!row) return null;
    if (isAdmin(user, options) || userOwns(row, user)) return clone(row);
    return null;
  }

  saveByKey(key, row) {
    const rows = this.entries();
    rows[key] = row;
    this.adapter.replaceCollection(this.collectionName, rows);
    return clone(row);
  }
}

export class ClinicalPersistenceAdapter {
  constructor({ mode, storage = null, storageKey = LOCAL_STORAGE_KEY } = {}) {
    this.mode = normalizeDataMode(mode || DATA_MODE);
    this.storage = storage;
    this.storageKey = storageKey;
    this.snapshot = {};
    this.status = "not_loaded";
    this.users = new EntityRepository(this, "users");
    this.childCases = new EntityRepository(this, "child_cases");
    this.sessions = new EntityRepository(this, "sessions");
    this.audioFiles = new EntityRepository(this, "audio_files");
    this.consentRecords = new EntityRepository(this, "consent_records");
    this.processingJobs = new EntityRepository(this, "processing_jobs");
    this.therapyGoals = new EntityRepository(this, "therapy_goals");
    this.therapistNotes = new EntityRepository(this, "therapist_notes");
    this.reports = new EntityRepository(this, "reports");
    this.clinicalSignoffs = new EntityRepository(this, "clinical_signoffs");
    this.privacyOperations = new EntityRepository(this, "privacy_operations");
    this.auditLogs = new EntityRepository(this, "audit_logs");
    this.transcripts = new KeyedEntityRepository(this, "transcripts");
    this.transcriptLines = new KeyedEntityRepository(this, "transcript_lines");
    this.extractedFeatures = new KeyedEntityRepository(this, "extracted_features");
    this.aiScreeningOutputs = new KeyedEntityRepository(this, "ai_screening_outputs");
    this.therapistThaiSummaries = new KeyedEntityRepository(this, "therapist_thai_summaries");
  }

  hydrate(seedSnapshot) {
    if (this.mode === "localStorage") {
      return this.hydrateFromLocalStorage(seedSnapshot);
    }
    this.snapshot = clone(seedSnapshot);
    if (this.mode === "database_placeholder") {
      this.status = "database_placeholder_ready";
    } else if (this.mode === "api") {
      this.status = "api_repository_configured";
    } else {
      this.status = "mock_ready";
    }
    return clone(this.snapshot);
  }

  hydrateFromLocalStorage(seedSnapshot) {
    if (!hasStorageShape(this.storage)) {
      this.snapshot = clone(seedSnapshot);
      this.status = "localStorage_unavailable_using_demo_seed";
      return clone(this.snapshot);
    }

    const raw = this.storage.getItem(this.storageKey);
    if (raw) {
      try {
        this.snapshot = { ...clone(seedSnapshot), ...JSON.parse(raw) };
        this.status = "localStorage_loaded";
        return clone(this.snapshot);
      } catch {
        this.snapshot = clone(seedSnapshot);
        this.status = "localStorage_parse_failed_using_demo_seed";
        this.persistSnapshot(this.snapshot);
        return clone(this.snapshot);
      }
    }

    this.snapshot = clone(seedSnapshot);
    this.persistSnapshot(this.snapshot);
    this.status = "localStorage_seeded";
    return clone(this.snapshot);
  }

  replaceCollection(collectionName, value) {
    if (!PERSISTED_COLLECTIONS.includes(collectionName)) {
      throw new Error(`Unknown repository collection: ${collectionName}`);
    }
    this.snapshot = { ...this.snapshot, [collectionName]: clone(value) };
    this.persistSnapshot(this.snapshot);
  }

  persistState(state) {
    this.snapshot = snapshotFromState(state);
    this.persistSnapshot(this.snapshot);
  }

  persistSnapshot(snapshot) {
    if (this.mode !== "localStorage" || !hasStorageShape(this.storage)) return;
    this.storage.setItem(this.storageKey, JSON.stringify(snapshot));
  }
}

export function createPersistenceAdapter({ mode = DATA_MODE, storage } = {}) {
  const selectedMode = normalizeDataMode(mode);
  const browserStorage = storage || (typeof window !== "undefined" ? window.localStorage : null);
  return new ClinicalPersistenceAdapter({ mode: selectedMode, storage: browserStorage });
}
