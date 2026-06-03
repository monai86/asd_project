export function renderGaugeChart(score) {
  const scoreNum = Number(score || 0.0);
  let label = "Low Concern";
  let colorClass = "status-good";
  let strokeColor = "var(--success)";

  if (scoreNum >= 0.67) {
    label = "Moderate Concern";
    colorClass = "status-bad";
    strokeColor = "var(--destructive)";
  } else if (scoreNum >= 0.4) {
    label = "Watchful Review";
    colorClass = "status-warn";
    strokeColor = "var(--warning)";
  }

  const clampedScore = Math.min(Math.max(scoreNum, 0), 1);
  const dashOffset = (205 * (1 - clampedScore)).toFixed(1);

  return `
    <div class="glass-card score-card">
      <div class="panel-title">
        <h3>Latest Screening Support Score</h3>
        <span>value between 0.12 and 0.90</span>
      </div>
      <div class="gauge-svg-container" style="position: relative; width: min(230px, 100%); aspect-ratio: 1.7 / 1; margin: 20px auto 6px; overflow: hidden;">
        <svg viewBox="0 0 200 90" style="width: 100%; height: auto; display: block; overflow: visible;">
          <!-- Background track -->
          <path d="M 35 85 A 65 65 0 0 1 165 85" fill="none" stroke="var(--line-dark)" stroke-width="12" stroke-linecap="round" />
          <!-- Active fill -->
          <path d="M 35 85 A 65 65 0 0 1 165 85" fill="none" stroke="${strokeColor}" stroke-width="12" stroke-linecap="round" stroke-dasharray="205" stroke-dashoffset="${dashOffset}" style="transition: stroke-dashoffset 0.6s cubic-bezier(0.4, 0, 0.2, 1), stroke 0.6s ease;" />
        </svg>
        <div class="gauge-core">
          <strong class="${colorClass}">${scoreNum.toFixed(2)}</strong>
          <span>${label}</span>
        </div>
      </div>
      <p class="score-range" style="margin-top: 10px; font-size: 0.8rem; color: var(--muted);">
        0.12 - 0.39 Low · 0.40 - 0.66 Watchful · 0.67+ Moderate
      </p>
      <p style="margin-top: 8px; font-size: 0.78rem; color: var(--muted);">
        Prototype support: rule-based/mock screening support, not a validated medical model.
      </p>
    </div>
  `;
}
