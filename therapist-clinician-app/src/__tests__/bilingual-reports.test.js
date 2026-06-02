import { describe, it, expect, beforeEach } from "vitest";
import { buildProgressReportMarkdown } from "../services/report-service.js";
import { store } from "../store/state.js";
import { bindProgressReports } from "../views/progress-view.js";

describe("Bilingual Progress Reports & Therapist Overrides", () => {
  beforeEach(() => {
    // Reset store state
    store.setState({
      selectedCaseId: "CASE-001",
      therapistThaiSummaries: {},
      cases: [{ case_id: "CASE-001", anonymized_child_code: "CHI-A01" }],
      sessions: [],
      generatedReports: []
    });

    // Mock document and DOM elements for Node environment
    global.document = {
      getElementById: (id) => {
        if (id === "thai-summary-textarea") {
          return mockTextarea;
        }
        return mockBtn;
      }
    };
  });

  const mockTextarea = {
    value: "",
    addEventListener: (event, handler) => {
      mockTextarea.triggerInput = (val) => {
        mockTextarea.value = val;
        handler({ target: { value: val } });
      };
    }
  };

  const mockBtn = {
    getAttribute: () => "CASE-001",
    addEventListener: () => {}
  };

  it("should format report with custom therapist Thai summary and disclaimer", () => {
    const caseItem = { case_id: "CASE-001", anonymized_child_code: "CHI-A01" };
    const sessions = [
      { session_id: "SESSION-001", session_date: "2026-05-01", session_type: "toyplay" },
      { session_id: "SESSION-002", session_date: "2026-05-10", session_type: "toyplay" }
    ];
    const featuresMap = {
      "SESSION-001": { features: { mlu: 1.5, ttr: 0.3, echolalia_ratio: 0.2 } },
      "SESSION-002": { features: { mlu: 2.2, ttr: 0.45, echolalia_ratio: 0.05 } }
    };
    const aiOutputs = {};

    const customSummary = "ผู้ป่วยให้ความร่วมมือดีมากในการเล่น มีการตอบสนองที่เหมาะสม";
    const reportMd = buildProgressReportMarkdown(
      caseItem,
      sessions,
      featuresMap,
      aiOutputs,
      {},
      customSummary
    );

    expect(reportMd).toContain("## บทสรุปทางคลินิกภาษาไทย (Safe Thai Summary)");
    expect(reportMd).toContain("ระบบสนับสนุนการตัดสินใจทางคลินิกจำลองในขั้นวิจัย");
    expect(reportMd).toContain("ไม่ใช่เครื่องมือทางการแพทย์");
    expect(reportMd).toContain(customSummary);
  });

  it("should auto-generate Safe Thai Summary using fallback rule template when custom summary is empty", () => {
    const caseItem = { case_id: "CASE-001", anonymized_child_code: "CHI-A01" };
    const sessions = [
      { session_id: "SESSION-001", session_date: "2026-05-01", session_type: "toyplay" },
      { session_id: "SESSION-002", session_date: "2026-05-10", session_type: "toyplay" }
    ];
    const featuresMap = {
      "SESSION-001": { features: { mlu: 1.0, ttr: 0.3, echolalia_ratio: 0.2 } },
      "SESSION-002": { features: { mlu: 2.0, ttr: 0.45, echolalia_ratio: 0.05 } }
    };
    const aiOutputs = {};

    const reportMd = buildProgressReportMarkdown(
      caseItem,
      sessions,
      featuresMap,
      aiOutputs,
      {},
      ""
    );

    expect(reportMd).toContain("## บทสรุปทางคลินิกภาษาไทย (Safe Thai Summary)");
    expect(reportMd).toContain("มีความก้าวหน้าขึ้นในการเพิ่มความยาวประโยคเฉลี่ย (MLU)");
    expect(reportMd).toContain("มีความหลากคำและคลังคำศัพท์ที่กว้างขวางมากขึ้น");
    expect(reportMd).toContain("มีอัตราการพูดซ้ำเลียนแบบ (Echolalia) ลดลงอย่างเห็นได้ชัด");
  });

  it("should capture textarea changes and update store state", () => {
    bindProgressReports(() => {});

    mockTextarea.triggerInput("แก้ไขโดยนักบำบัด");

    const state = store.getState();
    expect(state.therapistThaiSummaries["CASE-001"]).toBe("แก้ไขโดยนักบำบัด");
  });
});
