// Centralized reactive state store

class Store {
  constructor() {
    this.state = {
      currentUser: null,
      authError: "",
      authStatus: "signed_out",
      authSession: null,
      dataMode: "mock",
      persistenceStatus: "not_loaded",
      activeView: "dashboard",
      selectedCaseId: "CASE-001",
      selectedSessionId: "SESSION-001",
      isEditingTranscript: false,
      cases: [],
      sessions: [],
      audioFiles: [],
      consentRecords: [],
      processingJobs: [],
      transcripts: {}, // transcriptRecords by sessionId
      transcriptLines: {}, // transcriptLines by sessionId
      goals: [],
      notes: [],
      generatedReports: [],
      clinicalSignoffs: [],
      privacyOperations: [],
      aiDecisionOutputs: {}, // aiDecisionOutputs by sessionId
      extractedFeatureOutputs: {}, // extractedFeatureOutputs by sessionId
      transcriptQaResults: {}, // transient backend/local QA result state by sessionId
      referenceComparisons: {}, // transient reference comparison view state by sessionId
      developmentalNorms: {}, // developmentalNorms map
      audioUrls: {}, // session_id to Blob URL or filepath
      sessionVocabs: {}, // session_id to vocab array
      auditLogs: [],
      users: [],
      therapistThaiSummaries: {}
    };
    this.listeners = [];
    this.persistenceAdapter = null;
  }

  getState() {
    return this.state;
  }

  configurePersistence(adapter) {
    this.persistenceAdapter = adapter;
    this.setState(
      {
        dataMode: adapter.mode,
        persistenceStatus: adapter.status
      },
      { persist: false }
    );
  }

  setState(nextState, options = {}) {
    this.state = { ...this.state, ...nextState };
    if (options.persist !== false && this.persistenceAdapter) {
      this.persistenceAdapter.persistState(this.state);
    }
    this.notify();
  }

  subscribe(listener) {
    this.listeners.push(listener);
    // Return unsubscribe function
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  notify() {
    this.listeners.forEach(listener => listener(this.state));
  }
}

export const store = new Store();
export default store;
