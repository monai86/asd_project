// Centralized reactive state store

class Store {
  constructor() {
    this.state = {
      currentUser: null,
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
      auditLogs: []
    };
    this.listeners = [];
  }

  getState() {
    return this.state;
  }

  setState(nextState) {
    this.state = { ...this.state, ...nextState };
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
