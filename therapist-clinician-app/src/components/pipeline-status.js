export function renderPipelineStatus(processingStatus) {
  const steps = [
    { key: "uploaded", label: "Upload" },
    { key: "processing_submitted", label: "Queued" },
    { key: "processing", label: "Audio-to-CHAT" },
    { key: "transcript_ready", label: "Review" },
    { key: "completed", label: "Report" }
  ];

  let activeIndex = -1;
  if (processingStatus === "uploaded") activeIndex = 0;
  else if (processingStatus === "processing_submitted") activeIndex = 1;
  else if (processingStatus === "transcribing" || processingStatus === "processing") activeIndex = 2;
  else if (processingStatus === "transcript_ready" || processingStatus === "awaiting_review") activeIndex = 3;
  else if (processingStatus === "completed" || processingStatus === "therapist_reviewed" || processingStatus === "reviewed") activeIndex = 4;

  const stepElements = steps.map((s, idx) => {
    let stateClass = "pending";
    if (idx < activeIndex) stateClass = "completed";
    else if (idx === activeIndex) stateClass = "active";

    const indicator = stateClass === "completed" ? "✓" : idx + 1;

    return `
      <div class="stepper-step ${stateClass}">
        <div class="step-indicator">${indicator}</div>
        <div class="step-label">${s.label}</div>
      </div>
    `;
  }).join('<div class="stepper-connector"></div>');

  return `
    <div class="pipeline-stepper-container" style="margin-bottom: 20px; padding: 12px; background: var(--shell); border-radius: var(--radius); border: 1px solid var(--line);">
      <h4 style="margin-bottom: 8px;">Pipeline Status: <span class="status-pill status-good">${processingStatus.replace("_", " ")}</span></h4>
      <div class="pipeline-stepper" style="display: flex; align-items: center; justify-content: space-between;">
        ${stepElements}
      </div>
    </div>
  `;
}
