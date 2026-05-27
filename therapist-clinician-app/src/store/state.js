// Centralized reactive state store

class Store {
  constructor() {
    this.state = {
      currentUser: null,
      authError: "",
      dataMode: "mock",
      persistenceStatus: "not_loaded",
      activeView: "dashboard",
      selectedCaseId: "CASE-001",
      selectedSessionId: "SESSION-001",
      cases: [],
      sessions: [],
      audioFiles: [],
      transcripts: {}, // transcriptRecords by sessionId
      transcriptLines: {}, // transcriptLines by sessionId
      goals: [],
      notes: [],
      generatedReports: [],
      aiDecisionOutputs: {}, // aiDecisionOutputs by sessionId
      extractedFeatureOutputs: {}, // extractedFeatureOutputs by sessionId
      auditLogs: [],
      users: []
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
