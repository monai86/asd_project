import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PipelineProgressBar } from "@/components/pipeline-progress-bar";

describe("PipelineProgressBar component stage indexing and rendering", () => {
  it("renders with correct stage mapping based on status input", () => {
    // Stage 1: Awaiting Consent
    const { rerender } = render(<PipelineProgressBar currentStatus="awaiting_consent" />);
    expect(screen.getByText("Stage 1 of 8: Consent")).toBeInTheDocument();

    rerender(<PipelineProgressBar currentStatus="Awaiting Consent" />);
    expect(screen.getByText("Stage 1 of 8: Consent")).toBeInTheDocument();

    // Stage 2: Ready for Audio
    rerender(<PipelineProgressBar currentStatus="ready_for_audio" />);
    expect(screen.getByText("Stage 2 of 8: Ready")).toBeInTheDocument();

    rerender(<PipelineProgressBar currentStatus="Ready for Audio" />);
    expect(screen.getByText("Stage 2 of 8: Ready")).toBeInTheDocument();

    // Stage 3: Upload
    rerender(<PipelineProgressBar currentStatus="uploading" />);
    expect(screen.getByText("Stage 3 of 8: Upload")).toBeInTheDocument();

    rerender(<PipelineProgressBar currentStatus="Recording" />);
    expect(screen.getByText("Stage 3 of 8: Upload")).toBeInTheDocument();

    // Stage 4: ASR
    rerender(<PipelineProgressBar currentStatus="transcribing" />);
    expect(screen.getByText("Stage 4 of 8: ASR")).toBeInTheDocument();

    rerender(<PipelineProgressBar currentStatus="Transcribing" />);
    expect(screen.getByText("Stage 4 of 8: ASR")).toBeInTheDocument();

    // Stage 5: CHA
    rerender(<PipelineProgressBar currentStatus="cha_generating" />);
    expect(screen.getByText("Stage 5 of 8: CHA")).toBeInTheDocument();

    rerender(<PipelineProgressBar currentStatus="CHA Generating" />);
    expect(screen.getByText("Stage 5 of 8: CHA")).toBeInTheDocument();

    // Stage 6: Review
    rerender(<PipelineProgressBar currentStatus="review_required" />);
    expect(screen.getByText("Stage 6 of 8: Review")).toBeInTheDocument();

    rerender(<PipelineProgressBar currentStatus="Needs Review" />);
    expect(screen.getByText("Stage 6 of 8: Review")).toBeInTheDocument();

    rerender(<PipelineProgressBar currentStatus="in_review" />);
    expect(screen.getByText("Stage 6 of 8: Review")).toBeInTheDocument();

    // Stage 7: Evidence review
    rerender(<PipelineProgressBar currentStatus="ml_pending" />);
    expect(screen.getByText("Stage 7 of 8: Evidence review")).toBeInTheDocument();

    rerender(<PipelineProgressBar currentStatus="attested" />);
    expect(screen.getByText("Stage 7 of 8: Evidence review")).toBeInTheDocument();

    // Stage 8: Report
    rerender(<PipelineProgressBar currentStatus="report_ready" />);
    expect(screen.getByText("Stage 8 of 8: Report")).toBeInTheDocument();

    rerender(<PipelineProgressBar currentStatus="Signed Off" />);
    expect(screen.getByText("Stage 8 of 8: Report")).toBeInTheDocument();
  });

  it("checks completed and active step visual representations", () => {
    // When currentStatus is transcribing (Stage 4, activeIndex = 3)
    // Completed stages should be Consent (1), Ready (2), Upload (3) -> they should show Check icon
    // Active stage is ASR (4) -> should render as text "4" (idx + 1)
    // Future stages are CHA (5), Review (6), Evidence review (7), Report (8) -> should render as text "5", "6", "7", "8"
    const { container } = render(<PipelineProgressBar currentStatus="transcribing" />);

    // Active stage header text
    expect(screen.getByText("Stage 4 of 8: ASR")).toBeInTheDocument();

    // Verify progress line width is around 42.8% (3 / 7 * 100)
    const activeLine = container.querySelector('div[style*="width"]');
    expect(activeLine).toHaveStyle({ width: "42.857142857142854%" });

    // Completed steps should have a Check icon (we expect 3 check icons in the nodes, since active index is 3)
    const svgElements = container.querySelectorAll("svg");
    expect(svgElements.length).toBe(3); // Stage 1, 2, 3

    // Let's verify labels
    expect(screen.getByText("Consent")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText("Upload")).toBeInTheDocument();
    expect(screen.getByText("ASR")).toBeInTheDocument();
  });

  it("renders only the stages that apply to the chosen source path", () => {
    // Paste never uploads audio or runs ASR, so Upload/ASR/CHA stages are omitted.
    const { rerender } = render(<PipelineProgressBar currentStatus="ready_for_audio" path="paste" />);
    expect(screen.getByText("Stage 2 of 5: Ready")).toBeInTheDocument();
    expect(screen.queryByText("Upload")).not.toBeInTheDocument();
    expect(screen.queryByText("ASR")).not.toBeInTheDocument();
    expect(screen.queryByText("CHA")).not.toBeInTheDocument();
    expect(screen.getByText("Review")).toBeInTheDocument();

    // Recording keeps Upload and ASR but never generates CHA from scratch.
    rerender(<PipelineProgressBar currentStatus="transcribing" path="recording" />);
    expect(screen.getByText("Stage 4 of 7: ASR")).toBeInTheDocument();
    expect(screen.getByText("Upload")).toBeInTheDocument();
    expect(screen.queryByText("CHA")).not.toBeInTheDocument();

    // Audio upload keeps Upload but ASR stays a separate experimental step.
    rerender(<PipelineProgressBar currentStatus="ready_for_audio" path="audio" />);
    expect(screen.getByText("Stage 2 of 6: Ready")).toBeInTheDocument();
    expect(screen.getByText("Upload")).toBeInTheDocument();
    expect(screen.queryByText("ASR")).not.toBeInTheDocument();
  });

  it("highlights the nearest applicable stage when a status is absent from the path", () => {
    // "transcribing" never happens on the paste path; the bar settles on Ready.
    render(<PipelineProgressBar currentStatus="transcribing" path="paste" />);
    expect(screen.getByText("Stage 2 of 5: Ready")).toBeInTheDocument();
  });

  it("handles null, undefined, empty, or unrecognized statuses gracefully", () => {
    // Unrecognized or empty status should default to Stage 1 (Consent)
    const { rerender } = render(<PipelineProgressBar currentStatus="" />);
    expect(screen.getByText("Stage 1 of 8: Consent")).toBeInTheDocument();

    rerender(<PipelineProgressBar currentStatus={null as any} />);
    expect(screen.getByText("Stage 1 of 8: Consent")).toBeInTheDocument();

    rerender(<PipelineProgressBar currentStatus={undefined as any} />);
    expect(screen.getByText("Stage 1 of 8: Consent")).toBeInTheDocument();

    rerender(<PipelineProgressBar currentStatus="some_random_status" />);
    expect(screen.getByText("Stage 1 of 8: Consent")).toBeInTheDocument();
  });
});
