import { describe, it, expect } from "vitest";
import { exportCHAT, exportJSON } from "@shared/services/export-service.js";

describe("Transcript Exporters", () => {
  const caseItem = { case_id: "CASE-001", anonymized_child_code: "CHI-A01", age_months: 48, sex: "male" };
  const session = { session_id: "SESSION-001", session_date: "2026-05-20", session_type: "free_play", notes: "test" };
  const lines = [
    { speaker: "CHI", text: "car ." },
    { speaker: "MOT", text: "yes ." }
  ];

  it("should generate a valid CHAT-like header and lines format", () => {
    const chat = exportCHAT(session, caseItem, lines);
    expect(chat).toContain("@Begin");
    expect(chat).toContain("@ID:\tteng|Mock|CHI|4;00.00|male|||Target_Child|||");
    expect(chat).toContain("*CHI:\tcar .");
    expect(chat).toContain("@End");
  });

  it("should generate a structured JSON dataset including case and sessions info", () => {
    const json = exportJSON(session, caseItem, lines, { mlu: 2.5 }, { score: 0.6 });
    expect(json.case.anonymized_child_code).toBe("CHI-A01");
    expect(json.session.session_id).toBe("SESSION-001");
    expect(json.transcript.length).toBe(2);
    expect(json.export_metadata.disclaimer).toBeDefined();
  });
});
