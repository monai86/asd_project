export function renderGaugeChart(score) {
  const scoreNum = Number(score || 0.0);
  let label = "Low Concern";
  let colorClass = "status-good";

  if (scoreNum >= 0.67) {
    label = "Moderate Concern";
    colorClass = "status-bad";
  } else if (scoreNum >= 0.4) {
    label = "Watchful Review";
    colorClass = "status-warn";
  }

  return `
    <div class="panel score-card">
      <div class="panel-title">
        <h3>Latest Screening Support Score</h3>
        <span>value between 0.12 and 0.90</span>
      </div>
      <div class="gauge" style="--score: ${scoreNum}">
        <div class="gauge-core">
          <strong class="${colorClass}">${scoreNum.toFixed(2)}</strong>
          <span>${label}</span>
        </div>
      </div>
      <p class="score-range" style="margin-top: 10px; font-size: 0.8rem; color: var(--muted);">
        0.12 - 0.39 Low · 0.40 - 0.66 Watchful · 0.67+ Moderate
      </p>
    </div>
  `;
}
