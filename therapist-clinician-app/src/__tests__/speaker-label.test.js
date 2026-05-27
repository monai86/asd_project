import { describe, it, expect, beforeEach } from "vitest";
import { store } from "../store/state.js";
import { updateUtterance } from "../services/review-service.js";

describe("Speaker Correction & Auditing", () => {
  beforeEach(() => {
    store.setState({
      transcriptLines: {
        "SESSION-TEST": [
          { speaker: "CHI", text: "train", confidence: 0.8 }
        ]
      },
      auditLogs: []
    });
  });

  it("should update speaker label and log an audit trail event", () => {
    updateUtterance("SESSION-TEST", 0, "train", "MOT");
    
    const lines = store.getState().transcriptLines["SESSION-TEST"];
    expect(lines[0].speaker).toBe("MOT");

    const logs = store.getState().auditLogs;
    expect(logs.length).toBe(1);
    expect(logs[0].event_type).toBe("edit_utterance");
    expect(logs[0].message).toContain("Speaker changed from CHI to MOT");
  });
});
