const FEATURE_OPTIONS = [
  "age_months",
  "total_utterances",
  "mlu",
  "mluw",
  "ttr",
  "total_words",
  "unintelligible_count",
  "unintelligible_ratio",
  "zero_vocalization_count",
  "nonverbal_vocalization_count",
  "question_ratio",
  "echolalia_count",
  "echolalia_ratio",
];

const FEATURE_DOCS = {
  age_months: {
    title: "Age (months)",
    group: "Demographics",
    desc: "อายุของเด็กในหน่วยเดือน แปลงจาก CHAT age format เช่น 5;03.10",
    clinical: "ใช้เป็น control variable เพราะภาษาเด็กเปลี่ยนเร็วมากช่วง 2-5 ปี",
    direction: "neutral",
  },
  total_utterances: {
    title: "Total utterances",
    group: "Productivity",
    desc: "จำนวนบรรทัด *CHI: ที่เด็กพูดทั้งหมด",
    clinical: "ช่วยดูความถี่การสื่อสารและ engagement ในแต่ละ session",
    direction: "สูง = ดี",
  },
  mlu: {
    title: "MLU (morphemes)",
    group: "Complexity",
    desc: "Mean Length of Utterance, จำนวน morphemes เฉลี่ยต่อ utterance",
    clinical: "ตัวชี้วัดพัฒนาการโครงสร้างภาษาที่ใช้กันมากในงาน child language",
    direction: "สูง = ดี",
  },
  mluw: {
    title: "MLU (words)",
    group: "Complexity",
    desc: "ความยาว utterance เฉลี่ยเมื่อนับเป็นคำ",
    clinical: "เหมาะกับ workflow ที่ยังไม่ได้ parse morphology ละเอียด",
    direction: "สูง = ดี",
  },
  ttr: {
    title: "TTR (Type-Token Ratio)",
    group: "Lexical diversity",
    desc: "unique words / total words เพื่อดูความหลากหลายของคำ",
    clinical: "ค่าอาจสะท้อนการใช้คำซ้ำและ lexical diversity แต่ไวต่อความยาว transcript",
    direction: "สูง = ดี",
  },
  total_words: {
    title: "Total words",
    group: "Productivity",
    desc: "จำนวนคำทั้งหมดที่เด็กพูดหลังตัด punctuation",
    clinical: "ใช้เป็น proxy ของ vocabulary production และ session participation",
    direction: "สูง = ดี",
  },
  unintelligible_count: {
    title: "Unintelligible count",
    group: "ASD markers",
    desc: "จำนวน utterances ที่มี marker เช่น xxx หรือ yyy",
    clinical: "ช่วยติดตามความชัดเจนของ speech และคุณภาพ transcript",
    direction: "ต่ำ = ดี",
  },
  unintelligible_ratio: {
    title: "Unintelligible ratio",
    group: "ASD markers",
    desc: "unintelligible_count / total_utterances เพื่อ normalize ตามความยาว session",
    clinical: "เหมาะกว่า count เมื่อต้องเปรียบเทียบ transcript ที่ยาวไม่เท่ากัน",
    direction: "ต่ำ = ดี",
  },
  zero_vocalization_count: {
    title: "Zero vocalizations",
    group: "ASD markers",
    desc: "จำนวนบรรทัด 0 . ที่สื่อถึง response แบบไม่ใช้เสียง",
    clinical: "ใช้ดู nonverbal response trend โดยต้องอ่านคู่กับ context",
    direction: "ต่ำ = ดี",
  },
  nonverbal_vocalization_count: {
    title: "Non-verbal vocalizations",
    group: "ASD markers",
    desc: "จำนวน marker เช่น &=laugh, &=gasp, &=cry",
    clinical: "เป็น signal ที่ต้องตีความตามบริบท เพราะบางกรณีอาจเป็น social engagement",
    direction: "บริบทขึ้นอยู่",
  },
  question_ratio: {
    title: "Question ratio",
    group: "Pragmatic",
    desc: "สัดส่วน utterances ของเด็กที่เป็นคำถาม",
    clinical: "เกี่ยวกับ social initiation และ pragmatic language",
    direction: "สูง = ดี",
  },
  echolalia_count: {
    title: "Echolalia count",
    group: "ASD markers",
    desc: "จำนวนครั้งที่เด็กพูดซ้ำคำพูดก่อนหน้าแบบใกล้เคียง",
    clinical: "เป็น marker ที่ควรใช้ประกอบร่วมกับ feature อื่นและการตรวจ transcript",
    direction: "สูง = ASD marker",
  },
  echolalia_ratio: {
    title: "Echolalia ratio",
    group: "ASD markers",
    desc: "echolalia_count / total_utterances",
    clinical: "ใช้เปรียบเทียบข้าม session ได้ดีกว่า count",
    direction: "สูง = ASD marker",
  },
};

const PARENT_CONCERN_ITEMS = [
  "Rarely responds when called by name",
  "Rarely points to request or share interest",
  "Limited pretend play",
  "Limited eye contact or social smile",
  "Limited interest in other children",
  "Frequent repeated phrases",
  "Limited spoken words or phrases for age",
  "Repetitive movements or object routines",
  "High sensory sensitivity",
  "Parent remains concerned about communication",
];

const FALLBACK_MODELS = [
  { task: "binary", model: "LogReg", accuracy: 0.8770, f1_macro: 0.8770, roc_auc: 0.9312, sensitivity: 0.8462, specificity: 0.9123, ppv: 0.9167, npv: 0.8387, brier_score: 0.0983 },
  { task: "binary", model: "RandomForest", accuracy: 0.8279, f1_macro: 0.8276, roc_auc: 0.9063, sensitivity: 0.8154, specificity: 0.8421, ppv: 0.8548, npv: 0.8000, brier_score: 0.1278 },
  { task: "binary", model: "SVM", accuracy: 0.8525, f1_macro: 0.8523, roc_auc: 0.9239, sensitivity: 0.8308, specificity: 0.8772, ppv: 0.8852, npv: 0.8197, brier_score: 0.1127 },
  { task: "multiclass", model: "LogReg", accuracy: 0.7869, f1_macro: 0.7427, roc_auc: null },
  { task: "multiclass", model: "RandomForest", accuracy: 0.8279, f1_macro: 0.7746, roc_auc: null },
  { task: "multiclass", model: "SVM", accuracy: 0.7459, f1_macro: 0.7062, roc_auc: null },
  { task: "binary", model: "TabularMLP", accuracy: 0.8525, f1_macro: 0.8525, roc_auc: 0.9320 },
  { task: "binary", model: "UtteranceLSTM", accuracy: 0.6311, f1_macro: 0.6311, roc_auc: 0.7193 },
];

const colors = ["oklch(60% 0.19 260)", "oklch(68% 0.16 155)", "oklch(67% 0.16 295)", "oklch(78% 0.16 78)", "oklch(65% 0.18 28)"];

const state = {
  combined: [],
  models: FALLBACK_MODELS,
  progress: [],
  longitudinal: [],
  thresholds: [],
  calibration: [],
  decision: [],
  predictions: [],
  subgroups: [],
  loco: [],
  fairness: [],
  calibrationSummary: [],
  modelCard: null,
  liveTimer: null,
  livePaused: false,
  liveTick: 0,
};

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines.shift().split(",");
  return lines.map((line) => {
    const values = line.split(",");
    return Object.fromEntries(headers.map((h, i) => [h, coerce(values[i])]));
  });
}

function coerce(value) {
  if (value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : value;
}

async function fetchCSV(path, fallback = []) {
  try {
    const response = await fetch(path);
    if (!response.ok) return fallback;
    return parseCSV(await response.text());
  } catch {
    return fallback;
  }
}

async function fetchJSON(path, fallback = null) {
  try {
    const response = await fetch(path);
    if (!response.ok) return fallback;
    return response.json();
  } catch {
    return fallback;
  }
}

function groupBy(rows, key) {
  return rows.reduce((acc, row) => {
    const k = row[key] ?? "unknown";
    acc[k] = acc[k] || [];
    acc[k].push(row);
    return acc;
  }, {});
}

function mean(rows, key) {
  const values = rows.map((r) => Number(r[key])).filter(Number.isFinite);
  if (!values.length) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function std(rows, key) {
  const values = rows.map((r) => Number(r[key])).filter(Number.isFinite);
  if (values.length < 2) return 0;
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  return Math.sqrt(values.reduce((sum, value) => sum + (value - avg) ** 2, 0) / (values.length - 1));
}

function correlation(rows, a, b) {
  const pairs = rows
    .map((row) => [Number(row[a]), Number(row[b])])
    .filter(([x, y]) => Number.isFinite(x) && Number.isFinite(y));
  if (pairs.length < 3) return 0;
  const ax = pairs.reduce((sum, [x]) => sum + x, 0) / pairs.length;
  const ay = pairs.reduce((sum, [, y]) => sum + y, 0) / pairs.length;
  const numerator = pairs.reduce((sum, [x, y]) => sum + (x - ax) * (y - ay), 0);
  const dx = Math.sqrt(pairs.reduce((sum, [x]) => sum + (x - ax) ** 2, 0));
  const dy = Math.sqrt(pairs.reduce((sum, [, y]) => sum + (y - ay) ** 2, 0));
  return dx && dy ? numerator / (dx * dy) : 0;
}

function filteredEdaRows() {
  const selectedGroups = Array.from(document.querySelectorAll("#edaGroups input:checked")).map((input) => input.value);
  const corpus = document.getElementById("edaCorpus").value;
  return state.combined.filter((row) => selectedGroups.includes(row.group) && (corpus === "all" || row.corpus === corpus));
}

function scale(value, min, max, outMin, outMax) {
  if (max === min) return (outMin + outMax) / 2;
  return outMin + ((value - min) / (max - min)) * (outMax - outMin);
}

function renderBars(targetId, rows, formatter = (v) => v, maxOverride = null) {
  const target = document.getElementById(targetId);
  if (!target) return;
  const max = maxOverride ?? Math.max(...rows.map((row) => Number(row.value) || 0), 1);
  target.innerHTML = rows
    .map((row, i) => {
      const value = Number(row.value) || 0;
      const width = Math.max(2, (value / max) * 100).toFixed(1);
      return `
        <div class="bar-row">
          <div class="bar-label">${row.label}</div>
          <div class="bar-track" aria-hidden="true">
            <div class="bar-fill" style="--value:${width}%; --bar-color:${row.color ?? colors[i % colors.length]}"></div>
          </div>
          <div class="bar-value">${formatter(value)}</div>
        </div>
      `;
    })
    .join("");
}

function renderDataset() {
  const corpus = document.getElementById("corpusFilter").value;
  const metric = document.getElementById("datasetMetric").value;
  const filtered = corpus === "all" ? state.combined : state.combined.filter((r) => r.corpus === corpus);
  const grouped = groupBy(filtered, "group");
  const rows = ["ASD", "TD", "DD"].filter((g) => grouped[g]).map((g, i) => ({
    label: g,
    value: metric === "count" ? grouped[g].length : mean(grouped[g], metric),
    color: colors[i],
  }));
  renderBars("datasetChart", rows, metric === "count" ? (v) => String(v) : (v) => v.toFixed(metric.includes("ratio") || metric === "ttr" ? 3 : 2));
  document.getElementById("datasetInsight").textContent =
    `${filtered.length} records shown · metric: ${metric.replaceAll("_", " ")} · corpus: ${corpus}`;
}

function renderComposition() {
  const view = document.getElementById("groupView").value;
  const grouped = groupBy(state.combined, view);
  const rows = Object.entries(grouped).map(([label, values], i) => ({ label, value: values.length, color: colors[i % colors.length] }));
  const total = rows.reduce((sum, row) => sum + row.value, 0);
  let cursor = 0;
  const gradient = rows.map((row) => {
    const start = cursor;
    cursor += (row.value / Math.max(total, 1)) * 100;
    return `${row.color} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`;
  }).join(", ");
  document.getElementById("compositionDonut").style.background = `conic-gradient(${gradient})`;
  document.getElementById("donutTotal").textContent = total;
  document.getElementById("groupLegend").innerHTML = rows
    .map((r) => `<div><span class="dot" style="background:${r.color}"></span>${r.label}<strong>${r.value}</strong></div>`)
    .join("");
}

function renderTopFeatures() {
  const rows = ["mlu", "mluw", "ttr", "total_words", "echolalia_ratio"].map((feature) => ({
    feature,
    value: mean(state.combined, feature),
  }));
  document.getElementById("topFeatureTable").innerHTML = rows.map((row) => `
    <div>
      <span>${row.feature}</span>
      <strong>${row.value.toFixed(row.feature.includes("ratio") || row.feature === "ttr" ? 3 : 2)}</strong>
    </div>
  `).join("");
}

function renderFeature() {
  const feature = document.getElementById("featureSelect").value;
  const grouped = groupBy(state.combined, "group");
  const rows = ["ASD", "DD", "TD"].filter((g) => grouped[g]).map((g, i) => ({
    label: g,
    value: mean(grouped[g], feature),
    color: colors[i],
  }));
  renderBars("featureChart", rows, (v) => v.toFixed(feature.includes("ratio") || feature === "ttr" ? 3 : 2));
  const values = state.combined.map((r) => Number(r[feature])).filter(Number.isFinite);
  const avg = values.reduce((a, b) => a + b, 0) / Math.max(values.length, 1);
  const doc = FEATURE_DOCS[feature];
  document.getElementById("featureDetail").innerHTML = `
    <div><strong>${doc.title}</strong><span>${doc.group} · ${doc.direction}</span></div>
    <div><strong>Mean all</strong><span>${avg.toFixed(3)} · SD ${std(state.combined, feature).toFixed(3)}</span></div>
    <div><strong>Definition</strong><span>${doc.desc}</span></div>
    <div><strong>Clinical note</strong><span>${doc.clinical}. ใช้เป็น screening/progress signal ไม่ใช่ diagnosis เดี่ยว ๆ</span></div>
  `;
}

function renderFeatureReferenceCards() {
  const target = document.getElementById("featureReferenceCards");
  if (!target) return;
  target.innerHTML = FEATURE_OPTIONS.map((feature) => {
    const doc = FEATURE_DOCS[feature];
    return `
      <button type="button" class="feature-ref-card" data-feature="${feature}">
        <span>${doc.group}</span>
        <strong>${feature}</strong>
        <small>${doc.direction}</small>
      </button>
    `;
  }).join("");
}

function renderScatter(rows) {
  const target = document.getElementById("edaScatter");
  const xFeature = document.getElementById("edaX").value;
  const yFeature = document.getElementById("edaY").value;
  const valuesX = rows.map((row) => Number(row[xFeature])).filter(Number.isFinite);
  const valuesY = rows.map((row) => Number(row[yFeature])).filter(Number.isFinite);
  const minX = Math.min(...valuesX, 0);
  const maxX = Math.max(...valuesX, 1);
  const minY = Math.min(...valuesY, 0);
  const maxY = Math.max(...valuesY, 1);
  const width = 660;
  const height = 340;
  const pad = 38;
  const groupColor = { ASD: colors[0], DD: colors[1], TD: colors[2] };
  target.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <line x1="${pad}" y1="${height - pad}" x2="${width - 18}" y2="${height - pad}" class="axis"></line>
      <line x1="${pad}" y1="18" x2="${pad}" y2="${height - pad}" class="axis"></line>
      ${rows.slice(0, 170).map((row) => {
        const x = scale(Number(row[xFeature]), minX, maxX, pad, width - 28);
        const y = scale(Number(row[yFeature]), minY, maxY, height - pad, 24);
        const r = scale(Number(row.total_words) || 1, 1, Math.max(...rows.map((item) => Number(item.total_words) || 1)), 4, 14);
        return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r.toFixed(1)}" fill="${groupColor[row.group] ?? colors[3]}"><title>${row.participant_id} · ${row.group} · ${row.corpus}</title></circle>`;
      }).join("")}
      <text x="${width / 2}" y="${height - 5}" text-anchor="middle">${xFeature}</text>
      <text x="12" y="${height / 2}" text-anchor="middle" transform="rotate(-90 12 ${height / 2})">${yFeature}</text>
    </svg>
  `;
}

function renderDistribution(rows) {
  const target = document.getElementById("edaDistribution");
  const feature = document.getElementById("edaDist").value;
  const grouped = groupBy(rows, "group");
  const chartRows = ["ASD", "DD", "TD"].filter((group) => grouped[group]).map((group, i) => ({
    label: group,
    value: mean(grouped[group], feature),
    spread: std(grouped[group], feature),
    color: colors[i],
  }));
  target.innerHTML = chartRows.map((row) => {
    const max = Math.max(...chartRows.map((item) => item.value + item.spread), 1);
    const width = Math.max(3, ((row.value + row.spread) / max) * 100).toFixed(1);
    const mid = Math.max(2, (row.value / max) * 100).toFixed(1);
    return `
      <div class="dist-row">
        <span>${row.label}</span>
        <div class="dist-track">
          <i style="width:${width}%; background:${row.color}"></i>
          <b style="left:${mid}%"></b>
        </div>
        <strong>${row.value.toFixed(feature.includes("ratio") || feature === "ttr" ? 3 : 2)}</strong>
      </div>
    `;
  }).join("");
}

function renderCorrelation(rows) {
  const target = document.getElementById("edaCorrelation");
  const features = ["mlu", "mluw", "ttr", "total_words", "unintelligible_ratio", "zero_vocalization_count", "question_ratio", "echolalia_ratio"];
  const labels = {
    mlu: "MLU",
    mluw: "MLUw",
    ttr: "TTR",
    total_words: "Words",
    unintelligible_ratio: "Unint.",
    zero_vocalization_count: "Zero",
    question_ratio: "Q ratio",
    echolalia_ratio: "Echo",
  };
  target.innerHTML = `
    <div class="corr-grid">
      <span></span>
      ${features.map((feature) => `<strong title="${feature}">${labels[feature]}</strong>`).join("")}
      ${features.map((rowFeature) => `
        <strong title="${rowFeature}">${labels[rowFeature]}</strong>
        ${features.map((colFeature) => {
          const value = correlation(rows, rowFeature, colFeature);
          const hue = value >= 0 ? "260" : "30";
          const light = 95 - Math.abs(value) * 26;
          return `<span style="background:oklch(${light}% 0.12 ${hue}); color:${Math.abs(value) > 0.55 ? "oklch(99% 0.004 220)" : "oklch(28% 0.03 245)"}">${value.toFixed(2)}</span>`;
        }).join("")}
      `).join("")}
    </div>
  `;
}

function renderRawTable(rows) {
  const target = document.getElementById("rawDataTable");
  const columns = ["participant_id", "corpus", "group", "age_months", "mlu", "ttr", "total_words", "echolalia_ratio"];
  target.innerHTML = `
    <table>
      <thead><tr>${columns.map((col) => `<th>${col}</th>`).join("")}</tr></thead>
      <tbody>
        ${rows.slice(0, 10).map((row) => `
          <tr>${columns.map((col) => `<td>${Number.isFinite(Number(row[col])) ? Number(row[col]).toFixed(col.includes("ratio") || col === "ttr" || col === "mlu" ? 3 : 0) : row[col]}</td>`).join("")}</tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderEda() {
  const rows = filteredEdaRows();
  renderScatter(rows);
  renderDistribution(rows);
  renderCorrelation(rows);
  renderRawTable(rows);
  document.getElementById("edaCaption").textContent = `Showing ${rows.length} of ${state.combined.length} rows after filters`;
}

function renderModels() {
  const task = document.getElementById("modelTask").value;
  const metric = document.querySelector("#modelMetric button.active").dataset.metric;
  const rows = state.models
    .filter((m) => m.task === task && Number.isFinite(Number(m[metric])))
    .map((m, i) => ({ label: m.model, value: Number(m[metric]), color: colors[i % colors.length] }));
  renderBars("modelChart", rows, (v) => v.toFixed(3), 1);
}

function renderTrustLeaderboard() {
  const metric = document.getElementById("trustMetric").value;
  const rows = state.models
    .filter((m) => m.task === "binary" && Number.isFinite(Number(m[metric])))
    .sort((a, b) => {
      const dir = metric === "brier_score" ? 1 : -1;
      return dir * (Number(a[metric]) - Number(b[metric]));
    });
  const target = document.getElementById("trustLeaderboard");
  if (!target) return;
  target.innerHTML = rows.map((row, index) => `
    <div class="trust-row ${index === 0 ? "top" : ""}">
      <span>${row.model}</span>
      <strong>${Number(row[metric]).toFixed(3)}</strong>
      <small>sens ${fmtMetric(row.sensitivity)} · spec ${fmtMetric(row.specificity)} · NPV ${fmtMetric(row.npv)}</small>
    </div>
  `).join("");
}

function fmtMetric(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(2) : "n/a";
}

function thresholdRow() {
  const threshold = Number(document.getElementById("thresholdSlider").value);
  const rows = state.thresholds.length ? state.thresholds : FALLBACK_MODELS
    .filter((m) => m.model === "LogReg")
    .map((m) => ({ threshold: 0.5, ...m, tp: 56, fp: 9, tn: 48, fn: 9, uncertain_rate: 0.2 }));
  return rows.reduce((best, row) => (
    Math.abs(Number(row.threshold) - threshold) < Math.abs(Number(best.threshold) - threshold) ? row : best
  ), rows[0]);
}

function renderThresholdPlayground() {
  const row = thresholdRow();
  const threshold = Number(row.threshold || 0.5);
  document.getElementById("thresholdLabel").textContent = threshold.toFixed(2);
  const stats = [
    ["Sensitivity", row.sensitivity],
    ["Specificity", row.specificity],
    ["PPV", row.ppv],
    ["NPV", row.npv],
  ];
  document.getElementById("thresholdMetrics").innerHTML = stats.map(([label, value]) => `
    <div><span>${label}</span><strong>${fmtMetric(value)}</strong></div>
  `).join("");
  document.getElementById("confusionMatrix").innerHTML = `
    <div><span>TN</span><strong>${row.tn ?? "n/a"}</strong></div>
    <div><span>FP</span><strong>${row.fp ?? "n/a"}</strong></div>
    <div><span>FN</span><strong>${row.fn ?? "n/a"}</strong></div>
    <div><span>TP</span><strong>${row.tp ?? "n/a"}</strong></div>
  `;
}

function renderLineChart(targetId, rows, series, options = {}) {
  const target = document.getElementById(targetId);
  if (!target) return;
  if (!rows.length) {
    target.innerHTML = `<div class="empty-note">Metrics not generated yet. Run python src/classifier.py.</div>`;
    return;
  }
  const width = 660;
  const height = 260;
  const pad = 34;
  const xValues = rows.map((r) => Number(r[options.x || "threshold"])).filter(Number.isFinite);
  const allY = rows.flatMap((r) => series.map((s) => Number(r[s.key]))).filter(Number.isFinite);
  const minX = Math.min(...xValues, 0);
  const maxX = Math.max(...xValues, 1);
  const minY = Math.min(...allY, 0);
  const maxY = Math.max(...allY, 1);
  const paths = series.map((s, i) => {
    const points = rows.map((row) => {
      const x = scale(Number(row[options.x || "threshold"]), minX, maxX, pad, width - 22);
      const y = scale(Number(row[s.key]), minY, maxY, height - pad, 18);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    return `<polyline points="${points.join(" ")}" style="--line-color:${s.color || colors[i % colors.length]}"><title>${s.label}</title></polyline>`;
  }).join("");
  target.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <line x1="${pad}" y1="${height - pad}" x2="${width - 18}" y2="${height - pad}" class="axis"></line>
      <line x1="${pad}" y1="18" x2="${pad}" y2="${height - pad}" class="axis"></line>
      ${options.diagonal ? `<line x1="${pad}" y1="${height - pad}" x2="${width - 22}" y2="18" class="diagonal"></line>` : ""}
      ${paths}
      <text x="${width / 2}" y="${height - 5}" text-anchor="middle">${options.xLabel || options.x || "threshold"}</text>
    </svg>
    <div class="line-legend">${series.map((s, i) => `<span><i style="background:${s.color || colors[i % colors.length]}"></i>${s.label}</span>`).join("")}</div>
  `;
}

function renderCalibration() {
  renderLineChart("calibrationChart", state.calibration, [
    { key: "observed_rate", label: "observed", color: colors[0] },
  ], { x: "predicted_mean", xLabel: "predicted probability", diagonal: true });
  const summary = state.calibrationSummary[0] || {};
  const brier = Number.isFinite(Number(summary.brier_score))
    ? summary.brier_score
    : state.models.find((m) => m.model === "LogReg" && Number.isFinite(Number(m.brier_score)))?.brier_score;
  const ece = summary.ece;
  const target = document.getElementById("calibrationSummary");
  if (target) {
    target.innerHTML = `
      <div><span>ECE</span><strong>${Number.isFinite(Number(ece)) ? Number(ece).toFixed(3) : "n/a"}</strong></div>
      <div><span>Brier</span><strong>${Number.isFinite(Number(brier)) ? Number(brier).toFixed(3) : "n/a"}</strong></div>
    `;
  }
  document.getElementById("calibrationInsight").textContent =
    `ECE: ${Number.isFinite(Number(ece)) ? Number(ece).toFixed(3) : "run fairness script"} · Brier score: ${Number.isFinite(Number(brier)) ? Number(brier).toFixed(3) : "run classifier.py to generate"} · lower is better calibrated.`;
}

function renderFairnessAudit() {
  const target = document.getElementById("fairnessTable");
  if (!target) return;
  if (!state.fairness.length) {
    target.innerHTML = `<div class="empty-note">Run python scripts/compute_fairness_metrics.py to generate fairness metrics.</div>`;
    return;
  }
  target.innerHTML = `
    <table>
      <thead><tr><th>Attribute</th><th>Group</th><th>N</th><th>TPR</th><th>FPR</th><th>DP</th><th>TPR Δ</th><th>FPR Δ</th></tr></thead>
      <tbody>
        ${state.fairness.map((row) => `
          <tr>
            <td>${row.attribute}</td>
            <td>${row.group}</td>
            <td>${row.n}</td>
            <td>${fmtMetric(row.tpr)}</td>
            <td>${fmtMetric(row.fpr)}</td>
            <td>${fmtMetric(row.demographic_parity)}</td>
            <td>${fmtMetric(row.tpr_difference)}</td>
            <td>${fmtMetric(row.fpr_difference)}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderDecisionCurve() {
  renderLineChart("decisionCurve", state.decision, [
    { key: "model_net_benefit", label: "model", color: colors[0] },
    { key: "treat_all_net_benefit", label: "treat all", color: colors[3] },
    { key: "treat_none_net_benefit", label: "treat none", color: colors[4] },
  ], { x: "threshold", xLabel: "referral threshold" });
}

function renderUncertainty() {
  const grouped = groupBy(state.predictions.length ? state.predictions : [
    { uncertainty_zone: "low" }, { uncertainty_zone: "uncertain" }, { uncertainty_zone: "high" },
  ], "uncertainty_zone");
  const order = ["low", "uncertain", "high"];
  const zoneColors = { low: colors[1], uncertain: colors[3], high: colors[4] };
  const rows = order.map((label) => ({ label, value: grouped[label]?.length || 0, color: zoneColors[label] }));
  const total = Math.max(rows.reduce((sum, row) => sum + row.value, 0), 1);
  let cursor = 0;
  const gradient = rows.map((row) => {
    const start = cursor;
    cursor += (row.value / total) * 100;
    return `${row.color} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`;
  }).join(", ");
  document.getElementById("uncertaintyDonut").style.background = `conic-gradient(${gradient})`;
  document.getElementById("uncertaintyLegend").innerHTML = rows.map((r) => `
    <div><span class="dot" style="background:${r.color}"></span>${r.label}<strong>${r.value}</strong></div>
  `).join("");
}

function renderSubgroupRobustness() {
  const target = document.getElementById("subgroupHeatmap");
  if (!target) return;
  const rows = state.subgroups.length ? state.subgroups : [];
  if (!rows.length) {
    target.innerHTML = `<div class="empty-note">Run python src/classifier.py to generate subgroup_performance.csv.</div>`;
    return;
  }
  target.innerHTML = rows.map((row) => {
    const auc = Number(row.roc_auc);
    const light = Number.isFinite(auc) ? 96 - Math.min(Math.max(auc, 0), 1) * 28 : 92;
    return `
      <div style="background:oklch(${light}% 0.11 155)">
        <span>${row.dimension}: ${row.value}</span>
        <strong>AUC ${fmtMetric(row.roc_auc)}</strong>
        <small>n=${row.n} · sens ${fmtMetric(row.sensitivity)} · spec ${fmtMetric(row.specificity)}</small>
      </div>
    `;
  }).join("");
}

function renderLoco() {
  const target = document.getElementById("locoTable");
  if (!target) return;
  const rows = state.loco.length ? state.loco : [];
  target.innerHTML = `
    <table>
      <thead><tr><th>Held-out</th><th>n</th><th>Status</th><th>AUC</th><th>F1</th></tr></thead>
      <tbody>
        ${rows.map((row) => `<tr><td>${row.held_out_corpus}</td><td>${row.n_test}</td><td>${row.status}</td><td>${fmtMetric(row.roc_auc)}</td><td>${fmtMetric(row.f1_macro)}</td></tr>`).join("")}
      </tbody>
    </table>
  `;
}

function renderModelCard() {
  const card = state.modelCard || {};
  const target = document.getElementById("modelCardPanel");
  if (!target) return;
  const meta = card.training_metadata || {};
  target.innerHTML = `
    <div><span>Version</span><strong>${card.model_version || "runtime"}</strong></div>
    <div><span>Rows</span><strong>${meta.n_rows ?? state.combined.length}</strong></div>
    <div><span>Data hash</span><strong>${meta.data_hash || "not generated"}</strong></div>
    <div><span>Thai validation</span><strong>${card.thai_validation_status || "not_yet_validated"}</strong></div>
    <p>${card.intended_use || "ASD screening support and research demo; not diagnostic."}</p>
    <p><strong>Not intended:</strong> ${card.not_intended_use || "autonomous diagnosis or replacement for clinician assessment."}</p>
    <ul>${(card.clinical_caveats || ["Not externally validated in Thai clinical cohorts yet."]).map((item) => `<li>${item}</li>`).join("")}</ul>
  `;
}

function renderClinicalReadiness() {
  const target = document.getElementById("clinicalReadinessCards");
  if (!target) return;
  const cards = [
    {
      title: "Current prototype status",
      items: [
        "English public corpora",
        "internal validation",
        "parent demo",
        "model trust dashboard",
        "no-data-retention wording",
      ],
    },
    {
      title: "Needed before Thai clinical use",
      items: [
        "Thai validation dataset",
        "expert labels",
        "IRB/consent",
        "calibration",
        "subgroup audit",
        "clinician workflow testing",
      ],
    },
    {
      title: "Transcript QA workflow",
      pipeline: "Audio -> ASR -> CHAT formatter -> AI Transcript Reviewer -> Human confirmation -> Features -> Model/report",
    },
    {
      title: "Therapist report workflow",
      pipeline: "Multiple sessions -> features -> trend summary -> therapist report -> expert interpretation",
    },
    {
      title: "No Thai data yet",
      items: [
        "technical workflow is feasible",
        "governance structure is prepared",
        "reporting and safety layer is in place",
        "future Thai validation data can be accepted",
      ],
    },
    {
      title: "AI Speech Therapist Assistant",
      items: [
        "transcript QA interpretation",
        "speech-language pattern interpretation",
        "progress trend summary",
        "therapist report and case brief generation",
      ],
    },
    {
      title: "Assistant boundaries",
      items: [
        "cannot diagnose ASD",
        "cannot replace speech therapist judgment",
        "cannot validate Thai clinical accuracy without Thai data",
        "requires human-in-the-loop review",
      ],
    },
    {
      title: "Assistant workflow",
      pipeline: "Audio/CHAT -> Transcript QA -> Feature extraction -> Assistant interpretation -> Therapist review -> Clinical decision",
    },
  ];

  target.innerHTML = cards.map((card) => `
    <div class="readiness-card">
      <strong>${card.title}</strong>
      ${card.pipeline ? `<p class="readiness-pipeline">${card.pipeline}</p>` : ""}
      ${card.items ? `<ul>${card.items.map((item) => `<li>${item}</li>`).join("")}</ul>` : ""}
    </div>
  `).join("");
}

function renderAtlas() {
  const inventory = [
    ["Raw CHAT transcripts", "data/*/*.cha", "TalkBank/ASDBank source files used for feature extraction"],
    ["Classification features", "data/combined_features.csv", `${state.combined.length || 122} child-level rows for screening models`],
    ["Longitudinal features", "data/longitudinal_features.csv", `${state.longitudinal.length || 87} session rows for progress tracking`],
    ["Model metrics", "reports/metrics/*.csv", "classification, calibration, threshold, subgroup, and progress metrics"],
    ["Report figures", "reports/figures/*.png", "EDA, ROC, confusion matrix, feature importance, progress figures"],
    ["Model bundle", "artifacts/screening_model.joblib", "versioned LogReg bundle with feature schema and thresholds"],
  ];
  document.getElementById("dataInventory").innerHTML = inventory.map(([title, path, desc]) => `
    <div><strong>${title}</strong><span>${path}</span><p>${desc}</p></div>
  `).join("");

  const corpusMeta = [
    ["Eigsti", "ASD/DD/TD cross-sectional labels; core classifier training source"],
    ["Nadig", "Mixed ASD/TD labels read from CHAT @ID headers"],
    ["NYU-Emerson", "ASD-heavy cross-sectional corpus for broader ASD coverage"],
    ["Flusberg", "ASD longitudinal corpus; first session for classifier and full sequence for progress"],
    ["Rollins", "Longitudinal therapy sessions for progress tracking"],
    ["QuigleyMcNally", "Mostly mother speech in this project; used cautiously for longitudinal context"],
  ];
  document.getElementById("corpusAtlas").innerHTML = corpusMeta.map(([name, desc], i) => `
    <div><span class="status ${i < 4 ? "ok" : "next"}"></span>${name}<strong>${desc}</strong></div>
  `).join("");

  const evidence = [
    ["TRIPOD+AI", "Report predictors, data flow, missingness, validation, and calibration."],
    ["DECIDE-AI", "Frame this as early-stage clinical decision support with human oversight."],
    ["Canvas Dx / Megerian", "Use multimodal input and indeterminate outputs; avoid forced diagnosis."],
    ["ASDSpeech", "Speech can support graded severity, but severity is not diagnosis."],
    ["Child speech ASR", "Measure WER and feature drift before trusting audio-derived predictions."],
  ];
  document.getElementById("researchCards").innerHTML = evidence.map(([title, desc]) => `
    <div><strong>${title}</strong><p>${desc}</p></div>
  `).join("");

  const glossary = [
    ["CHAT", "TalkBank transcript format with speaker tiers such as *CHI:"],
    ["MLU", "Mean length of utterance; language complexity marker"],
    ["TTR", "Type-token ratio; lexical diversity marker"],
    ["Diarization", "Speaker separation, here child vs adult"],
    ["Calibration", "Whether predicted probabilities match observed rates"],
    ["Decision curve", "Net benefit across referral thresholds"],
    ["XAI", "Feature contribution explanation for an individual prediction"],
  ];
  document.getElementById("glossaryList").innerHTML = glossary.map(([term, desc]) => `
    <div><strong>${term}</strong><span>${desc}</span></div>
  `).join("");

  document.getElementById("atlasNarrative").innerHTML = `
    <strong>How to present this project:</strong>
    เริ่มจาก pain point เรื่อง early screening และ progress tracking, ต่อด้วย dataset จาก CHAT transcripts,
    อธิบาย 13 features ที่ clinician อ่านเข้าใจ, โชว์ model trust แทนโชว์ AUC อย่างเดียว,
    แล้วปิดด้วย safety: human-in-the-loop, no diagnosis claim, Thai validation needed.
  `;
}

function setupPresentationMode() {
  const button = document.getElementById("presentationMode");
  if (!button) return;
  button.addEventListener("click", () => {
    document.body.classList.toggle("presentation-mode");
    button.textContent = document.body.classList.contains("presentation-mode") ? "Exit presentation" : "Presentation mode";
  });
}

function renderScreening() {
  const values = Object.fromEntries(
    FEATURE_OPTIONS.map((feature) => {
      const input = document.querySelector(`[data-screen-feature="${feature}"]`);
      return [feature, input ? Number(input.value) : mean(state.combined, feature)];
    }),
  );
  const riskSignal =
    values.echolalia_ratio * 6 +
    values.unintelligible_ratio * 4 +
    values.zero_vocalization_count / 80 +
    Math.max(0, 2.6 - values.mlu) * 0.22 +
    Math.max(0, 0.32 - values.ttr) * 0.85 -
    values.question_ratio * 1.5 -
    Math.max(0, values.total_words - 360) / 1500;
  const mchatChecked = Array.from(document.querySelectorAll("#mchatGrid input:checked")).length;
  const mchatScore = (mchatChecked / PARENT_CONCERN_ITEMS.length) * 10;
  const prob = Math.max(0.06, Math.min(0.94, 0.48 + riskSignal + (mchatScore - 3) * 0.025));
  const asd = Math.max(0, Math.min(10, prob * 10));
  const comm = Math.max(0, Math.min(10, 5 + (values.mlu - 2.1) + (values.ttr - 0.3) * 4 + values.question_ratio * 8));
  const marker = Math.max(0, Math.min(10, values.echolalia_ratio * 80 + values.unintelligible_ratio * 18 + values.zero_vocalization_count / 18));
  const fusion = Math.max(0, Math.min(10, asd * 0.65 + mchatScore * 0.35));
  const label = prob >= 0.6 ? "HIGH risk, recommend referral" : prob < 0.4 ? "LOW risk, likely typical" : "UNCERTAIN, recommend further assessment";
  document.getElementById("riskNeedle").style.left = `${Math.round(prob * 100)}%`;
  document.getElementById("riskOutput").innerHTML = `<strong>${Math.round(prob * 100)}%</strong><span>${label}</span>`;
  document.getElementById("sevAsd").textContent = asd.toFixed(1);
  document.getElementById("sevComm").textContent = comm.toFixed(1);
  document.getElementById("sevMarker").textContent = marker.toFixed(1);
  document.getElementById("sevFusion").textContent = fusion.toFixed(1);
  const xai = [
    ["echolalia_ratio", values.echolalia_ratio * 6],
    ["unintelligible_ratio", values.unintelligible_ratio * 4],
    ["zero_vocalization_count", values.zero_vocalization_count / 80],
    ["low MLU", Math.max(0, 2.6 - values.mlu) * 0.22],
    ["question_ratio", -values.question_ratio * 1.5],
    ["total_words", -Math.max(0, values.total_words - 360) / 1500],
  ].sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).slice(0, 5);
  document.getElementById("xaiList").innerHTML = xai.map(([feature, value]) => `
    <div>
      <span class="status ${value > 0 ? "next" : "ok"}"></span>
      ${feature} <strong>${value > 0 ? "+" : ""}${value.toFixed(2)}</strong>
    </div>
  `).join("");
  document.getElementById("mchatScore").textContent = `${mchatChecked}/10 concerning`;
}

function applyScreeningProfile() {
  const profiles = {
    balanced: { age_months: 48, total_utterances: 180, mlu: 2.5, mluw: 2.3, ttr: 0.4, total_words: 400, unintelligible_count: 10, unintelligible_ratio: 0.05, zero_vocalization_count: 5, nonverbal_vocalization_count: 8, question_ratio: 0.08, echolalia_count: 3, echolalia_ratio: 0.02 },
    high: { age_months: 48, total_utterances: 150, mlu: 1.55, mluw: 1.65, ttr: 0.23, total_words: 190, unintelligible_count: 34, unintelligible_ratio: 0.18, zero_vocalization_count: 42, nonverbal_vocalization_count: 24, question_ratio: 0.02, echolalia_count: 18, echolalia_ratio: 0.12 },
    low: { age_months: 48, total_utterances: 260, mlu: 3.4, mluw: 3.0, ttr: 0.53, total_words: 820, unintelligible_count: 4, unintelligible_ratio: 0.015, zero_vocalization_count: 1, nonverbal_vocalization_count: 5, question_ratio: 0.12, echolalia_count: 1, echolalia_ratio: 0.004 },
  };
  const profile = profiles[document.getElementById("screeningProfile").value];
  Object.entries(profile).forEach(([feature, value]) => {
    const input = document.querySelector(`[data-screen-feature="${feature}"]`);
    if (input) input.value = value;
  });
  renderScreeningInputs();
  renderScreening();
}

function renderScreeningInputs() {
  const compact = ["age_months", "total_utterances", "total_words", "mlu", "mluw", "ttr", "unintelligible_ratio", "zero_vocalization_count", "question_ratio", "echolalia_ratio"];
  const target = document.getElementById("screeningInputs");
  if (!target) return;
  target.innerHTML = compact.map((feature) => {
    const input = document.querySelector(`[data-screen-feature="${feature}"]`);
    const value = input ? Number(input.value) : mean(state.combined, feature);
    const max = feature.includes("ratio") || feature === "ttr" ? 1 : Math.max(value * 2, mean(state.combined, feature) * 2, feature.includes("words") ? 1200 : 120);
    const step = feature.includes("ratio") || feature === "ttr" ? 0.01 : feature === "mlu" || feature === "mluw" ? 0.1 : 1;
    return `
      <label class="screen-input">
        <span>${feature}<strong>${value.toFixed(feature.includes("ratio") || feature === "ttr" || feature === "mlu" || feature === "mluw" ? 2 : 0)}</strong></span>
        <input type="range" min="0" max="${max}" step="${step}" value="${value}" data-screen-feature="${feature}" />
      </label>
    `;
  }).join("");
}

function renderMchat() {
  const target = document.getElementById("mchatGrid");
  if (!target) return;
  target.innerHTML = PARENT_CONCERN_ITEMS.map((item, index) => `
    <label>
      <input type="checkbox" value="${index}" />
      <span>${index + 1}. ${item}</span>
    </label>
  `).join("");
}

function renderProgress() {
  const child = document.getElementById("childSelect").value;
  const row = state.progress.find((r) => r.child === child) || state.progress[0];
  if (!row) return;
  const metrics = [
    ["MLU Δ", row.mlu_delta],
    ["MLUW Δ", row.mluw_delta],
    ["TTR Δ", row.ttr_delta],
    ["Words Δ", row.total_words_delta],
    ["Utts Δ", row.total_utterances_delta],
  ].map(([label, value], i) => ({ label, value: Math.max(Number(value) || 0, 0), color: colors[i] }));
  renderBars("progressChart", metrics, (v) => v.toFixed(labelLooksSmall(v) ? 2 : 0));
  document.getElementById("reportChild").textContent = `${row.child}, ${row.corpus} corpus`;
  document.getElementById("reportText").textContent =
    `${row.child} มี ${row.n_sessions} sessions. MLU เปลี่ยน ${fmt(row.mlu_delta)}, total words เปลี่ยน ${fmt(row.total_words_delta)}. ใช้เป็นข้อมูลประกอบ progress tracking เท่านั้น.`;
  document.getElementById("reportSessions").textContent = row.n_sessions;
  document.getElementById("reportWords").textContent = fmt(row.total_words_delta);
  document.getElementById("reportMlu").textContent = fmt(row.mlu_delta);
  renderProgressTrajectory();
  renderFirstLastTable(row);
}

function renderProgressTrajectory() {
  const target = document.getElementById("progressTrajectory");
  if (!target) return;
  const child = document.getElementById("childSelect").value;
  const feature = document.getElementById("progressFeature").value;
  const rows = state.longitudinal
    .filter((row) => row.child === child)
    .sort((a, b) => Number(a.session_order) - Number(b.session_order));
  if (!rows.length) {
    target.innerHTML = `<div class="empty-note">No longitudinal rows for this child.</div>`;
    return;
  }
  const values = rows.map((row) => Number(row[feature])).filter(Number.isFinite);
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const width = 660;
  const height = 260;
  const pad = 34;
  const step = (width - pad * 2) / Math.max(rows.length - 1, 1);
  const points = rows.map((row, i) => {
    const value = Number(row[feature]) || 0;
    return [pad + i * step, scale(value, min, max, height - pad, 18), value, row.session_order];
  });
  const path = points.map(([x, y], i) => `${i ? "L" : "M"} ${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  target.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <line x1="${pad}" y1="${height - pad}" x2="${width - 18}" y2="${height - pad}" class="axis"></line>
      <line x1="${pad}" y1="18" x2="${pad}" y2="${height - pad}" class="axis"></line>
      <path class="trajectory-area" d="${path} L ${points.at(-1)[0]} ${height - pad} L ${pad} ${height - pad} Z"></path>
      <path class="trajectory-line" d="${path}"></path>
      ${points.map(([x, y, value, session]) => `<circle cx="${x}" cy="${y}" r="5"><title>Session ${session}: ${value.toFixed(3)}</title></circle>`).join("")}
      ${points.map(([x, , , session]) => `<text x="${x}" y="${height - 5}" text-anchor="middle">${session}</text>`).join("")}
    </svg>
  `;
}

function renderFirstLastTable(row) {
  const target = document.getElementById("firstLastTable");
  if (!target) return;
  const features = ["mlu", "mluw", "ttr", "total_words", "total_utterances", "unintelligible_ratio", "zero_vocalization_count"];
  target.innerHTML = `
    <table>
      <thead><tr><th>Feature</th><th>First</th><th>Last</th><th>Delta</th><th>Trend</th></tr></thead>
      <tbody>
        ${features.map((feature) => {
          const start = Number(row[`${feature}_start`]) || 0;
          const end = Number(row[`${feature}_end`]) || 0;
          const delta = Number(row[`${feature}_delta`]) || end - start;
          const inverse = feature === "unintelligible_ratio" || feature === "zero_vocalization_count";
          const improved = inverse ? delta < 0 : delta > 0;
          const digits = feature.includes("ratio") || feature === "ttr" || feature === "mlu" || feature === "mluw" ? 3 : 0;
          return `<tr><td>${feature}</td><td>${start.toFixed(digits)}</td><td>${end.toFixed(digits)}</td><td>${delta > 0 ? "+" : ""}${delta.toFixed(digits)}</td><td><span class="pill ${improved ? "ok-pill" : "warn-pill"}">${improved ? "improved" : "watch"}</span></td></tr>`;
        }).join("")}
      </tbody>
    </table>
  `;
}

function liveSeries() {
  const metric = document.getElementById("liveMetric").value;
  if (metric === "model_auc") {
    return state.models
      .filter((m) => m.task === "binary" && Number.isFinite(Number(m.roc_auc)))
      .map((m) => ({ label: m.model, value: Number(m.roc_auc) }));
  }
  const grouped = groupBy(state.combined, "corpus");
  const rows = Object.entries(grouped).map(([label, rows]) => ({
    label,
    value: mean(rows, metric),
  }));
  return rows.length ? rows : [{ label: "No data", value: 0 }];
}

function renderLiveChart() {
  const svg = document.getElementById("liveChart");
  if (!svg) return;
  const rows = liveSeries();
  const values = rows.map((row, i) => {
    const drift = Math.sin((state.liveTick + i) * 0.75) * Math.max(row.value * 0.04, 0.003);
    return Math.max(0, row.value + drift);
  });
  const max = Math.max(...values, 1);
  const width = 720;
  const height = 300;
  const pad = 28;
  const step = (width - pad * 2) / Math.max(values.length - 1, 1);
  const points = values.map((value, i) => {
    const x = pad + i * step;
    const y = height - pad - (value / max) * (height - pad * 2);
    return [x, y, value, rows[i].label];
  });
  const path = points.map(([x, y], i) => `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const areaPath = path || `M ${pad} ${height - pad}`;
  svg.innerHTML = `
    <defs>
      <linearGradient id="liveFill" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stop-color="oklch(60% 0.19 260 / 32%)"></stop>
        <stop offset="100%" stop-color="oklch(60% 0.19 260 / 0%)"></stop>
      </linearGradient>
    </defs>
    <path class="live-area" d="${areaPath} L ${points.at(-1)?.[0] ?? pad} ${height - pad} L ${pad} ${height - pad} Z"></path>
    <path class="live-line" d="${areaPath}"></path>
    ${points.map(([x, y]) => `<circle cx="${x}" cy="${y}" r="5"></circle>`).join("")}
    ${points.map(([x, _y, _value, label]) => `<text x="${x}" y="${height - 6}" text-anchor="middle">${label}</text>`).join("")}
  `;
  const latest = points.at(-1);
  document.getElementById("liveMax").textContent = max.toFixed(max < 2 ? 2 : 0);
  document.getElementById("liveMid").textContent = (max / 2).toFixed(max < 2 ? 2 : 0);
  document.getElementById("liveTooltip").innerHTML = `<span>${latest?.[3] ?? "Current"}</span><strong>${(latest?.[2] ?? 0).toFixed(max < 2 ? 3 : 1)}</strong>`;
  document.getElementById("liveInsight").textContent =
    `Live view: ${document.getElementById("liveMetric").selectedOptions[0].textContent}. Values are recomputed from current project CSVs with a subtle realtime pulse.`;
  state.liveTick += 1;
}

function startLive() {
  clearInterval(state.liveTimer);
  state.liveTimer = setInterval(() => {
    if (!state.livePaused) renderLiveChart();
  }, 2200);
}

function labelLooksSmall(v) {
  return Math.abs(v) < 10;
}

function fmt(value) {
  const n = Number(value) || 0;
  return `${n >= 0 ? "+" : ""}${Math.abs(n) < 10 ? n.toFixed(2) : n.toFixed(0)}`;
}

function setupImageTabs() {
  document.querySelectorAll(".image-tabs").forEach((group) => {
    group.addEventListener("click", (event) => {
      const button = event.target.closest("button");
      if (!button) return;
      group.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      button.classList.add("active");
      document.getElementById(group.dataset.target).src = button.dataset.src;
    });
  });
}

function setupNav() {
  const links = Array.from(document.querySelectorAll(".side-nav a"));
  links.forEach((link) => {
    link.addEventListener("click", () => {
      links.forEach((l) => l.classList.remove("active"));
      link.classList.add("active");
    });
  });
}

function setupControls() {
  ["corpusFilter", "datasetMetric"].forEach((id) => document.getElementById(id).addEventListener("change", renderDataset));
  document.getElementById("groupView").addEventListener("change", renderComposition);
  document.getElementById("liveMetric").addEventListener("change", renderLiveChart);
  document.getElementById("liveToggle").addEventListener("click", () => {
    state.livePaused = !state.livePaused;
    document.getElementById("liveToggle").textContent = state.livePaused ? "Resume live" : "Pause live";
    document.getElementById("liveStatus").textContent = state.livePaused ? "Paused" : "Live";
  });
  document.getElementById("dashboardSearch").addEventListener("input", (event) => {
    const q = event.target.value.toLowerCase();
    document.querySelectorAll(".panel, .metric-card").forEach((el) => {
      el.classList.toggle("dimmed", q && !el.textContent.toLowerCase().includes(q));
    });
  });
  document.getElementById("featureSelect").addEventListener("change", renderFeature);
  document.getElementById("featureReferenceCards").addEventListener("click", (event) => {
    const card = event.target.closest("[data-feature]");
    if (!card) return;
    document.getElementById("featureSelect").value = card.dataset.feature;
    renderFeature();
    document.getElementById("features").scrollIntoView({ behavior: "smooth", block: "start" });
  });
  ["edaX", "edaY", "edaDist", "edaCorpus"].forEach((id) => document.getElementById(id).addEventListener("change", renderEda));
  document.getElementById("edaGroups").addEventListener("change", renderEda);
  document.getElementById("modelTask").addEventListener("change", renderModels);
  document.getElementById("trustMetric").addEventListener("change", renderTrustLeaderboard);
  document.getElementById("thresholdSlider").addEventListener("input", renderThresholdPlayground);
  document.getElementById("screeningProfile").addEventListener("change", applyScreeningProfile);
  document.getElementById("screeningInputs").addEventListener("input", (event) => {
    const input = event.target.closest("input");
    if (!input) return;
    renderScreeningInputs();
    renderScreening();
  });
  document.getElementById("mchatGrid").addEventListener("change", renderScreening);
  document.getElementById("childSelect").addEventListener("change", renderProgress);
  document.getElementById("progressFeature").addEventListener("change", renderProgressTrajectory);
  document.getElementById("audioMode").addEventListener("change", (event) => {
    const copy = {
      auto: "Mode: auto, fast single pass for mixed recordings.",
      dual_pass: "Mode: dual_pass, runs English and Thai passes then picks stronger segments.",
      thai_specialized: "Mode: thai_specialized, Thai-heavy recordings with a Thai-fine-tuned model.",
    };
    document.getElementById("audioInsight").textContent = copy[event.target.value];
  });
  document.getElementById("resetFilters").addEventListener("click", () => {
    document.getElementById("corpusFilter").value = "all";
    document.getElementById("datasetMetric").value = "count";
    renderDataset();
  });
  document.getElementById("modelMetric").addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    document.querySelectorAll("#modelMetric button").forEach((b) => b.classList.remove("active"));
    button.classList.add("active");
    renderModels();
  });
}

async function init() {
  const [
    combined,
    classifier,
    deep,
    progress,
    longitudinal,
    thresholds,
    calibration,
    decision,
    predictions,
    subgroups,
    loco,
    fairness,
    calibrationSummary,
    modelCard,
  ] = await Promise.all([
    fetchCSV("../data/combined_features.csv"),
    fetchCSV("../reports/metrics/classification_results.csv"),
    fetchCSV("../reports/metrics/deep_learning_results.csv"),
    fetchCSV("../reports/metrics/longitudinal_progress_summary.csv"),
    fetchCSV("../data/longitudinal_features.csv"),
    fetchCSV("../reports/metrics/threshold_metrics.csv"),
    fetchCSV("../reports/metrics/calibration_bins.csv"),
    fetchCSV("../reports/metrics/decision_curve.csv"),
    fetchCSV("../reports/metrics/binary_oof_predictions.csv"),
    fetchCSV("../reports/metrics/subgroup_performance.csv"),
    fetchCSV("../reports/metrics/leave_one_corpus_out.csv"),
    fetchCSV("../reports/metrics/fairness_metrics.csv"),
    fetchCSV("../reports/metrics/calibration_summary.csv"),
    fetchJSON("../artifacts/model_card.json"),
  ]);
  state.combined = combined;
  state.progress = progress;
  state.longitudinal = longitudinal;
  state.thresholds = thresholds;
  state.calibration = calibration;
  state.decision = decision;
  state.predictions = predictions;
  state.subgroups = subgroups;
  state.loco = loco;
  state.fairness = fairness;
  state.calibrationSummary = calibrationSummary;
  state.modelCard = modelCard;
  state.models = [...classifier, ...deep.map((m) => ({ ...m, task: "binary" }))].length ? [...classifier, ...deep.map((m) => ({ ...m, task: "binary" }))] : FALLBACK_MODELS;

  document.getElementById("metricChildren").textContent = combined.length || 122;
  const logReg = state.models.find((m) => m.task === "binary" && m.model === "LogReg");
  if (logReg && Number.isFinite(Number(logReg.roc_auc))) {
    document.getElementById("metricAuc").textContent = Number(logReg.roc_auc).toFixed(3);
  }
  const corpora = [...new Set(combined.map((r) => r.corpus).filter(Boolean))].sort();
  document.getElementById("corpusFilter").innerHTML += corpora.map((c) => `<option value="${c}">${c}</option>`).join("");
  document.getElementById("edaCorpus").innerHTML += corpora.map((c) => `<option value="${c}">${c}</option>`).join("");
  document.getElementById("featureSelect").innerHTML = FEATURE_OPTIONS.map((f) => `<option value="${f}">${f}</option>`).join("");
  document.getElementById("featureSelect").value = "mlu";
  ["edaX", "edaY", "edaDist", "progressFeature"].forEach((id) => {
    document.getElementById(id).innerHTML = FEATURE_OPTIONS.map((f) => `<option value="${f}">${f}</option>`).join("");
  });
  document.getElementById("edaX").value = "mlu";
  document.getElementById("edaY").value = "ttr";
  document.getElementById("edaDist").value = "mlu";
  document.getElementById("progressFeature").value = "mlu";
  document.getElementById("childSelect").innerHTML = progress.map((r) => `<option value="${r.child}">${r.child}</option>`).join("");
  if (progress.some((r) => r.child === "Roger")) document.getElementById("childSelect").value = "Roger";
  renderFeatureReferenceCards();
  renderMchat();
  renderScreeningInputs();

  setupControls();
  setupImageTabs();
  setupNav();
  setupPresentationMode();
  renderDataset();
  renderComposition();
  renderTopFeatures();
  renderFeature();
  renderEda();
  renderModels();
  renderTrustLeaderboard();
  renderThresholdPlayground();
  renderCalibration();
  renderDecisionCurve();
  renderUncertainty();
  renderSubgroupRobustness();
  renderLoco();
  renderFairnessAudit();
  renderModelCard();
  renderClinicalReadiness();
  renderAtlas();
  applyScreeningProfile();
  renderProgress();
  renderLiveChart();
  startLive();
}

init();
