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

  let splinePathD = "";
  let areaPathD = "";

  if (points.length > 0) {
    const firstPoint = points[0];
    splinePathD = `M ${firstPoint.x.toFixed(1)} ${firstPoint.y.toFixed(1)}`;
    
    for (let i = 1; i < points.length; i++) {
      const p1 = points[i - 1];
      const p2 = points[i];
      const cx1 = ((p1.x + p2.x) / 2).toFixed(1);
      const cy1 = p1.y.toFixed(1);
      const cx2 = cx1;
      const cy2 = p2.y.toFixed(1);
      const x2 = p2.x.toFixed(1);
      const y2 = p2.y.toFixed(1);
      splinePathD += ` C ${cx1} ${cy1}, ${cx2} ${cy2}, ${x2} ${y2}`;
    }

    if (points.length > 1) {
      const lastPoint = points[points.length - 1];
      areaPathD = splinePathD + ` L ${lastPoint.x.toFixed(1)} ${(height - padding).toFixed(1)} L ${firstPoint.x.toFixed(1)} ${(height - padding).toFixed(1)} Z`;
    }
  }

  return `
    <div class="glass-card trend-panel">
      <div class="panel-title">
        <h3>Score Trend Over Sessions</h3>
        <span>longitudinal screening tracking</span>
      </div>
      <div style="position: relative; width: 100%;">
        <svg viewBox="0 0 ${width} ${height}" style="width: 100%; height: auto; overflow: visible;">
          <defs>
            <linearGradient id="trendAreaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="var(--primary)" stop-opacity="0.3" />
              <stop offset="100%" stop-color="var(--primary)" stop-opacity="0.0" />
            </linearGradient>
          </defs>

          <!-- Grid lines -->
          <g class="grid-lines" stroke="var(--line)" stroke-width="1" stroke-dasharray="3 4">
            <line x1="${padding}" y1="${padding}" x2="${width - padding}" y2="${padding}" />
            <line x1="${padding}" y1="${height / 2}" x2="${width - padding}" y2="${height / 2}" />
            <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" />
          </g>

          <!-- Area fill path -->
          ${points.length > 1 ? `<path d="${areaPathD}" fill="url(#trendAreaGradient)" stroke="none" />` : ""}

          <!-- Trend line path -->
          ${points.length > 1 ? `<path d="${splinePathD}" fill="none" stroke="var(--primary)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />` : ""}

          <!-- Points -->
          ${points
            .map(
              p => `
            <circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="4.5" fill="#ffffff" stroke="var(--primary)" stroke-width="2.5" style="transition: r 0.15s ease, stroke-width 0.15s ease; cursor: pointer;" onmouseover="this.setAttribute('r', '6.5'); this.setAttribute('stroke-width', '3.5')" onmouseout="this.setAttribute('r', '4.5'); this.setAttribute('stroke-width', '2.5')" />
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
