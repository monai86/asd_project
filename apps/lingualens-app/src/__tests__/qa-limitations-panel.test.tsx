import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { QaLimitationsPanel } from "@/features/sessions/transcript/qa-limitations-panel";

describe("QaLimitationsPanel", () => {
  it("separates non-overridable blockers from acknowledgeable limitations", () => {
    const acknowledge = vi.fn();
    render(
      <QaLimitationsPanel
        busy={false}
        blockers={[{
          code: "TIMESTAMP_ORDER_INVALID",
          disposition: "integrity_blocker",
          severity: "error",
          rule_version: "speech-qa-v1.7.0",
          affected_resources: ["utt-2"],
          remediation: "Correct timestamps.",
          message: "Timestamp order is invalid.",
        }]}
        limitations={[{
          code: "SHORT_SAMPLE",
          disposition: "acknowledgeable_limitation",
          severity: "warning",
          rule_version: "speech-qa-v1.7.0",
          affected_resources: [],
          remediation: "Interpret counts cautiously.",
          message: "The reviewed sample is short.",
        }]}
        acknowledgedCodes={[]}
        onAcknowledge={acknowledge}
      />,
    );

    const blocker = screen.getByTestId("qa-blocker-TIMESTAMP_ORDER_INVALID");
    expect(within(blocker).getByText("Cannot be overridden")).toBeInTheDocument();
    expect(within(blocker).queryByRole("button")).not.toBeInTheDocument();

    const limitation = screen.getByTestId("qa-limitation-SHORT_SAMPLE");
    fireEvent.change(within(limitation).getByLabelText("Reason for SHORT_SAMPLE"), {
      target: { value: "context_documented" },
    });
    fireEvent.click(within(limitation).getByRole("button", { name: "Acknowledge SHORT_SAMPLE" }));
    expect(acknowledge).toHaveBeenCalledWith("SHORT_SAMPLE", "context_documented", "");
  });

  it("shows current acknowledgment state and validator provenance", () => {
    render(
      <QaLimitationsPanel
        busy={false}
        blockers={[]}
        limitations={[{
          code: "LOW_INTELLIGIBILITY",
          disposition: "acknowledgeable_limitation",
          severity: "warning",
          rule_version: "speech-qa-v1.7.0",
          affected_resources: [],
          remediation: "Review uncertain utterances.",
          message: "Some retained wording is uncertain.",
        }]}
        acknowledgedCodes={["LOW_INTELLIGIBILITY"]}
        onAcknowledge={vi.fn()}
      />,
    );

    expect(screen.getByText("Acknowledged for this transcript version")).toBeInTheDocument();
    expect(screen.getByText("speech-qa-v1.7.0")).toBeInTheDocument();
  });
});
