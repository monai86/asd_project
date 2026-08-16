import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SessionContextHeader } from "@/features/sessions/components/session-context-header";

describe("SessionContextHeader", () => {
  it("shows persisted clinical context, explicit data mode, and canonical Session views", () => {
    render(
      <SessionContextHeader
        title="Session Intake"
        description="Prepare the session for therapist review."
        context={{
          sessionId: "session-1",
          caseId: "case-1024",
          caseLabel: "C-1024",
          sourceLabel: "Uploaded audio",
          consentStatus: "granted",
          workflowStatus: "Draft",
          dataMode: "backend",
          activeView: "intake",
        }}
      />,
    );

    expect(screen.getByRole("region", { name: "Session context" })).toBeInTheDocument();
    expect(screen.getAllByText("C-1024").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Consent granted")).toBeInTheDocument();
    expect(screen.getByText("Connected")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Breadcrumb" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Cases" })).toHaveAttribute("href", "/cases");
    expect(screen.getByRole("link", { name: "C-1024" })).toHaveAttribute("href", "/cases/case-1024");
    expect(screen.getByRole("link", { name: "Intake" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Transcript" })).toHaveAttribute(
      "href",
      "/sessions/session-1?view=transcript",
    );
    expect(screen.getByRole("link", { name: "Findings" })).toHaveAttribute(
      "href",
      "/sessions/session-1?view=findings",
    );
    expect(screen.getByRole("link", { name: "Report" })).toHaveAttribute(
      "href",
      "/sessions/session-1?view=report",
    );
  });

  it("renders unavailable instead of fabricating missing context", () => {
    render(
      <SessionContextHeader
        title="Session Intake"
        description="Prepare the session for therapist review."
        context={{ activeView: "intake", dataMode: "unavailable" }}
      />,
    );

    expect(screen.getAllByText("Unavailable").length).toBeGreaterThanOrEqual(4);
    expect(screen.getByText("Offline")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Transcript" })).toHaveAttribute(
      "href",
      "/cases?intent=start-session",
    );
  });

  it("compresses transcript context into a workbench header without the page-level eyebrow", () => {
    render(
      <SessionContextHeader
        density="compact"
        title="Review Transcript"
        description="Confirm speaker labels before downstream review."
        context={{
          sessionId: "session-compact",
          caseId: "case-compact",
          caseLabel: "Case C-18",
          sourceLabel: "Uploaded audio",
          workflowStatus: "Needs review",
          dataMode: "backend",
          activeView: "transcript",
        }}
      />,
    );

    const context = screen.getByRole("region", { name: "Session context" });
    expect(context).toHaveAttribute("data-density", "compact");
    expect(screen.getByRole("heading", { level: 1, name: "Review Transcript" })).toBeInTheDocument();
    expect(screen.queryByText("Clinical decision-support prototype")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Transcript" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Case C-18" })).toHaveAttribute("href", "/cases/case-compact");
  });
});
