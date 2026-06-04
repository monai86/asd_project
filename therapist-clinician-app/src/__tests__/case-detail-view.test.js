import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { bindCaseDetail, renderCaseDetail } from "../views/case-detail-view.js";
import { store } from "../store/state.js";

function mockButton(attrs = {}) {
  return {
    listener: null,
    getAttribute(name) {
      return attrs[name] || null;
    },
    addEventListener(event, listener) {
      if (event === "click") this.listener = listener;
    },
    click() {
      this.listener?.();
    }
  };
}

describe("case detail tabs", () => {
  beforeEach(() => {
    store.persistenceAdapter = null;
    store.setState({
      currentUser: { user_id: "therapist_a", role: "therapist", name: "Therapist A" },
      selectedCaseId: "CASE-001",
      caseDetailTab: "overview",
      cases: [{
        case_id: "CASE-001",
        owner_user_id: "therapist_a",
        display_label: "Daniel",
        anonymized_child_code: "CHI-D",
        age_months: 48,
        sex: "male",
        notes: ""
      }],
      sessions: [{
        session_id: "SESSION-001",
        case_id: "CASE-001",
        owner_user_id: "therapist_a",
        session_date: "2026-06-04",
        session_type: "therapy_session",
        therapist_review_status: "awaiting_review"
      }]
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("re-renders case detail when switching local tabs", () => {
    renderCaseDetail();
    const sessionsTab = mockButton({ "data-tab": "sessions" });
    vi.stubGlobal("document", {
      querySelectorAll(selector) {
        if (selector === ".case-tab-btn") return [sessionsTab];
        return [];
      }
    });
    const navigate = vi.fn();

    bindCaseDetail(navigate);
    sessionsTab.click();

    expect(store.getState().caseDetailTab).toBe("sessions");
    expect(navigate).toHaveBeenCalledWith("case_detail");
  });

  it("routes notes tab through the transcript workspace notes area", () => {
    store.setState({ caseDetailTab: "notes" });
    renderCaseDetail();
    const redirectBtn = mockButton({ "data-target-tab": "notes" });
    vi.stubGlobal("document", {
      querySelectorAll(selector) {
        if (selector === ".redirect-tab-btn") return [redirectBtn];
        return [];
      }
    });
    const navigate = vi.fn();

    bindCaseDetail(navigate);
    redirectBtn.click();

    expect(navigate).toHaveBeenCalledWith("transcript");
  });
});
