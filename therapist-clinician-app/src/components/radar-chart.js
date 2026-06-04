import { store } from "../store/state.js";
import { getCaseSessions } from "../services/session-service.js";

function featureRowsForCase(caseId) {
  const sessions = getCaseSessions(caseId).sort((a, b) => a.session_date.localeCompare(b.session_date));
  const { extractedFeatureOutputs } = store.getState();
  return sessions
    .map(session => ({ session, output: extractedFeatureOutputs[session.session_id] }))
    .filter(row => row.output);
}

function featureTrendRows(caseItem) {
  const rows = featureRowsForCase(caseItem.case_id);
  const preferred = ["total_utterances", "total_words", "mlu", "ttr", "unintelligible_ratio", "echolalia_ratio"];
  return preferred.map(metric => {
    const values = rows.map(row => row.output.features[metric]).filter(value => Number.isFinite(value));
    const first = values[0] ?? null;
    const latest = values.at(-1) ?? null;
    const delta = first === null || latest === null ? null : Number((latest - first).toFixed(3));
    const lowerIsBetter = ["unintelligible_ratio", "echolalia_ratio"].includes(metric);
    const improved = delta === null ? null : lowerIsBetter ? delta < 0 : delta > 0;
    return { metric, first, latest, delta, improved };
  });
}

export function radarEntries(caseItem) {
  const rows = featureRowsForCase(caseItem.case_id);
  if (!rows.length) {
    return featureTrendRows(caseItem).map(row => ({
      metric: row.metric,
      first: 0,
      latest: 0
    }));
  }
  const first = rows[0].output.features;
  const latest = rows.at(-1).output.features;
  return ["total_utterances", "total_words", "mlu", "ttr", "unintelligible_ratio", "echolalia_ratio"].map(metric => ({
    metric,
    first: first[metric] ?? 0,
    latest: latest[metric] ?? 0
  }));
}

function normalizeRadarMetric(metric, value) {
  const ranges = {
    total_utterances: 8,
    total_words: 32,
    mlu: 6,
    ttr: 1,
    unintelligible_ratio: 1,
    echolalia_ratio: 1
  };
  return Math.max(0.08, Math.min(1, Number(value || 0) / ranges[metric]));
}

function radarPoints(entries, key, radius, cx, cy) {
  return entries
    .map((entry, index) => {
      const angle = -Math.PI / 2 + (index * Math.PI * 2) / entries.length;
      const value = normalizeRadarMetric(entry.metric, entry[key]);
      const x = cx + Math.cos(angle) * radius * value;
      const y = cy + Math.sin(angle) * radius * value;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export function renderRadarChart(entries) {
  const cx = 100;
  const cy = 100;
  const radius = 70;

  // Outer web concentric rings
  const webs = [0.25, 0.5, 0.75, 1.0];
  const ringElements = webs
    .map(scale => {
      const points = entries
        .map((_, i) => {
          const angle = -Math.PI / 2 + (i * Math.PI * 2) / entries.length;
          const x = cx + Math.cos(angle) * radius * scale;
          const y = cy + Math.sin(angle) * radius * scale;
          return `${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(" ");
      return `<polygon points="${points}" fill="none" stroke="var(--line)" stroke-width="0.8" />`;
    })
    .join("\n");

  // Axis lines
  const axisElements = entries
    .map((entry, i) => {
      const angle = -Math.PI / 2 + (i * Math.PI * 2) / entries.length;
      const x = cx + Math.cos(angle) * radius;
      const y = cy + Math.sin(angle) * radius;

      // Position text label
      const textDist = radius + 15;
      const tx = cx + Math.cos(angle) * textDist;
      const ty =
        cy +
        Math.sin(angle) * textDist +
        (angle === -Math.PI / 2 ? -2 : angle === Math.PI / 2 ? 8 : 3);
      const textAnchor = Math.cos(angle) > 0.1 ? "start" : Math.cos(angle) < -0.1 ? "end" : "middle";

      const niceLabels = {
        total_utterances: "Child Utts",
        total_words: "Total Words",
        mlu: "MLU",
        ttr: "TTR",
        unintelligible_ratio: "Unintel Ratio",
        echolalia_ratio: "Echo Ratio"
      };

      return `
      <line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="var(--line)" stroke-dasharray="1 2" />
      <text x="${tx.toFixed(1)}" y="${ty.toFixed(1)}" text-anchor="${textAnchor}" font-size="8" fill="var(--muted)" font-weight="700">
        ${niceLabels[entry.metric] || entry.metric}
      </text>
    `;
    })
    .join("\n");

  const ptsFirst = radarPoints(entries, "first", radius, cx, cy);
  const ptsLatest = radarPoints(entries, "latest", radius, cx, cy);

  return `
    <div class="panel" style="text-align: center;">
      <div class="panel-title">
        <h3>Before/After Radar</h3>
        <span>first session vs latest session comparison</span>
      </div>
      <div style="display: flex; justify-content: center; align-items: center;">
        <svg viewBox="0 0 200 210" style="width: 200px; height: 210px; overflow: visible;">
          ${ringElements}
          ${axisElements}
          <!-- First Session Polygon -->
          <polygon points="${ptsFirst}" fill="var(--medical-blue-soft)" stroke="var(--medical-blue)" stroke-width="2" opacity="0.6" />
          <!-- Latest Session Polygon -->
          <polygon points="${ptsLatest}" fill="var(--primary-soft)" stroke="var(--primary)" stroke-width="2" opacity="0.6" />
          <!-- Center dot -->
          <circle cx="${cx}" cy="${cy}" r="3" fill="var(--muted)" />
        </svg>
      </div>
      <div style="display: flex; justify-content: center; gap: 12px; margin-top: 10px; font-size: 0.8rem;">
        <span style="color: var(--medical-blue); font-weight: 700;">● First Session</span>
        <span style="color: var(--primary); font-weight: 700;">● Latest Session</span>
      </div>
    </div>
  `;
}
