import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ClinicalEvidenceDrawer } from "@/features/sessions/components/clinical-evidence-drawer";

describe("ClinicalEvidenceDrawer", () => {
  it("renders TalkBank score and Clinical Findings heading when open", () => {
    render(
      <ClinicalEvidenceDrawer
        isOpen={true}
        onClose={vi.fn()}
        findings={{ talkBankScore: 0.85 }}
      />
    );
    expect(screen.getByText(/Clinical Findings/i)).toBeInTheDocument();
    expect(screen.getByText("85%")).toBeInTheDocument();
  });

  it("hides aside offscreen when closed", () => {
    const { container } = render(
      <ClinicalEvidenceDrawer isOpen={false} onClose={vi.fn()} findings={{ talkBankScore: 0.85 }} />
    );
    const aside = container.querySelector("aside");
    expect(aside?.className).toContain("translate-x-full");
  });

  it("shows stale warning when findings are stale", () => {
    render(
      <ClinicalEvidenceDrawer isOpen={true} onClose={vi.fn()} findings={{ stale: true }} />
    );
    expect(screen.getByText(/stale/i)).toBeInTheDocument();
  });

  it("shows View Report button when onViewReport is provided", () => {
    const onViewReport = vi.fn();
    render(
      <ClinicalEvidenceDrawer isOpen={true} onClose={vi.fn()} onViewReport={onViewReport} />
    );
    expect(screen.getByText(/View Clinical Report/i)).toBeInTheDocument();
  });
});
