import { escapeHtml } from "@shared/utils/html.js";

export function renderUtteranceRow(line, index, sessionId) {
  const speakerOptions = ["CHI", "MOT", "FAT", "INV", "CLI", "PAR"];
  const confidence = line.confidence ?? 1;
  const isLowConfidence = confidence < 0.65;
  const hasFlags = (line.clinical_flags || []).length > 0;
  const statusClass = isLowConfidence || hasFlags ? "warning-line" : "";
  const reviewStatus = line.review_status || (line.reviewed ? "reviewed" : "needs_review");
  const hasTiming = line.timing && line.timing.start_time !== undefined;
  
  const optionsHtml = speakerOptions
    .map(opt => `<option value="${opt}" ${line.speaker === opt ? "selected" : ""}>${opt}</option>`)
    .join("");

  const flagsHtml = (line.clinical_flags || [])
    .map(flag => `
      <span class="status-pill status-warn" style="font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; display: inline-flex; align-items: center; gap: 2px;" title="${escapeHtml(flag.explanation || "")}">
        ⚠ ${escapeHtml(flag.marker_type.replace('_marker', '').replace('_', ' '))}
      </span>
    `)
    .join(" ");

  return `
    <tr class="utterance-row talkbank-row ${statusClass}" data-line-index="${index}" style="border-bottom: 1px solid var(--line); transition: background 0.15s ease;">
      <!-- Boxed Line Number Column -->
      <td style="padding: 6px 8px; vertical-align: top; width: 45px; user-select: none;">
        <div style="border: 1px solid var(--line); background: rgba(15, 23, 42, 0.3); border-radius: 4px; font-family: monospace; font-size: 0.75rem; color: var(--muted); text-align: center; width: 32px; padding: 2px 0;">
          ${line.line_number || index + 1}
        </div>
      </td>
      
      <!-- Monospace Speaker Select Column -->
      <td style="padding: 6px 8px; vertical-align: top; width: 75px;">
        <span style="font-family: monospace; font-size: 0.85rem; font-weight: bold; color: var(--ink); display: inline-flex; align-items: center;">
          <select class="speaker-edit-select" data-session-id="${sessionId}" data-line-index="${index}" 
                  style="font-family: monospace; font-size: 0.85rem; font-weight: bold; border: 1px solid transparent; background: transparent; padding: 2px 4px; cursor: pointer; outline: none; -webkit-appearance: none; -moz-appearance: none; appearance: none; color: inherit; margin: 0; text-align: right; width: 36px;">
            ${optionsHtml}
          </select>:
        </span>
      </td>
      
      <!-- Transparent monospaced text inputs -->
      <td style="padding: 6px 8px; vertical-align: top; width: 60%;">
        <div style="display: flex; flex-direction: column; gap: 4px; width: 100%;">
          <input type="text" class="text-edit-input" data-session-id="${sessionId}" data-line-index="${index}" value="${escapeHtml(line.text)}" 
                 style="width: 100%; font-family: monospace; font-size: 0.85rem; border: 1px solid transparent; background: transparent; padding: 3px 6px; border-radius: 4px; outline: none; transition: all 0.15s ease;" />
          
          <div class="interpretation-note-container" style="width: 100%; display: ${line.interpretation_note ? 'block' : 'none'};">
            <input type="text" class="interpretation-note-input" data-session-id="${sessionId}" data-line-index="${index}" value="${escapeHtml(line.interpretation_note || "")}" placeholder="Add clinical interpretation..."
                   style="width: 100%; font-size: 0.75rem; color: var(--muted); border: 1px solid transparent; background: transparent; padding: 2px 4px; border-radius: 4px; outline: none;" />
          </div>
        </div>
      </td>
      
      <!-- Timing Play Button, Badges, and Review Checkbox -->
      <td style="padding: 6px 8px; vertical-align: top; text-align: right; white-space: nowrap; font-size: 0.8rem; display: flex; align-items: center; justify-content: flex-end; gap: 8px; flex-wrap: wrap;">
        <!-- Timing Button -->
        ${hasTiming ? `
          <button type="button" class="play-segment-btn" data-start="${line.timing.start_time}" data-end="${line.timing.end_time}" 
                  style="display: inline-flex; align-items: center; gap: 4px; padding: 2px 6px; border-radius: 4px; border: 1px solid var(--line); background: var(--panel); font-size: 0.75rem; font-weight: 700; cursor: pointer; color: var(--ink);">
            ▶ ${line.timing.start_time.toFixed(1)}s
          </button>
        ` : ''}
        
        <!-- Flags -->
        ${flagsHtml}
        
        <!-- Confidence score -->
        <span class="confidence-badge ${isLowConfidence ? "low" : "high"}" title="Confidence score: ${confidence}" 
              style="font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; background: ${isLowConfidence ? 'var(--destructive-soft)' : 'var(--primary-soft)'}; color: ${isLowConfidence ? 'var(--destructive)' : 'var(--primary)'}; border: 1px solid ${isLowConfidence ? 'rgba(239, 68, 68, 0.2)' : 'rgba(20, 184, 166, 0.2)'};">
          ${(confidence * 100).toFixed(0)}%
        </span>
        
        <!-- Reviewed checkbox -->
        <label style="display: inline-flex; align-items: center; gap: 4px; font-size: 0.75rem; cursor: pointer; user-select: none;" title="Reviewed status">
          <input type="checkbox" class="line-reviewed-checkbox" data-session-id="${sessionId}" data-line-index="${index}" ${line.reviewed ? "checked" : ""} style="cursor: pointer;" />
          <span style="color: var(--muted); font-size: 0.7rem;">${reviewStatus === 'reviewed' ? '✓' : '?'}</span>
        </label>
      </td>
    </tr>
  `;
}
