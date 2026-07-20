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
    expect(screen.getByText("C-1024")).toBeInTheDocument();
    expect(screen.getByText("Consent granted")).toBeInTheDocument();
    expect(screen.getByText("Backend mode")).toBeInTheDocument();
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
    expect(screen.getByText("Unavailable mode")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Transcript" })).toHaveAttribute(
      "href",
      "/cases?intent=start-session",
    );
  });
});
