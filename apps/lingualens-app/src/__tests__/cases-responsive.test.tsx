import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderAsyncPage, routerPush } from "@/__tests__/setup";
import CasesPage from "@/app/cases/page";
import { CaseList } from "@/features/cases/components/case-list";
import type { BackendCase } from "@/lib/workflow";

vi.mock("@/lib/use-runtime-settings", () => ({
  useRuntimeSettings: () => ({
    status: "success",
    mode: "backend",
    data: { auth_mode: "mock" },
  }),
}));

const cases: BackendCase[] = [
  {
    case_id: "case_alpha",
    child_code: "C-1001",
    nickname: "Alpha sample",
    age_months: 60,
    language: "Thai-English",
    consent_status: "granted",
    latest_session_status: "Draft",
    latest_report_status: "Draft",
    review_priority: "moderate",
    care_team_user_ids: ["therapist-demo"],
  },
  {
    case_id: "case_pending",
    child_code: "C-1002",
    nickname: "Pending sample",
    age_months: 58,
    language: "Thai",
    consent_status: "pending",
    latest_session_status: "Draft",
    latest_report_status: "Ready",
    review_priority: "high",
    care_team_user_ids: ["therapist-demo"],
  },
];

beforeEach(() => {
  routerPush.mockReset();
  vi.unstubAllGlobals();
});

describe("responsive Cases workspace", () => {
  it("requires deliberate case selection for the start-session intent", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/cases")) return jsonResponse(cases);
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderAsyncPage(CasesPage, {
      searchParams: Promise.resolve({ intent: "start-session" }),
    });

    expect(await screen.findByRole("heading", { name: "Choose a case to start a session" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start session" })).toBeDisabled();
    expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining("/sessions"), expect.anything());
    expect(routerPush).not.toHaveBeenCalled();
  });

  it("creates a session for only the selected consented case and opens canonical intake", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/cases") && !init?.method) return jsonResponse(cases);
      if (url.endsWith("/cases/case_alpha/sessions") && init?.method === "POST") {
        return jsonResponse({
          session_id: "session_created_001",
          case_id: "case_alpha",
          status: "Draft",
        });
      }
      throw new Error(`Unexpected request: ${init?.method ?? "GET"} ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderAsyncPage(CasesPage, {
      searchParams: Promise.resolve({ intent: "start-session" }),
    });

    fireEvent.click(await screen.findByRole("radio", { name: /Alpha sample/ }));
    expect(screen.getByRole("button", { name: "Start session for C-1001" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Start session for C-1001" }));

    await waitFor(() => {
      expect(routerPush).toHaveBeenCalledWith("/sessions/session_created_001?view=intake");
    });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/cases/case_alpha/sessions"),
      expect.objectContaining({ method: "POST" }),
    );
    const createRequest = fetchMock.mock.calls.find(([input, init]) => (
      String(input).endsWith("/cases/case_alpha/sessions") && init?.method === "POST"
    ));
    expect(JSON.parse(String(createRequest?.[1]?.body))).toMatchObject({
      notes: "Session created after deliberate case selection. Source will be selected in Intake.",
    });
    expect(screen.getByRole("radio", { name: /Pending sample/ })).toBeDisabled();
  });

  it("explains when no consented case can start a session", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/cases")) return jsonResponse([cases[1]]);
      throw new Error(`Unexpected request: ${String(input)}`);
    }));

    await renderAsyncPage(CasesPage, {
      searchParams: Promise.resolve({ intent: "start-session" }),
    });

    expect(await screen.findByRole("heading", { name: "No consented cases available" })).toBeInTheDocument();
    expect(screen.getByText(/confirm consent from the case record before starting a session/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start session" })).toBeDisabled();
  });

  it("uses a semantic compact list for the mobile Cases presentation", () => {
    render(<CaseList model={{ cases }} canFilterByClinician />);

    const mobileList = screen.getByRole("list", { name: "Cases" });
    expect(mobileList).toHaveClass("xl:hidden");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByRole("table", { name: "Cases workspace" }).closest("div.hidden")).toHaveClass("hidden", "xl:block");
  });

  it("routes every case-list session start through the deliberate selector", () => {
    render(<CaseList model={{ cases: [cases[0]] }} canFilterByClinician />);

    for (const link of screen.getAllByRole("link", { name: "Start session" })) {
      expect(link).toHaveAttribute("href", "/cases?intent=start-session");
    }
  });

  it("hides clinician filtering from ordinary therapists", () => {
    const { rerender } = render(<CaseList model={{ cases }} canFilterByClinician={false} />);
    expect(screen.queryByRole("combobox", { name: "Clinician filter" })).not.toBeInTheDocument();

    rerender(<CaseList model={{ cases }} canFilterByClinician />);
    expect(screen.getByRole("combobox", { name: "Clinician filter" })).toBeInTheDocument();
  });

  it("filters by consent and sorts the case list without losing workflow context", () => {
    render(<CaseList model={{ cases }} canFilterByClinician />);

    expect(screen.getByRole("combobox", { name: "Consent filter" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Sort cases" })).toBeInTheDocument();
    expect(screen.getAllByText("No session activity yet").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Consent follow-up").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByRole("combobox", { name: "Consent filter" }), {
      target: { value: "pending" },
    });

    const table = screen.getByRole("table", { name: "Cases workspace" });
    expect(table).toHaveTextContent("Pending sample");
    expect(table).not.toHaveTextContent("Alpha sample");
  });

  it("keeps the derived workflow stage and next action in the case row", () => {
    render(<CaseList model={{ cases: [{
      ...cases[0],
      latest_session_status: "Needs Review",
      latest_session_date: "2026-07-15",
    }] }} canFilterByClinician />);

    const table = screen.getByRole("table", { name: "Cases workspace" });
    expect(table).toHaveTextContent("Transcript review");
    expect(within(table).getByRole("link", { name: "Review session" })).toHaveAttribute("href", "/cases/case_alpha");
  });

  it("provides selected-case context in the desktop split view", () => {
    render(<CaseList model={{ cases }} canFilterByClinician />);

    const context = screen.getByRole("complementary", { name: "Selected case context" });
    expect(context).toHaveTextContent("Alpha sample");

    fireEvent.click(screen.getByRole("button", { name: "Preview Pending sample" }));
    expect(context).toHaveTextContent("Pending sample");
    expect(context).toHaveTextContent("Consent follow-up");
    expect(context).toHaveTextContent("High priority");
  });

  it("prioritizes latest activity, workflow status, and one next action over secondary analytics", () => {
    render(<CaseList model={{ cases }} canFilterByClinician />);

    const table = screen.getByRole("table", { name: "Cases workspace" });
    expect(screen.getAllByRole("columnheader", { hidden: true }).map((header) => header.textContent)).toEqual([
      "Case",
      "Latest activity",
      "Workflow status",
      "Next action",
    ]);
    expect(within(table).getAllByRole("link", { name: /Start session|Review consent|Review session|Finalize report|Continue workflow/ })).toHaveLength(cases.length);
    expect(screen.queryByRole("heading", { name: "Case overview stats" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Workflow at a glance" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Recent activity" })).not.toBeInTheDocument();
  });
});

function jsonResponse(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "content-type": "application/json" },
  });
}
