export function renderTrendChart(scores) {
  if (!scores || !scores.length) {
    return `
      <div class="glass-card trend-panel" style="display: flex; align-items: center; justify-content: center;">
        <p class="empty-state">No trend scores available.</p>
      </div>
    `;
  }

  // Draw SVG chart inline
  const width = 400;
  const height = 150;
  const padding = 20;

  const points = scores.map((score, i) => {
    const x = padding + (i * (width - 2 * padding)) / Math.max(scores.length - 1, 1);
    // Y runs from bottom (height - padding) to top (padding)
    // Map score range 0.0 - 1.0 to Y coordinates
    const y = height - padding - score * (height - 2 * padding);
    return { x, y, score };
  });

  const pathD = points.reduce((acc, p, i) => {
    return acc + `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)} `;
  }, "");

  return `
    <div class="glass-card trend-panel">
      <div class="panel-title">
        <h3>Score Trend Over Sessions</h3>
        <span>longitudinal screening tracking</span>
      </div>
      <div style="position: relative; width: 100%;">
        <svg viewBox="0 0 ${width} ${height}" style="width: 100%; height: auto; overflow: visible;">
          <!-- Grid lines -->
          <g class="grid-lines" stroke="var(--line)" stroke-width="1" stroke-dasharray="3 4">
            <line x1="${padding}" y1="${padding}" x2="${width - padding}" y2="${padding}" />
            <line x1="${padding}" y1="${height / 2}" x2="${width - padding}" y2="${height / 2}" />
            <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" />
          </g>

          <!-- Trend line path -->
          ${points.length > 1 ? `<path d="${pathD}" fill="none" stroke="var(--primary)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />` : ""}

          <!-- Points -->
          ${points
            .map(
              p => `
            <circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="4" fill="#ffffff" stroke="var(--primary)" stroke-width="2" />
            <text x="${p.x.toFixed(1)}" y="${(p.y - 8).toFixed(1)}" text-anchor="middle" font-size="9" fill="var(--muted)" font-weight="700" font-family="Outfit, sans-serif">
              ${p.score.toFixed(2)}
            </text>
          `
            )
            .join("")}
        </svg>
      </div>
    </div>
  `;
}
