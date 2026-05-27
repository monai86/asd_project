import { escapeHtml } from "@shared/utils/html.js";

export function renderUtteranceRow(line, index, sessionId) {
  const speakerOptions = ["CHI", "MOT", "INV"];
  const isLowConfidence = line.confidence < 0.65;
  const statusClass = isLowConfidence ? "warning-line" : "";

  const optionsHtml = speakerOptions
    .map(opt => `<option value="${opt}" ${line.speaker === opt ? "selected" : ""}>${opt}</option>`)
    .join("");

  return `
    <tr class="utterance-row ${statusClass}" data-line-index="${index}">
      <td style="padding: 10px;">
        <select class="speaker-edit-select" data-session-id="${sessionId}" data-line-index="${index}" style="min-width: 80px; padding: 4px;">
          ${optionsHtml}
        </select>
      </td>
      <td style="padding: 10px; width: 100%;">
        <input type="text" class="text-edit-input" data-session-id="${sessionId}" data-line-index="${index}" value="${escapeHtml(line.text)}" style="width: 100%; border: 1px solid var(--line); border-radius: 4px; padding: 6px;" />
      </td>
      <td style="padding: 10px; text-align: right;">
        <span class="confidence-badge ${isLowConfidence ? "low" : "high"}" title="Confidence score: ${line.confidence}">
          ${(line.confidence * 100).toFixed(0)}%
        </span>
      </td>
    </tr>
  `;
}
