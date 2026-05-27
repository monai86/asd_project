import { escapeHtml } from "@shared/utils/html.js";

export function renderUtteranceRow(line, index, sessionId) {
  const speakerOptions = ["CHI", "MOT", "FAT", "INV", "CLI", "PAR"];
  const confidence = line.confidence ?? 1;
  const isLowConfidence = confidence < 0.65;
  const hasFlags = (line.clinical_flags || []).length > 0;
  const statusClass = isLowConfidence || hasFlags ? "warning-line" : "";
  const reviewStatus = line.review_status || (line.reviewed ? "reviewed" : "needs_review");
  const timingLabel = line.timing
    ? `${line.timing.start_time?.toFixed?.(2) ?? line.timing.start_time}s-${line.timing.end_time?.toFixed?.(2) ?? line.timing.end_time}s`
    : "none";
  const flagsHtml = (line.clinical_flags || [])
    .map(flag => `<span class="status-pill status-warn" title="${escapeHtml(flag.explanation || "")}">${escapeHtml(flag.marker_type)}</span>`)
    .join(" ");

  const optionsHtml = speakerOptions
    .map(opt => `<option value="${opt}" ${line.speaker === opt ? "selected" : ""}>${opt}</option>`)
    .join("");

  return `
    <tr class="utterance-row ${statusClass}" data-line-index="${index}">
      <td style="padding: 10px; vertical-align: top;">
        <a href="#line-${line.line_number || index + 1}" id="line-${line.line_number || index + 1}">${line.line_number || index + 1}</a>
      </td>
      <td style="padding: 10px;">
        <select class="speaker-edit-select" data-session-id="${sessionId}" data-line-index="${index}" style="min-width: 80px; padding: 4px;">
          ${optionsHtml}
        </select>
      </td>
      <td style="padding: 10px; width: 100%;">
        <input type="text" class="text-edit-input" data-session-id="${sessionId}" data-line-index="${index}" value="${escapeHtml(line.text)}" style="width: 100%; border: 1px solid var(--line); border-radius: 4px; padding: 6px;" />
        <label style="display: block; margin-top: 8px; font-size: 0.8rem; color: var(--muted);">Interpretation note
          <input type="text" class="interpretation-note-input" data-session-id="${sessionId}" data-line-index="${index}" value="${escapeHtml(line.interpretation_note || "")}" style="width: 100%; border: 1px solid var(--line); border-radius: 4px; padding: 6px; margin-top: 4px;" />
        </label>
      </td>
      <td style="padding: 10px; vertical-align: top; min-width: 90px;">
        ${escapeHtml(timingLabel)}
      </td>
      <td style="padding: 10px; vertical-align: top; min-width: 150px;">
        ${flagsHtml || '<span style="color: var(--muted);">none</span>'}
      </td>
      <td style="padding: 10px; vertical-align: top; min-width: 120px;">
        <label style="display: flex; gap: 6px; align-items: center; font-size: 0.85rem;">
          <input type="checkbox" class="line-reviewed-checkbox" data-session-id="${sessionId}" data-line-index="${index}" ${line.reviewed ? "checked" : ""} />
          ${escapeHtml(reviewStatus)}
        </label>
      </td>
      <td style="padding: 10px; text-align: right;">
        <span class="confidence-badge ${isLowConfidence ? "low" : "high"}" title="Confidence score: ${confidence}">
          ${(confidence * 100).toFixed(0)}%
        </span>
      </td>
    </tr>
  `;
}
