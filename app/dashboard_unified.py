"""
Unified Streamlit dashboard foundation for the ASD project.

Run:
    streamlit run app/dashboard_unified.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# Make `src` importable when this file is launched directly by Streamlit.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.feature_schema import (  # noqa: E402
    FEATURES,
    MARKER_FEATURES,
    POSITIVE_FEATURES,
    UNCERTAIN_HIGH,
    UNCERTAIN_LOW,
)


DATA_DIR = PROJECT_ROOT / "data"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts"
METRICS_DIR = PROJECT_ROOT / "reports" / "metrics"
LITERATURE_DIR = PROJECT_ROOT / "docs" / "literature"

COLORS = {
    "TD": "#2EC4B6",
    "DD": "#FF9F1C",
    "ASD": "#E71D36",
    "primary": "#4361EE",
    "accent": "#7209B7",
    "muted": "#6C757D",
    "bg_card": "#FFFFFF",
    "bg_soft": "#F8F9FC",
    "text": "#1F2937",
}

PLOTLY_TEMPLATE = "plotly_white"
ST_CHART_CONFIG = {"displayModeBar": False}


# ---------------------------------------------------------------------------
# CSS injection: project_dashboard/styles.css tokens ported for Streamlit
# ---------------------------------------------------------------------------
CSS = """
<style>
:root {
  color-scheme: light;
  --bg: oklch(98.5% 0.006 220);
  --panel: oklch(99.2% 0.004 220);
  --line: oklch(90% 0.012 230);
  --ink: oklch(22% 0.03 245);
  --muted: oklch(51% 0.03 245);
  --sidebar: oklch(20% 0.055 255);
  --sidebar-2: oklch(14% 0.045 255);
  --blue: oklch(60% 0.19 260);
  --green: oklch(68% 0.16 155);
  --purple: oklch(67% 0.16 295);
  --amber: oklch(78% 0.16 78);
  --coral: oklch(65% 0.18 28);
  --shadow: 0 18px 50px oklch(25% 0.04 245 / 8%);
  --radius: 8px;
}

* { box-sizing: border-box; }

html { scroll-behavior: smooth; }

.stApp {
  color: var(--ink);
  background: var(--bg);
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    "Noto Sans Thai", sans-serif;
  line-height: 1.5;
}

.block-container {
  max-width: 1300px;
  padding-top: 1.35rem;
  padding-bottom: 3rem;
}

h1, h2, h3, h4, p { margin-top: 0; }
h1, h2, h3, h4 { color: var(--ink); letter-spacing: 0; }
h1 { margin-bottom: 5px; font-size: clamp(1.8rem, 3vw, 2.45rem); line-height: 1.08; font-weight: 850; }
h2 { margin-bottom: 4px; font-size: 1.12rem; line-height: 1.2; font-weight: 780; }
h3 { font-size: 1rem; font-weight: 760; }
p, .stCaptionContainer, .muted { color: var(--muted); }

button, input, select, textarea {
  font: inherit;
  max-width: 100%;
}

a { color: inherit; text-decoration: none; }
img { display: block; max-width: 100%; }

.hero {
  margin-bottom: 22px;
  padding: 28px 30px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  color: oklch(99% 0.004 220);
  background:
    radial-gradient(circle at 90% 0%, oklch(62% 0.17 285 / 45%), transparent 45%),
    linear-gradient(135deg, oklch(34% 0.12 260), oklch(24% 0.09 255));
  box-shadow: var(--shadow);
}

.hero h1 {
  margin: 0 0 8px;
  color: oklch(99% 0.004 220);
}

.hero .sub {
  max-width: 72rem;
  color: oklch(84% 0.025 245);
  font-size: 1rem;
}

.hero .tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.hero .tag,
.pill,
.chip,
.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 820;
}

.hero .tag {
  padding: 0 10px;
  color: oklch(96% 0.01 245);
  background: oklch(99% 0.004 220 / 14%);
  border: 1px solid oklch(99% 0.004 220 / 24%);
}

.section-label {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  margin-bottom: 8px;
  padding: 0 9px;
  border-radius: var(--radius);
  color: var(--blue);
  background: oklch(95% 0.025 260);
  font-size: 0.76rem;
  font-weight: 850;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.metric-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 18px;
  margin-bottom: 22px;
}

.metric-card,
.panel,
.card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  box-shadow: var(--shadow);
}

.metric-card {
  position: relative;
  min-height: 120px;
  padding: 20px;
  overflow: hidden;
  border-left: 4px solid var(--blue);
}

.metric-card.accent { border-left-color: var(--purple); }
.metric-card.td { border-left-color: var(--green); }
.metric-card.dd { border-left-color: var(--amber); }
.metric-card.asd { border-left-color: var(--coral); }

.metric-card .label {
  color: oklch(37% 0.035 245);
  font-size: 0.78rem;
  line-height: 1.25;
  font-weight: 850;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.metric-card .value {
  display: block;
  margin: 8px 0 4px;
  color: var(--ink);
  font-size: clamp(1.35rem, 1.8vw, 1.85rem);
  font-weight: 850;
  line-height: 1;
}

.metric-card .delta {
  max-width: 22ch;
  color: var(--muted);
  font-size: 0.82rem;
  line-height: 1.35;
}

.panel {
  min-width: 0;
  padding: 26px;
  margin-bottom: 22px;
}

.card {
  min-width: 0;
  height: 100%;
  padding: 22px;
}

.grid-two,
.grid-three {
  display: grid;
  gap: 18px;
  margin-bottom: 22px;
}

.grid-two { grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.85fr); }
.grid-three { grid-template-columns: repeat(3, minmax(0, 1fr)); }

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.panel-head p,
.metric-card p {
  margin-bottom: 0;
  color: var(--muted);
}

.feature-detail,
.insight-line,
.info-box,
.warn-box,
.success-box,
.empty-note {
  margin-top: 14px;
  padding: 14px;
  border-radius: var(--radius);
  color: oklch(38% 0.04 245);
  background: oklch(96.5% 0.009 230);
}

.info-box { border-left: 4px solid var(--blue); }
.warn-box { border-left: 4px solid var(--amber); background: oklch(96.5% 0.03 78); }
.success-box { border-left: 4px solid var(--green); background: oklch(96.5% 0.03 155); }

.empty-note {
  display: grid;
  place-items: center;
  min-height: 160px;
  color: var(--muted);
  text-align: center;
}

.chip {
  min-height: 24px;
  margin: 0 6px 6px 0;
  padding: 0 9px;
}

.chip-td,
.ok-pill {
  color: oklch(43% 0.12 155);
  background: oklch(92% 0.055 155);
}

.chip-dd,
.warn-pill {
  color: oklch(48% 0.12 78);
  background: oklch(94% 0.06 78);
}

.chip-asd {
  color: oklch(45% 0.16 28);
  background: oklch(94% 0.06 28);
}

.mini-table,
.feature-ref-grid,
.status-list,
.legend-list {
  display: grid;
  gap: 10px;
}

.mini-table div,
.feature-ref-card,
.status-list div,
.legend-list div {
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: oklch(97.5% 0.012 230);
}

.mini-table div,
.legend-list div {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 12px;
}

.mini-table span,
.feature-ref-card span,
.feature-ref-card small,
.status-list span {
  display: block;
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 780;
}

.mini-table strong,
.status-list strong {
  color: var(--blue);
  font-size: 1.05rem;
}

.feature-ref-grid {
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 190px), 1fr));
}

.feature-ref-card strong {
  display: block;
  margin: 6px 0;
  color: var(--ink);
  font-size: 0.88rem;
  overflow-wrap: anywhere;
  word-break: break-word;
  line-height: 1.22;
}

.feature-detail {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.feature-detail strong,
.feature-detail span {
  display: block;
}

.feature-detail span {
  margin-top: 4px;
  color: var(--muted);
}

.dot,
.status {
  display: inline-block;
  border-radius: 50%;
}

.dot {
  width: 10px;
  height: 10px;
  margin-right: 10px;
}

.dot.coral { background: var(--coral); }
.dot.blue { background: var(--blue); }
.dot.amber { background: var(--amber); }

.bar-chart {
  display: grid;
  gap: 14px;
}

.bar-row {
  display: grid;
  grid-template-columns: minmax(96px, 120px) minmax(0, 1fr) 70px;
  align-items: center;
  gap: 12px;
}

.bar-label {
  color: oklch(38% 0.04 245);
  font-weight: 780;
  overflow-wrap: anywhere;
  line-height: 1.2;
}

.bar-track {
  height: 16px;
  overflow: hidden;
  border-radius: 999px;
  background: oklch(94% 0.01 230);
}

.bar-fill {
  width: var(--value);
  height: 100%;
  border-radius: inherit;
  background: var(--bar-color);
  transition: width 220ms ease;
}

.bar-value {
  color: var(--muted);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

section[data-testid="stSidebar"] {
  background:
    radial-gradient(circle at 75% 15%, oklch(36% 0.1 260), transparent 30%),
    linear-gradient(180deg, var(--sidebar), var(--sidebar-2));
  border-right: 1px solid oklch(12% 0.035 255);
}

section[data-testid="stSidebar"] * {
  color: oklch(96% 0.01 245);
}

section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] small {
  color: oklch(80% 0.025 245);
}

section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
  justify-content: flex-start;
  width: 100%;
  min-height: 48px;
  padding: 0 16px;
  border: 0;
  border-radius: var(--radius);
  color: oklch(84% 0.025 245);
  background: transparent;
  font-weight: 760;
  transition: transform 180ms ease, background 180ms ease, color 180ms ease;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
  color: oklch(99% 0.004 220);
  background: linear-gradient(135deg, oklch(47% 0.16 260), oklch(38% 0.13 260));
  transform: translateY(-1px);
}

section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] {
  color: oklch(99% 0.004 220);
  background: linear-gradient(135deg, oklch(47% 0.16 260), oklch(38% 0.13 260));
  box-shadow: none;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 13px;
  margin-bottom: 18px;
}

.brand-icon {
  display: inline-grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--blue);
  color: oklch(99% 0.004 220);
  font-weight: 850;
}

.sidebar-card {
  margin-top: 22px;
  padding: 18px;
  border-radius: var(--radius);
  background:
    radial-gradient(circle at 90% 0%, oklch(62% 0.17 285 / 45%), transparent 45%),
    linear-gradient(135deg, oklch(34% 0.12 260), oklch(24% 0.09 255));
}

.sidebar-card span {
  color: oklch(80% 0.045 260);
  font-size: 0.78rem;
  font-weight: 850;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.sidebar-card strong {
  display: block;
  margin: 10px 0 8px;
}

[data-testid="stDataFrame"] {
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.stSelectbox [data-baseweb="select"],
.stMultiSelect [data-baseweb="select"],
.stNumberInput input,
.stTextInput input,
.stTextArea textarea {
  border-radius: var(--radius);
}

.stTabs [data-baseweb="tab-list"] { gap: 0.3rem; }

.stTabs [data-baseweb="tab"] {
  border-radius: var(--radius) var(--radius) 0 0;
  padding: 0.5rem 1.1rem;
  background: transparent;
}

.stTabs [aria-selected="true"] {
  background: var(--panel) !important;
  color: var(--blue) !important;
  font-weight: 800;
}

code {
  padding: 0.12rem 0.35rem;
  border-radius: 5px;
  color: var(--blue);
  background: oklch(95% 0.025 260);
  font-size: 0.9em;
}

pre {
  margin: 0;
  overflow-x: auto;
  padding: 18px;
  border-radius: var(--radius);
  color: oklch(92% 0.012 220);
  background: oklch(24% 0.025 245);
  font-size: 0.84rem;
  line-height: 1.55;
}

@keyframes soft-pulse {
  0%, 100% { box-shadow: 0 0 0 0 oklch(68% 0.16 155 / 18%); }
  50% { box-shadow: 0 0 0 8px oklch(68% 0.16 155 / 0%); }
}

.live-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--green);
  animation: soft-pulse 1.8s ease-in-out infinite;
}

@media (max-width: 1180px) {
  .metric-row,
  .grid-three {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .grid-two {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .block-container {
    padding: 1rem 1rem 2.2rem;
  }

  .metric-row,
  .grid-two,
  .grid-three,
  .feature-detail,
  .feature-ref-grid {
    grid-template-columns: 1fr;
  }

  .panel {
    padding: 18px;
  }

  .hero {
    padding: 22px;
  }
}
</style>
"""


FEATURE_DOCS = {
    "age_months": {
        "title": "Age (months)",
        "icon": "Age",
        "group": "Demographics",
        "desc": "อายุของเด็กในหน่วยเดือน แปลงจาก CHAT format `5;03.10` (ปี;เดือน.วัน)",
        "clinical": "ใช้เป็น control variable เพราะภาษาเด็กพัฒนาเร็วมากช่วง 2-5 ปี ต้องคุมอายุก่อนเปรียบเทียบกลุ่ม",
        "direction": "neutral",
    },
    "total_utterances": {
        "title": "Total utterances",
        "icon": "Utt",
        "group": "Productivity",
        "desc": "จำนวนประโยคที่เด็กพูดทั้งหมด โดยนับบรรทัด `*CHI:` ทุกบรรทัด",
        "clinical": "สะท้อนความถี่การสื่อสารและ engagement ใน session",
        "direction": "สูง = ดี",
    },
    "mlu": {
        "title": "MLU (morphemes)",
        "icon": "MLU",
        "group": "Complexity",
        "desc": "Mean Length of Utterance: จำนวน morphemes เฉลี่ยต่อประโยค",
        "clinical": "ตัวชี้วัดพัฒนาการโครงสร้างภาษาที่ใช้กันมากในงาน child language",
        "direction": "สูง = ดี",
    },
    "mluw": {
        "title": "MLU (words)",
        "icon": "MLUw",
        "group": "Complexity",
        "desc": "ความยาว utterance เฉลี่ยเมื่อนับเป็นคำแทน morpheme",
        "clinical": "เหมาะกับ workflow ที่ยังไม่ได้ parse morphology ละเอียด",
        "direction": "สูง = ดี",
    },
    "ttr": {
        "title": "TTR (Type-Token Ratio)",
        "icon": "TTR",
        "group": "Lexical diversity",
        "desc": "สูตร: `unique_words / total_words` เพื่อวัดความหลากหลายของคำ",
        "clinical": "ค่าอาจสะท้อน lexical diversity และการใช้คำซ้ำ แต่ไวต่อความยาว transcript",
        "direction": "สูง = ดี",
    },
    "total_words": {
        "title": "Total words",
        "icon": "Words",
        "group": "Productivity",
        "desc": "จำนวนคำที่เด็กพูด หลังตัด punctuation ออก",
        "clinical": "ใช้เป็น proxy ของ vocabulary production และ session participation",
        "direction": "สูง = ดี",
    },
    "unintelligible_count": {
        "title": "Unintelligible count",
        "icon": "Unint",
        "group": "ASD markers",
        "desc": "นับ utterances ที่มี marker เช่น `xxx` หรือ `yyy`",
        "clinical": "ช่วยติดตามความชัดเจนของ speech และคุณภาพ transcript",
        "direction": "ต่ำ = ดี",
    },
    "unintelligible_ratio": {
        "title": "Unintelligible ratio",
        "icon": "Ratio",
        "group": "ASD markers",
        "desc": "สัดส่วน `unintelligible_count / total_utterances`",
        "clinical": "เหมาะกว่า count เมื่อเปรียบเทียบ transcript ที่ยาวไม่เท่ากัน",
        "direction": "ต่ำ = ดี",
    },
    "zero_vocalization_count": {
        "title": "Zero vocalizations",
        "icon": "Zero",
        "group": "ASD markers",
        "desc": "นับบรรทัด `0 .` ที่สื่อถึง response แบบไม่ใช้เสียง",
        "clinical": "ใช้ดู nonverbal response trend โดยต้องอ่านคู่กับ context",
        "direction": "ต่ำ = ดี",
    },
    "nonverbal_vocalization_count": {
        "title": "Non-verbal vocalizations",
        "icon": "NonV",
        "group": "ASD markers",
        "desc": "นับ markers แบบ `&=gasp`, `&=laugh`, `&=cry`",
        "clinical": "เป็น signal ที่ต้องตีความตามบริบท เพราะบางกรณีอาจเป็น social engagement",
        "direction": "บริบทขึ้นอยู่",
    },
    "question_ratio": {
        "title": "Question ratio",
        "icon": "Q",
        "group": "Pragmatic",
        "desc": "สัดส่วน utterances ของเด็กที่เป็นคำถาม",
        "clinical": "เกี่ยวกับ social initiation, joint attention และ pragmatic language",
        "direction": "สูง = ดี",
    },
    "echolalia_count": {
        "title": "Echolalia count",
        "icon": "Echo",
        "group": "ASD markers",
        "desc": "จำนวนครั้งที่เด็กพูดซ้ำคำพูดก่อนหน้าแบบใกล้เคียง",
        "clinical": "เป็น marker ที่ควรใช้ประกอบร่วมกับ feature อื่นและการตรวจ transcript",
        "direction": "สูง = ASD marker",
    },
    "echolalia_ratio": {
        "title": "Echolalia ratio",
        "icon": "Echo%",
        "group": "ASD markers",
        "desc": "สัดส่วน `echolalia_count / total_utterances`",
        "clinical": "ใช้เปรียบเทียบข้าม session ได้ดีกว่า count",
        "direction": "สูง = ASD marker",
    },
}


NAV_ITEMS = [
    ("overview", "▦ Dashboard", "Overview from real project data"),
    ("dataset", "◫ Dataset", "Corpus and group composition"),
    ("features", "◎ Features", "Language feature reference"),
    ("eda", "≋ EDA", "Exploratory analysis"),
    ("screening", "◇ Screening", "Risk scoring workflow"),
    ("trust", "◬ Model Trust", "Validation and reliability"),
    ("audio", "◉ Audio", "Audio-to-assessment flow"),
    ("reports", "▤ Reports", "Figures and paper outputs"),
    ("progress", "↗ Progress", "Longitudinal tracking"),
    ("atlas", "▧ Atlas", "Project map"),
]

@st.cache_data
def load_combined() -> pd.DataFrame:
    path = DATA_DIR / "combined_features.csv"
    if not path.exists():
        st.error("combined_features.csv not found. Run `python src/data_loader.py` first.")
        st.stop()
    return pd.read_csv(path)


@st.cache_data
def load_longitudinal() -> pd.DataFrame:
    path = DATA_DIR / "longitudinal_features.csv"
    if not path.exists():
        st.error("longitudinal_features.csv not found. Run `python src/data_loader.py` first.")
        st.stop()
    return pd.read_csv(path).sort_values(["child", "session_order"])


@st.cache_data
def load_metric_csv(filename: str) -> pd.DataFrame:
    path = METRICS_DIR / filename
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


@st.cache_data
def load_model_card() -> dict:
    path = ARTIFACT_DIR / "model_card.json"
    if not path.exists():
        return {
            "model_version": "runtime-trained",
            "intended_use": "ASD screening support and research demo; not diagnostic.",
            "thresholds": {
                "uncertain_low": UNCERTAIN_LOW,
                "uncertain_high": UNCERTAIN_HIGH,
            },
        }
    try:
        import json

        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"model_version": "model-card-unreadable"}


def _compute_composite(df: pd.DataFrame) -> pd.DataFrame:
    direction = {
        "mlu": +1,
        "mluw": +1,
        "ttr": +1,
        "total_words": +1,
        "total_utterances": +1,
        "unintelligible_ratio": -1,
        "zero_vocalization_count": -1,
    }
    df = df.copy()
    z = pd.DataFrame(index=df.index)
    for feature, sign in direction.items():
        values = df[feature].astype(float)
        mean = values.mean()
        std = values.std(ddof=0)
        z[feature] = 0.0 if std == 0 else sign * (values - mean) / std
    df["composite_score"] = z.mean(axis=1).round(3)
    return df


def classify_risk(prob: float) -> tuple[str, str, str]:
    """Map P(ASD) to a clinical screening label and UI flavor."""
    if prob >= UNCERTAIN_HIGH:
        return ("HIGH risk -> recommend referral", "warn", COLORS["ASD"])
    if prob < UNCERTAIN_LOW:
        return ("LOW risk -> likely typical", "success", COLORS["TD"])
    return ("UNCERTAIN -> recommend further assessment", "warn", COLORS["DD"])


@st.cache_resource
def load_screening_model_artifact():
    bundle_path = ARTIFACT_DIR / "screening_model.joblib"
    if bundle_path.exists():
        try:
            bundle = joblib.load(bundle_path)
            if bundle.get("features") == FEATURES:
                return bundle["model"]
        except Exception:  # noqa: BLE001
            pass
    return None


@st.cache_data
def train_runtime_screening_model(df: pd.DataFrame):
    x_train = df[FEATURES].values
    y_train = (df["group"] == "ASD").astype(int).values
    pipe = Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("sc", StandardScaler()),
        (
            "clf",
            LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                random_state=42,
            ),
        ),
    ])
    pipe.fit(x_train, y_train)
    return pipe


def train_screening_model(df: pd.DataFrame):
    model = load_screening_model_artifact()
    if model is not None:
        return model
    return train_runtime_screening_model(df)


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = np.exp(-x)
        return float(1.0 / (1.0 + z))
    z = np.exp(x)
    return float(z / (1.0 + z))


PARENT_CHECKLIST_ITEMS = [
    ("ไม่ค่อยตอบสนองเมื่อเรียกชื่อ", "yes"),
    ("ไม่ค่อยชี้เพื่อขอของหรือชวนดูสิ่งที่สนใจ", "yes"),
    ("ไม่ค่อยเล่นสมมติ เช่น ป้อนตุ๊กตา หรือแกล้งคุยโทรศัพท์", "yes"),
    ("สบตาน้อยหรือไม่ค่อยยิ้มตอบขณะเล่นด้วย", "yes"),
    ("ไม่ค่อยสนใจเล่นหรือมองเด็กคนอื่น", "yes"),
    ("พูดซ้ำคำ/ประโยคเดิมบ่อยจนสื่อสารยาก", "yes"),
    ("พูดน้อยกว่าที่คาดสำหรับวัย หรือยังไม่ใช้วลี/ประโยค", "yes"),
    ("มีเสียง/ท่าทางซ้ำ ๆ เช่น โบกมือ หมุนตัว หรือเรียงของซ้ำ", "yes"),
    ("ไวต่อเสียง แสง สัมผัส หรือ routine เปลี่ยนแล้วลำบากมาก", "yes"),
    ("ผู้ปกครองรู้สึกกังวลเรื่องการสื่อสารหรือพัฒนาการ", "yes"),
]


def parent_checklist_severity(answers: list[str]) -> tuple[int, float]:
    n_concerning = 0
    for ans, (_q, concerning) in zip(answers, PARENT_CHECKLIST_ITEMS):
        if ans == concerning:
            n_concerning += 1
    return n_concerning, float(n_concerning)


def fuse_severity(
    speech_score: float,
    checklist_score: float,
    w_speech: float = 0.5,
) -> float:
    w_checklist = 1.0 - w_speech
    return round(w_speech * speech_score + w_checklist * checklist_score, 1)


def compute_severity(model, df_train: pd.DataFrame, x_row: np.ndarray) -> dict:
    imp = model.named_steps["imp"]
    sc = model.named_steps["sc"]
    clf = model.named_steps["clf"]

    x_imp = imp.transform(x_row)
    x_scaled = sc.transform(x_imp)[0]
    logit = float(clf.intercept_[0] + (clf.coef_[0] * x_scaled).sum())
    severity_overall = _sigmoid(logit) * 10.0

    def _subscore(feature_names: list[str], sign: int) -> float:
        zs = []
        for feature in feature_names:
            if feature not in df_train.columns:
                continue
            mu = float(df_train[feature].mean())
            sd = float(df_train[feature].std(ddof=0))
            if sd == 0:
                continue
            value = float(x_row[0, FEATURES.index(feature)])
            zs.append(sign * (value - mu) / sd)
        if not zs:
            return 5.0
        return _sigmoid(float(np.mean(zs))) * 10.0

    return {
        "severity_overall": round(severity_overall, 1),
        "communication_strength": round(_subscore(POSITIVE_FEATURES, sign=+1), 1),
        "marker_burden": round(_subscore(MARKER_FEATURES, sign=+1), 1),
        "logit": round(logit, 3),
    }


def hero(title: str, subtitle: str, tags: list[str] | None = None) -> None:
    tag_html = ""
    if tags:
        tag_html = '<div class="tags">' + "".join(
            f'<span class="tag">{tag}</span>' for tag in tags
        ) + "</div>"
    st.markdown(
        f'<div class="hero"><h1>{title}</h1><div class="sub">{subtitle}</div>{tag_html}</div>',
        unsafe_allow_html=True,
    )


def section_label(text: str) -> None:
    st.markdown(
        f'<span class="section-label">{text}</span>',
        unsafe_allow_html=True,
    )


def metric_card(col, label: str, value: str, delta: str = "", flavor: str = "") -> None:
    cls = f"metric-card {flavor}".strip()
    delta_html = f'<div class="delta">{delta}</div>' if delta else ""
    col.markdown(
        f'<div class="{cls}"><div class="label">{label}</div>'
        f'<div class="value">{value}</div>{delta_html}</div>',
        unsafe_allow_html=True,
    )


def info_box(text: str, kind: str = "info") -> None:
    cls = {"info": "info-box", "warn": "warn-box", "success": "success-box"}[kind]
    st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)


def style_fig(fig, height: int | None = None) -> go.Figure:
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        font={"family": "Inter, -apple-system, sans-serif", "color": COLORS["text"]},
        title_font={"size": 16, "color": COLORS["text"]},
        margin={"l": 10, "r": 10, "t": 40, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"gridcolor": "#EEF0F4", "zerolinecolor": "#EEF0F4"},
        yaxis={"gridcolor": "#EEF0F4", "zerolinecolor": "#EEF0F4"},
        legend={
            "bgcolor": "rgba(255,255,255,0.8)",
            "bordercolor": "#E5E7EB",
            "borderwidth": 1,
        },
    )
    if height is not None:
        fig.update_layout(height=height)
    return fig


def _format_metric(value: float, feature: str) -> str:
    if feature in {"ttr", "question_ratio", "echolalia_ratio", "unintelligible_ratio"}:
        return f"{value:.3f}"
    if abs(value) >= 100:
        return f"{value:,.0f}"
    return f"{value:.2f}"


def sidebar_nav() -> str:
    if "page" not in st.session_state:
        st.session_state["page"] = "overview"

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
              <span class="brand-icon">A</span>
              <span>
                <strong>ASD Flow</strong><br>
                <small>Clinical language AI</small>
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for key, label, help_text in NAV_ITEMS:
            if st.button(
                label,
                key=f"nav_{key}",
                type="primary" if st.session_state["page"] == key else "secondary",
                help=help_text,
                width="stretch",
            ):
                st.session_state["page"] = key
                st.rerun()

        st.markdown(
            """
            <div class="sidebar-card">
              <span>Next module</span>
              <strong>AI Transcript Reviewer</strong>
              <p>ตรวจ .cha, speaker labels, ASR confidence และ CHAT syntax ก่อนสกัด features</p>
            </div>
            <p style="margin-top:18px">v0.17.0 · Research prototype</p>
            """,
            unsafe_allow_html=True,
        )

    return st.session_state["page"]


def page_overview(df: pd.DataFrame, longitudinal: pd.DataFrame) -> None:
    hero(
        "AI-Assisted Clinical Assessment of Autism",
        "Term-paper prototype: วิเคราะห์ CHAT transcripts จาก ASDBank "
        "เพื่อคัดกรอง ASD และติดตามพัฒนาการจากการบำบัด",
        tags=[
            "Eigsti",
            "Nadig",
            "NYU-Emerson",
            "Flusberg",
            "13 features",
            "5 corpora",
            f"{len(df)} children",
        ],
    )

    c1, c2, c3, c4 = st.columns(4)
    metric_card(c1, "Cross-sectional", f"{len(df)}", "children in classification set")
    metric_card(
        c2,
        "Longitudinal",
        f"{longitudinal['child'].nunique()}",
        "children with sessions",
        flavor="accent",
    )
    metric_card(c3, "Features / child", f"{len(FEATURES)}", "extracted per transcript", flavor="td")
    metric_card(c4, "Best AUC", "0.93", "LogReg (ASD vs non-ASD)", flavor="asd")

    left, right = st.columns([1.2, 1])
    with left:
        section_label("Group distribution")
        st.markdown("### Samples by group x corpus")
        counts = df.groupby(["corpus", "group"]).size().reset_index(name="n")
        fig = px.bar(
            counts,
            x="group",
            y="n",
            color="corpus",
            barmode="group",
            text="n",
            category_orders={"group": ["TD", "DD", "ASD"]},
            color_discrete_sequence=[COLORS["primary"], COLORS["accent"], COLORS["TD"]],
        )
        fig.update_traces(textposition="outside", textfont_size=13, marker_line_width=0)
        st.plotly_chart(style_fig(fig, height=380), width="stretch", config=ST_CHART_CONFIG)

    with right:
        section_label("Per-group counts")
        st.markdown("### Total by group")
        group_counts = df["group"].value_counts()
        ca, cb, cc = st.columns(3)
        metric_card(ca, "TD", f"{group_counts.get('TD', 0)}", "typical development", flavor="td")
        metric_card(cb, "DD", f"{group_counts.get('DD', 0)}", "developmental delay", flavor="dd")
        metric_card(cc, "ASD", f"{group_counts.get('ASD', 0)}", "autism spectrum", flavor="asd")

        section_label("Pipeline status")
        info_box(
            "Features extracted &nbsp; Model metrics available &nbsp; Longitudinal data loaded "
            "&nbsp; Unified dashboard foundation started",
            kind="success",
        )

    section_label("Quick stats per group (mean)")
    st.markdown("### Key linguistic markers")
    table = df.groupby("group")[FEATURES].mean().round(2).reindex(["TD", "DD", "ASD"])
    display = table[
        [
            "age_months",
            "mlu",
            "mluw",
            "ttr",
            "total_words",
            "total_utterances",
            "unintelligible_ratio",
        ]
    ].rename(
        columns={
            "age_months": "Age (mo)",
            "mlu": "MLU (morph)",
            "mluw": "MLU (words)",
            "ttr": "TTR",
            "total_words": "Words",
            "total_utterances": "Utts",
            "unintelligible_ratio": "Unint. ratio",
        }
    )
    st.dataframe(display.style.background_gradient(cmap="Blues", axis=0), width="stretch")


def page_dataset(df: pd.DataFrame) -> None:
    hero(
        "Dataset Explorer",
        "สำรวจ `combined_features.csv` จากข้อมูลจริงของโปรเจกต์ แยกตาม corpus, group และ language metric",
        tags=["combined_features.csv", "ASDBank", "classification set", f"{len(df)} rows"],
    )

    corpora = sorted(df["corpus"].dropna().unique())
    selected_corpus = st.selectbox(
        "Filter by corpus",
        ["All corpora", *corpora],
        key="dataset_corpus_filter",
    )
    filtered = df if selected_corpus == "All corpora" else df[df["corpus"] == selected_corpus]

    c1, c2, c3, c4 = st.columns(4)
    metric_card(c1, "Rows shown", f"{len(filtered)}", "children after filter")
    metric_card(c2, "Corpora", f"{filtered['corpus'].nunique()}", "represented in view", flavor="accent")
    metric_card(c3, "Groups", f"{filtered['group'].nunique()}", "TD / DD / ASD labels", flavor="td")
    metric_card(c4, "Features", f"{len(FEATURES)}", "numeric language markers", flavor="asd")

    left, right = st.columns([1.25, 0.9])
    with left:
        section_label("Composition")
        st.markdown("### Group x corpus counts")
        counts = filtered.groupby(["corpus", "group"]).size().reset_index(name="n")
        fig = px.bar(
            counts,
            x="corpus",
            y="n",
            color="group",
            barmode="group",
            text="n",
            category_orders={"group": ["TD", "DD", "ASD"]},
            color_discrete_map=COLORS,
        )
        fig.update_traces(textposition="outside", marker_line_width=0)
        st.plotly_chart(style_fig(fig, height=420), width="stretch", config=ST_CHART_CONFIG)

    with right:
        section_label("Group totals")
        st.markdown("### Current filter")
        totals = filtered["group"].value_counts().reindex(["TD", "DD", "ASD"]).fillna(0).astype(int)
        for group, flavor in [("TD", "td"), ("DD", "dd"), ("ASD", "asd")]:
            st.markdown(
                f'<div class="mini-table"><div><span>{group}</span>'
                f'<strong>{totals[group]}</strong></div></div>',
                unsafe_allow_html=True,
            )

        metric = st.selectbox(
            "Metric summary",
            ["mlu", "ttr", "total_words", "total_utterances", "echolalia_ratio", "unintelligible_ratio"],
            key="dataset_metric_summary",
        )
        summary = filtered.groupby("group")[metric].agg(["mean", "std", "min", "max"]).round(3)
        st.dataframe(summary.reindex(["TD", "DD", "ASD"]), width="stretch")

    section_label("Metric by group")
    st.markdown(f"### Mean `{metric}` by group")
    metric_means = filtered.groupby("group")[metric].mean().reindex(["TD", "DD", "ASD"]).dropna()
    fig = go.Figure(
        go.Bar(
            x=metric_means.index,
            y=metric_means.values,
            marker_color=[COLORS.get(group, COLORS["primary"]) for group in metric_means.index],
            text=[_format_metric(value, metric) for value in metric_means.values],
            textposition="outside",
        )
    )
    fig.update_layout(showlegend=False, yaxis_title=f"{metric} (mean)")
    st.plotly_chart(style_fig(fig, height=320), width="stretch", config=ST_CHART_CONFIG)

    section_label("Preview")
    st.markdown("### Source rows")
    preview_columns = ["participant_id", "corpus", "group", *FEATURES]
    available_columns = [column for column in preview_columns if column in filtered.columns]
    st.dataframe(filtered[available_columns].head(50), width="stretch", hide_index=True)


def page_features(df: pd.DataFrame) -> None:
    hero(
        "Feature Reference",
        "ความหมายและความสำคัญทาง clinical ของแต่ละ feature ที่สกัดจาก CHAT transcripts",
        tags=["13 features", "CHI utterances only", "real group means"],
    )

    section_label("Overview")
    st.markdown("### Feature summary with live statistics")
    rows = []
    for feature in FEATURES:
        if feature not in df.columns:
            continue
        by_group = df.groupby("group")[feature].mean().to_dict()
        doc = FEATURE_DOCS[feature]
        rows.append(
            {
                "Feature": feature,
                "Group": doc["group"],
                "Direction": doc["direction"],
                "ASD": round(by_group.get("ASD", float("nan")), 3),
                "DD": round(by_group.get("DD", float("nan")), 3),
                "TD": round(by_group.get("TD", float("nan")), 3),
            }
        )
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    section_label("Deep dive")
    st.markdown("### อธิบายทีละ feature")
    picked = st.selectbox(
        "เลือก feature",
        FEATURES,
        index=FEATURES.index("mlu"),
        format_func=lambda feature: (
            f"{FEATURE_DOCS[feature]['icon']}  {feature} — {FEATURE_DOCS[feature]['title']}"
        ),
        key="feature_picker",
    )
    doc = FEATURE_DOCS[picked]
    sub = df.dropna(subset=[picked, "group"])

    left, right = st.columns([1.3, 1])
    with left:
        st.markdown(
            f'<div class="card">'
            f'<h3 style="margin:0">{doc["title"]}</h3>'
            f'<div style="margin:0.55rem 0 0.9rem 0">'
            f'<span class="chip chip-td">{doc["group"]}</span>'
            f'<span class="chip chip-dd">{doc["direction"]}</span>'
            f'</div>'
            f'<p><b>นิยาม:</b><br>{doc["desc"]}</p>'
            f'<p style="margin-bottom:0"><b>ความสำคัญ clinical:</b><br>{doc["clinical"]}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f"#### Stats for `{picked}`")
        ca, cb = st.columns(2)
        ca.metric("Mean (all)", f"{sub[picked].mean():.3f}")
        cb.metric("Std (all)", f"{sub[picked].std():.3f}")
        by_group = sub.groupby("group")[picked].mean().reindex(["TD", "DD", "ASD"])
        fig = go.Figure(
            go.Bar(
                x=by_group.index,
                y=by_group.values,
                marker_color=[COLORS["TD"], COLORS["DD"], COLORS["ASD"]],
                text=[f"{value:.2f}" for value in by_group.values],
                textposition="outside",
            )
        )
        fig.update_layout(showlegend=False, yaxis_title=f"{picked} (mean)")
        st.plotly_chart(style_fig(fig, height=250), width="stretch", config=ST_CHART_CONFIG)
        st.markdown("</div>", unsafe_allow_html=True)

    section_label("Distribution")
    st.markdown(f"### `{picked}` by group")
    fig = px.violin(
        sub,
        x="group",
        y=picked,
        color="group",
        box=True,
        points="all",
        category_orders={"group": ["TD", "DD", "ASD"]},
        color_discrete_map=COLORS,
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(style_fig(fig, height=430), width="stretch", config=ST_CHART_CONFIG)


def page_eda(df: pd.DataFrame) -> None:
    hero(
        "Exploratory Data Analysis",
        "เปรียบเทียบ features ระหว่างกลุ่ม TD / DD / ASD แบบ interactive",
        tags=["Scatter", "Box plot", "Correlation heatmap", "Raw data"],
    )

    c1, c2 = st.columns(2)
    groups_sel = c1.multiselect(
        "Groups",
        options=["TD", "DD", "ASD"],
        default=["TD", "DD", "ASD"],
    )
    corpora_sel = c2.multiselect(
        "Corpora",
        options=sorted(df["corpus"].unique()),
        default=sorted(df["corpus"].unique()),
    )
    filtered = df[df["group"].isin(groups_sel) & df["corpus"].isin(corpora_sel)]
    st.caption(f"Showing **{len(filtered)}** of {len(df)} rows after filter")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Scatter", "Box plot", "Correlation", "Raw data"]
    )

    with tab1:
        c1, c2 = st.columns(2)
        x_feat = c1.selectbox("X-axis", FEATURES, index=FEATURES.index("mlu"))
        y_feat = c2.selectbox("Y-axis", FEATURES, index=FEATURES.index("ttr"))
        fig = px.scatter(
            filtered,
            x=x_feat,
            y=y_feat,
            color="group",
            size="total_words",
            size_max=28,
            hover_data=["participant_id", "corpus", "age_months"],
            color_discrete_map=COLORS,
        )
        fig.update_traces(
            marker={"opacity": 0.8, "line": {"width": 1, "color": "white"}}
        )
        st.plotly_chart(
            style_fig(fig, height=520),
            width="stretch",
            config=ST_CHART_CONFIG,
        )

    with tab2:
        feature = st.selectbox(
            "Feature",
            FEATURES,
            index=FEATURES.index("mlu"),
            key="eda_dist_feat",
        )
        c1, c2 = st.columns(2)
        fig1 = px.violin(
            filtered,
            x="group",
            y=feature,
            color="group",
            box=True,
            points="all",
            category_orders={"group": ["TD", "DD", "ASD"]},
            color_discrete_map=COLORS,
        )
        fig1.update_layout(showlegend=False)
        c1.plotly_chart(
            style_fig(fig1, height=430),
            width="stretch",
            config=ST_CHART_CONFIG,
        )
        fig2 = px.box(
            filtered,
            x="group",
            y=feature,
            color="group",
            points="all",
            category_orders={"group": ["TD", "DD", "ASD"]},
            color_discrete_map=COLORS,
        )
        fig2.update_layout(showlegend=False)
        c2.plotly_chart(
            style_fig(fig2, height=430),
            width="stretch",
            config=ST_CHART_CONFIG,
        )

    with tab3:
        corr = filtered[FEATURES].corr(numeric_only=True).round(2)
        fig = px.imshow(
            corr,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="RdBu_r",
            zmin=-1,
            zmax=1,
        )
        st.plotly_chart(
            style_fig(fig, height=600),
            width="stretch",
            config=ST_CHART_CONFIG,
        )

    with tab4:
        st.dataframe(filtered, width="stretch", hide_index=True)


def page_screening(df: pd.DataFrame) -> None:
    hero(
        "Screening Tool",
        "กรอก language profile ของเด็ก -> AI ทำนายความเสี่ยง ASD",
        tags=[
            "Logistic Regression",
            "AUC 0.931",
            "Uncertainty band",
            "XAI",
            "Severity scoring",
        ],
    )

    model = train_screening_model(df)

    left, right = st.columns([1, 1.3])
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Child profile")
        with st.form("unified_screen_form"):
            c1, c2 = st.columns(2)
            age = c1.slider("Age (months)", 12.0, 120.0, 48.0, step=1.0)
            n_utt = c2.slider("Utterances (CHI)", 10, 1000, 180, step=10)

            c1, c2 = st.columns(2)
            n_words = c1.slider("Total words", 0, 5000, 400, step=20)
            ttr = c2.slider("TTR", 0.0, 1.0, 0.4, step=0.01)

            c1, c2 = st.columns(2)
            mlu = c1.slider("MLU (morph)", 0.0, 10.0, 2.5, step=0.1)
            mluw = c2.slider("MLU (words)", 0.0, 10.0, 2.3, step=0.1)

            c1, c2 = st.columns(2)
            unint = c1.slider("Unintelligible (xxx/yyy)", 0, 500, 10)
            unint_r = c2.slider("Unint. ratio", 0.0, 1.0, 0.05, step=0.01)

            c1, c2 = st.columns(2)
            zero = c1.slider("Zero vocal. (`0 .`)", 0, 500, 5)
            nonverb = c2.slider("Non-verbal (&=)", 0, 500, 8)

            c1, c2 = st.columns(2)
            q_ratio = c1.slider("Question ratio", 0.0, 1.0, 0.08, step=0.01)
            echo = c2.slider("Echolalia (count)", 0, 500, 3)
            echo_r = st.slider("Echolalia ratio", 0.0, 1.0, 0.02, step=0.01)

            checklist_answers: list[str] = []
            with st.expander("Parent concern checklist (optional)"):
                st.caption(
                    "รายการนี้เขียนขึ้นสำหรับ demo ไม่ใช่ M-CHAT-R/F. "
                    "ข้ามได้ — ระบบจะใช้แค่ speech features"
                )
                for i, (question, _concerning) in enumerate(PARENT_CHECKLIST_ITEMS):
                    ans = st.radio(
                        f"{i + 1}. {question}",
                        options=["", "yes", "no"],
                        format_func=lambda value: {
                            "": "- ไม่ตอบ -",
                            "yes": "ใช่",
                            "no": "ไม่",
                        }[value],
                        index=0,
                        horizontal=True,
                        key=f"unified_parent_checklist_{i}",
                    )
                    checklist_answers.append(ans)

            submitted = st.form_submit_button(
                "Predict risk",
                type="primary",
                width="stretch",
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Prediction")

        if submitted:
            x_row = np.array([[
                age,
                n_utt,
                mlu,
                mluw,
                ttr,
                n_words,
                unint,
                unint_r,
                zero,
                nonverb,
                q_ratio,
                echo,
                echo_r,
            ]])
            prob = float(model.predict_proba(x_row)[0, 1])
            pred, kind, color = classify_risk(prob)

            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=prob * 100,
                number={"suffix": "%", "font": {"size": 52, "color": color}},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1},
                    "bar": {"color": color, "thickness": 0.65},
                    "bgcolor": "#F8F9FC",
                    "borderwidth": 0,
                    "steps": [
                        {"range": [0, UNCERTAIN_LOW * 100], "color": "#ECFDF5"},
                        {
                            "range": [UNCERTAIN_LOW * 100, UNCERTAIN_HIGH * 100],
                            "color": "#FFF7ED",
                        },
                        {"range": [UNCERTAIN_HIGH * 100, 100], "color": "#FEE2E2"},
                    ],
                    "threshold": {
                        "line": {"color": color, "width": 5},
                        "thickness": 0.8,
                        "value": prob * 100,
                    },
                },
            ))
            fig.update_layout(
                template=PLOTLY_TEMPLATE,
                height=300,
                margin={"l": 20, "r": 20, "t": 10, "b": 10},
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, width="stretch", config=ST_CHART_CONFIG)

            info_box(f"**{pred}** · ASD probability = {prob:.1%}", kind=kind)
            st.caption(
                f"Uncertain band = [{UNCERTAIN_LOW:.0%}, {UNCERTAIN_HIGH:.0%}) — "
                "predictions inside this range are reported as indeterminate."
            )
            info_box(
                "Research prototype — not for clinical use. "
                f"Trained/evaluated on {len(df)} TalkBank/ASDBank rows; "
                "not externally validated in Thai clinical cohorts.",
                kind="warn",
            )

            sev = compute_severity(model, df, x_row)
            st.markdown("#### Graded severity scores (0-10)")
            score_cols = st.columns(3)

            def _sev_color(value: float, reverse: bool = False) -> str:
                if reverse:
                    if value >= 6.5:
                        return COLORS["TD"]
                    if value >= 3.5:
                        return COLORS["DD"]
                    return COLORS["ASD"]
                if value >= 6.5:
                    return COLORS["ASD"]
                if value >= 3.5:
                    return COLORS["DD"]
                return COLORS["TD"]

            def _score_card(col, label: str, value: float, score_color: str, hint: str) -> None:
                col.markdown(
                    f"""<div class="card" style="text-align:center;padding:1rem">
                        <div style="font-size:0.75rem;color:#6C757D;
                                    text-transform:uppercase;letter-spacing:.06em">{label}</div>
                        <div style="font-size:2.4rem;font-weight:800;color:{score_color};
                                    line-height:1">{value:.1f}</div>
                        <div style="font-size:0.75rem;color:#6B7280;margin-top:.4rem">{hint}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

            _score_card(
                score_cols[0],
                "ASD severity",
                sev["severity_overall"],
                _sev_color(sev["severity_overall"]),
                "0 = no risk · 10 = highest risk",
            )
            _score_card(
                score_cols[1],
                "Communication strength",
                sev["communication_strength"],
                _sev_color(sev["communication_strength"], reverse=True),
                "↑ MLU, TTR, words, questions",
            )
            _score_card(
                score_cols[2],
                "ASD-marker burden",
                sev["marker_burden"],
                _sev_color(sev["marker_burden"]),
                "↑ echolalia, unintelligible, 0-vocal",
            )

            n_answered = sum(1 for answer in checklist_answers if answer)
            if n_answered >= 5:
                n_concerning, checklist_score = parent_checklist_severity(checklist_answers)
                combined = fuse_severity(
                    sev["severity_overall"],
                    checklist_score,
                    w_speech=0.5,
                )
                st.markdown("#### Multi-modal severity")
                mc1, mc2, mc3 = st.columns(3)
                _score_card(
                    mc1,
                    "Speech-only",
                    sev["severity_overall"],
                    _sev_color(sev["severity_overall"]),
                    "from CHAT features",
                )
                _score_card(
                    mc2,
                    "Parent concern",
                    float(checklist_score),
                    _sev_color(float(checklist_score)),
                    f"{n_concerning}/10 concerning answers",
                )
                _score_card(
                    mc3,
                    "Combined",
                    combined,
                    _sev_color(combined),
                    "late-fusion average",
                )
            elif n_answered > 0:
                info_box(
                    f"ตอบ parent checklist เพียง {n_answered}/10 ข้อ — "
                    "ต้องตอบอย่างน้อย 5 ข้อจึงจะคำนวณ multi-modal score",
                    kind="warn",
                )

            st.markdown("#### Why did the AI predict this?")
            imp = model.named_steps["imp"]
            sc = model.named_steps["sc"]
            clf = model.named_steps["clf"]
            x_imp = imp.transform(x_row)
            x_scaled = sc.transform(x_imp)[0]
            contribs = clf.coef_[0] * x_scaled
            intercept = float(clf.intercept_[0])

            order = np.argsort(np.abs(contribs))
            f_sorted = [FEATURES[i] for i in order]
            c_sorted = contribs[order]
            x_sorted = x_row[0][order]
            shap_colors = [COLORS["ASD"] if value > 0 else COLORS["TD"] for value in c_sorted]
            hover = [
                f"{feature}: input={raw_value:.2f}<br>contribution={contrib:+.3f}"
                for feature, raw_value, contrib in zip(f_sorted, x_sorted, c_sorted)
            ]
            shap_fig = go.Figure(go.Bar(
                x=c_sorted,
                y=f_sorted,
                orientation="h",
                marker_color=shap_colors,
                text=[f"{value:+.2f}" for value in c_sorted],
                textposition="outside",
                hovertext=hover,
                hoverinfo="text",
            ))
            shap_fig.update_layout(
                xaxis_title="Contribution to log-odds (ASD)",
                yaxis_title="",
                height=380,
            )
            st.plotly_chart(
                style_fig(shap_fig),
                width="stretch",
                config=ST_CHART_CONFIG,
            )
            logit = intercept + float(contribs.sum())
            st.caption(
                f"intercept = {intercept:+.2f} · "
                f"sum(contributions) = {contribs.sum():+.2f} · "
                f"logit = {logit:+.2f} -> P(ASD) = {prob:.1%}"
            )
        else:
            st.markdown(
                '<div class="empty-note">Fill in the sliders and click '
                '<strong>Predict risk</strong> to see the AI prediction.</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    section_label("Model interpretation")
    st.markdown("### Which features drive the prediction?")
    coef = model.named_steps["clf"].coef_[0]
    coef_df = pd.DataFrame({"feature": FEATURES, "coefficient": coef.round(3)})
    coef_df = coef_df.reindex(
        coef_df["coefficient"].abs().sort_values(ascending=True).index
    )
    colors = [COLORS["ASD"] if value > 0 else COLORS["TD"] for value in coef_df["coefficient"]]
    fig = go.Figure(go.Bar(
        x=coef_df["coefficient"],
        y=coef_df["feature"],
        orientation="h",
        marker_color=colors,
        text=coef_df["coefficient"].round(2),
        textposition="outside",
    ))
    fig.update_layout(xaxis_title="Coefficient (standardized)", yaxis_title="")
    st.plotly_chart(style_fig(fig, height=420), width="stretch", config=ST_CHART_CONFIG)


def page_audio(df: pd.DataFrame) -> None:
    hero(
        "Audio Assessment",
        "อัปโหลดเสียง session ของเด็ก -> Whisper ASR -> CHAT transcript -> features -> ASD risk",
        tags=["Whisper ASR", "CHAT", "Feature extraction", "Screening result"],
    )

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Upload session audio")
    st.caption(
        "รองรับ `.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`. "
        "แนะนำบันทึกในห้องเงียบ 15-30 นาที โดยมีเด็ก + ผู้ใหญ่ 1 คน"
    )

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    audio_file = c1.file_uploader(
        "Audio file",
        type=["wav", "mp3", "m4a", "flac", "ogg"],
        label_visibility="collapsed",
    )
    model_size = c2.selectbox(
        "Whisper model",
        ["tiny", "base", "small", "medium"],
        index=2,
    )
    strategy = c3.selectbox(
        "Language",
        ["auto", "english", "thai", "dual_pass", "thai_specialized"],
        index=0,
        format_func=lambda strategy_name: {
            "auto": "Auto-detect",
            "english": "English only",
            "thai": "Thai only",
            "dual_pass": "Dual-pass EN+TH",
            "thai_specialized": "Thai-specialized",
        }[strategy_name],
    )
    c4.markdown('<div style="padding-top:1.6rem"></div>', unsafe_allow_html=True)
    run_btn = c4.button(
        "Run pipeline",
        width="stretch",
        type="primary",
        disabled=audio_file is None,
    )

    with st.expander("Child metadata (optional — kept in CHAT header)"):
        mc1, mc2, mc3, mc4 = st.columns(4)
        child_id = mc1.text_input("Child ID", value="CHI001")
        child_age = mc2.number_input("Age (months)", 0.0, 120.0, 48.0, step=1.0)
        child_sex = mc3.selectbox("Sex", ["", "male", "female"], index=0)
        child_group = mc4.selectbox("Group", ["ASD", "TD", "DD"], index=0)

    with st.expander("Speaker enrollment (optional)"):
        st.caption(
            "อัปไฟล์เสียงเด็กสั้น ๆ 5-10 วินาที เพื่อช่วยจับคู่ cluster ที่เป็นเด็ก"
        )
        enrollment_file = st.file_uploader(
            "Child reference audio",
            type=["wav", "mp3", "m4a", "flac", "ogg"],
            label_visibility="collapsed",
            key="unified_enrollment_audio",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    audio_signature = None
    if audio_file is not None:
        audio_signature = (audio_file.name, getattr(audio_file, "size", 0), model_size, strategy)
    cached_sig = st.session_state.get("unified_audio_pipe_sig")
    cached_result = st.session_state.get("unified_audio_pipe_result")
    cached_tmp_audio = st.session_state.get("unified_audio_pipe_tmp_audio")
    cached_tmp_cha = st.session_state.get("unified_audio_pipe_tmp_cha")
    cached_meta = st.session_state.get("unified_audio_pipe_meta", {})

    have_cached = (
        cached_sig == audio_signature
        and cached_result is not None
        and cached_tmp_cha is not None
        and Path(cached_tmp_cha).exists()
    )

    if not run_btn and not have_cached:
        st.info(
            "อัปโหลด audio แล้วกด Run pipeline เพื่อถอดเสียง สร้าง CHAT transcript "
            "สกัด 13 features และทำนาย ASD risk"
        )
        return
    if audio_file is None and not have_cached:
        return

    if run_btn or not have_cached:
        with st.spinner(
            f"กำลังประมวลผลเสียงด้วย Whisper-{model_size}... "
            "(อาจใช้เวลา 1-3 นาที ขึ้นกับความยาวไฟล์)"
        ):
            try:
                suffix = Path(audio_file.name).suffix or ".wav"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
                    tf.write(audio_file.read())
                    tmp_audio = Path(tf.name)

                tmp_cha = tmp_audio.with_suffix(".cha")
                tmp_enrollment = None
                if enrollment_file is not None:
                    en_suffix = Path(enrollment_file.name).suffix or ".wav"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=en_suffix) as ef:
                        ef.write(enrollment_file.read())
                        tmp_enrollment = Path(ef.name)

                from src.audio_pipeline import audio_to_cha

                result = audio_to_cha(
                    tmp_audio,
                    output_path=tmp_cha,
                    model_size=model_size,
                    strategy=strategy,
                    prefer_pyannote=False,
                    enrollment_audio_path=tmp_enrollment,
                    child_id=child_id,
                    child_age_months=child_age if child_age > 0 else None,
                    child_sex=child_sex or None,
                    child_group=child_group,
                )
            except ImportError as exc:
                st.error(
                    f"Audio pipeline dependencies missing.\n\n{exc}\n\n"
                    "Install with: `pip install faster-whisper librosa soundfile`"
                )
                return
            except Exception as exc:  # noqa: BLE001
                st.error(f"Pipeline failed: {exc}")
                return

        st.session_state["unified_audio_pipe_sig"] = audio_signature
        st.session_state["unified_audio_pipe_result"] = result
        st.session_state["unified_audio_pipe_tmp_audio"] = tmp_audio
        st.session_state["unified_audio_pipe_tmp_cha"] = tmp_cha
        st.session_state["unified_audio_pipe_meta"] = {
            "child_id": child_id,
            "child_age": child_age,
            "child_sex": child_sex,
            "child_group": child_group,
        }
    else:
        result = cached_result
        tmp_audio = Path(cached_tmp_audio)
        tmp_cha = Path(cached_tmp_cha)
        child_id = cached_meta.get("child_id", child_id)
        child_age = cached_meta.get("child_age", child_age)
        child_sex = cached_meta.get("child_sex", child_sex)
        child_group = cached_meta.get("child_group", child_group)

    section_label("Pipeline output")
    c1, c2, c3, c4 = st.columns(4)
    metric_card(c1, "Duration", f"{result.total_duration_sec:.0f} s", "audio length")
    metric_card(c2, "Child utterances", f"{result.n_child_utterances}", "*CHI: lines", flavor="accent")
    metric_card(c3, "Adult utterances", f"{result.n_adult_utterances}", "*MOT: lines", flavor="td")
    metric_card(
        c4,
        "Total segments",
        f"{result.n_child_utterances + result.n_adult_utterances}",
        "Whisper segments",
    )

    if result.n_child_utterances == 0:
        st.warning(
            "ไม่พบ child speech — ลองใช้ model ใหญ่ขึ้นหรือตรวจสอบว่า audio มีเสียงเด็กจริง"
        )

    validation = result.validation
    if validation is not None:
        if validation.skipped:
            st.caption(f"CHATTER: skipped ({validation.skip_reason})")
        elif validation.ok:
            st.caption(f"CHATTER: passed (auto-fixed {validation.fixed_count})")
        else:
            st.caption(
                f"CHATTER: {validation.n_errors} error(s), "
                f"{validation.n_warnings} warning(s) (auto-fixed {validation.fixed_count})"
            )

    tab_pred, tab_cha, tab_segments = st.tabs(
        ["Features + Prediction", "CHAT transcript", "Segments"]
    )

    with tab_pred:
        try:
            from src.data_loader import _extract_features

            feats = _extract_features(tmp_cha)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Feature extraction failed: {exc}")
            feats = None

        if feats is None:
            st.error("ไม่สามารถสกัด features ได้")
        else:
            feat_row = {feature: feats.get(feature) for feature in FEATURES}
            feat_row["age_months"] = child_age if child_age > 0 else feats.get("age_months")
            feat_df = pd.DataFrame([feat_row])
            st.markdown("#### Extracted features")
            st.dataframe(feat_df, width="stretch", hide_index=True)

            model = train_screening_model(df)
            try:
                x_row = feat_df[FEATURES].values
                prob_asd = float(model.predict_proba(x_row)[0, 1])
                _label, kind, color = classify_risk(prob_asd)
                if prob_asd >= UNCERTAIN_HIGH:
                    pred_label = "ASD"
                elif prob_asd < UNCERTAIN_LOW:
                    pred_label = "non-ASD"
                else:
                    pred_label = "UNCERTAIN"
                st.markdown(
                    f"""<div class="card" style="text-align:center;padding:1.5rem">
                        <div style="color:#6C757D;font-size:0.85rem;
                                    text-transform:uppercase;letter-spacing:.08em">
                            Prediction
                        </div>
                        <div style="font-size:2.2rem;font-weight:800;color:{color};
                                    margin:.3rem 0">
                            {pred_label}
                        </div>
                        <div style="font-size:1.1rem;color:#4B5563">
                            P(ASD) = <b>{prob_asd:.3f}</b>
                        </div>
                        <div style="color:#6C757D;font-size:0.8rem;margin-top:.8rem">
                            Screening support only — not diagnostic.
                        </div>
                       </div>""",
                    unsafe_allow_html=True,
                )
                info_box(_label, kind=kind)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Prediction failed: {exc}")

            st.download_button(
                "Download features (CSV)",
                data=feat_df.to_csv(index=False).encode("utf-8"),
                file_name=f"{child_id}_features.csv",
                mime="text/csv",
            )

    with tab_cha:
        st.code(result.chat_text, language="text")
        st.download_button(
            "Download .cha",
            data=result.chat_text.encode("utf-8"),
            file_name=f"{child_id}.cha",
            mime="text/plain",
        )

    with tab_segments:
        seg_rows = []
        for utterance in result.utterances:
            min_conf = min(
                (word.probability for word in utterance.words),
                default=1.0,
            ) if utterance.words else 1.0
            seg_rows.append({
                "start (s)": round(utterance.start, 2),
                "end (s)": round(utterance.end, 2),
                "speaker": utterance.speaker or "MOT",
                "lang": (utterance.language or "").lower(),
                "min_conf": round(min_conf, 2),
                "n_words": len(utterance.words),
                "text": utterance.text,
            })
        st.dataframe(pd.DataFrame(seg_rows), width="stretch", hide_index=True)

    if st.button("Delete cached audio/transcript for this session", type="secondary"):
        for key in ("unified_audio_pipe_tmp_audio", "unified_audio_pipe_tmp_cha"):
            cached_path = st.session_state.get(key)
            if cached_path:
                Path(cached_path).unlink(missing_ok=True)
        for key in (
            "unified_audio_pipe_sig",
            "unified_audio_pipe_result",
            "unified_audio_pipe_tmp_audio",
            "unified_audio_pipe_tmp_cha",
            "unified_audio_pipe_meta",
        ):
            st.session_state.pop(key, None)
        st.success("Deleted cached temporary audio/transcript files for this session.")


def page_trust() -> None:
    hero(
        "Model Trust Dashboard",
        "ดู performance, threshold behavior, calibration และ transparency notes จาก cross-validation",
        tags=["Leaderboard", "Threshold", "Calibration", "Decision curve", "Model card"],
    )

    results = load_metric_csv("classification_results.csv")
    thresholds = load_metric_csv("threshold_metrics.csv")
    calibration = load_metric_csv("calibration_bins.csv")
    decision = load_metric_csv("decision_curve.csv")
    subgroups = load_metric_csv("subgroup_performance.csv")
    loco = load_metric_csv("leave_one_corpus_out.csv")
    predictions = load_metric_csv("binary_oof_predictions.csv")
    model_card = load_model_card()

    left, right = st.columns([1.45, 0.85])
    with left:
        section_label("Leaderboard")
        st.markdown("### Binary model performance")
        if results.empty:
            info_box("Metrics not generated yet. Run `python src/classifier.py`.", kind="warn")
        else:
            metric = st.selectbox(
                "Rank by",
                ["roc_auc", "sensitivity", "specificity", "ppv", "npv", "brier_score"],
                format_func=lambda value: value.replace("_", " ").upper(),
            )
            binary = results[results["task"] == "binary"].copy()
            ascending = metric == "brier_score"
            binary = binary.sort_values(metric, ascending=ascending, na_position="last")
            for index, row in binary.iterrows():
                flavor = "td" if index == binary.index[0] else ""
                metric_card(
                    st.container(),
                    str(row["model"]),
                    f"{float(row[metric]):.3f}" if pd.notna(row[metric]) else "n/a",
                    (
                        f"sens {row.get('sensitivity', np.nan):.2f} · "
                        f"spec {row.get('specificity', np.nan):.2f} · "
                        f"NPV {row.get('npv', np.nan):.2f}"
                    ),
                    flavor=flavor,
                )

    with right:
        section_label("Model card")
        st.markdown("### Transparency")
        meta = model_card.get("training_metadata", {})
        st.markdown(
            f"""<div class="card">
                <p><b>Version</b><br>{model_card.get("model_version", "runtime")}</p>
                <p><b>Rows</b><br>{meta.get("n_rows", "n/a")}</p>
                <p><b>Data hash</b><br>{meta.get("data_hash", "not generated")}</p>
                <p><b>Intended use</b><br>{model_card.get("intended_use", "Screening support demo.")}</p>
                <p><b>Not intended</b><br>{model_card.get("not_intended_use", "Autonomous diagnosis.")}</p>
            </div>""",
            unsafe_allow_html=True,
        )

    section_label("Threshold playground")
    st.markdown("### Live confusion matrix")
    if thresholds.empty:
        info_box("Threshold metrics missing. Run `python src/classifier.py`.", kind="warn")
    else:
        threshold_value = st.slider("Referral threshold", 0.05, 0.95, 0.50, step=0.05)
        row = thresholds.iloc[(thresholds["threshold"] - threshold_value).abs().argsort()[:1]].iloc[0]
        c1, c2 = st.columns([1.1, 0.9])
        with c1:
            cols = st.columns(4)
            metric_card(cols[0], "Sensitivity", f"{row['sensitivity']:.2f}", flavor="td")
            metric_card(cols[1], "Specificity", f"{row['specificity']:.2f}", flavor="accent")
            metric_card(cols[2], "PPV", f"{row['ppv']:.2f}", flavor="dd")
            metric_card(cols[3], "NPV", f"{row['npv']:.2f}", flavor="asd")
            st.caption(f"Nearest generated threshold: {row['threshold']:.2f}")
        with c2:
            matrix = pd.DataFrame(
                [[int(row["tn"]), int(row["fp"])], [int(row["fn"]), int(row["tp"])]],
                index=["Actual non-ASD", "Actual ASD"],
                columns=["Pred non-ASD", "Pred ASD"],
            )
            st.dataframe(matrix, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        section_label("Calibration")
        st.markdown("### Predicted vs observed")
        if calibration.empty:
            info_box("Calibration bins missing. Run `python src/classifier.py`.", kind="warn")
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=calibration["predicted_mean"],
                y=calibration["observed_rate"],
                mode="lines+markers",
                name="Observed",
                line={"color": COLORS["primary"], "width": 3},
            ))
            fig.add_trace(go.Scatter(
                x=[0, 1],
                y=[0, 1],
                mode="lines",
                name="Perfect calibration",
                line={"color": COLORS["muted"], "dash": "dash"},
            ))
            fig.update_layout(xaxis_title="Predicted probability", yaxis_title="Observed ASD rate")
            st.plotly_chart(style_fig(fig, height=360), width="stretch", config=ST_CHART_CONFIG)
            if not results.empty:
                logreg = results[(results["task"] == "binary") & (results["model"] == "LogReg")]
                if not logreg.empty and pd.notna(logreg.iloc[0].get("brier_score")):
                    info_box(f"**Brier score:** {float(logreg.iloc[0]['brier_score']):.3f} · lower is better calibrated")

    with c2:
        section_label("Decision curve")
        st.markdown("### Net benefit")
        if decision.empty:
            info_box("Decision curve missing. Run `python src/classifier.py`.", kind="warn")
        else:
            long_decision = decision.melt(
                id_vars="threshold",
                value_vars=["model_net_benefit", "treat_all_net_benefit", "treat_none_net_benefit"],
                var_name="strategy",
                value_name="net_benefit",
            )
            fig = px.line(
                long_decision,
                x="threshold",
                y="net_benefit",
                color="strategy",
                markers=True,
                color_discrete_sequence=[COLORS["primary"], COLORS["DD"], COLORS["ASD"]],
            )
            st.plotly_chart(style_fig(fig, height=360), width="stretch", config=ST_CHART_CONFIG)

    section_label("Uncertainty and robustness")
    c1, c2 = st.columns([0.8, 1.2])
    with c1:
        st.markdown("### Uncertainty zone")
        if predictions.empty or "uncertainty_zone" not in predictions.columns:
            info_box("OOF prediction zones missing. Run `python src/classifier.py`.", kind="warn")
        else:
            zone_counts = predictions["uncertainty_zone"].value_counts().reset_index()
            zone_counts.columns = ["zone", "n"]
            fig = px.pie(
                zone_counts,
                names="zone",
                values="n",
                color="zone",
                color_discrete_map={"low": COLORS["TD"], "uncertain": COLORS["DD"], "high": COLORS["ASD"]},
                hole=0.55,
            )
            st.plotly_chart(style_fig(fig, height=330), width="stretch", config=ST_CHART_CONFIG)
    with c2:
        st.markdown("### Subgroup table")
        if subgroups.empty:
            info_box("Subgroup performance missing. Run `python src/classifier.py`.", kind="warn")
        else:
            st.dataframe(subgroups, width="stretch", hide_index=True)

    section_label("Stress test")
    st.markdown("### Leave-one-corpus-out")
    if loco.empty:
        info_box("LOCO metrics missing. Run `python src/classifier.py`.", kind="warn")
    else:
        st.dataframe(loco, width="stretch", hide_index=True)

    section_label("Model card JSON")
    st.json(model_card)


def page_progress(longitudinal: pd.DataFrame) -> None:
    hero(
        "Progress Tracker",
        "ติดตามพัฒนาการของเด็ก ASD ตลอดหลาย sessions ของการบำบัด",
        tags=[
            "Longitudinal tracking",
            f"{longitudinal['child'].nunique()} children",
            f"{len(longitudinal)} sessions",
            "First vs last",
        ],
    )

    children = sorted(longitudinal["child"].unique())
    scored = _compute_composite(longitudinal)

    section_label("Children")
    st.markdown("### Per-child summary")
    cols = st.columns(min(len(children), 4))
    for index, child in enumerate(children):
        col = cols[index % len(cols)]
        group = scored[scored["child"] == child].sort_values("session_order")
        first = group["composite_score"].iloc[0]
        last = group["composite_score"].iloc[-1]
        delta = last - first
        metric_card(
            col,
            child,
            f"{last:+.2f}",
            f"delta {delta:+.2f} over {len(group)} sessions",
            flavor="td" if delta > 0 else "asd",
        )

    tab1, tab2, tab3 = st.tabs(["Feature trajectories", "Composite score", "First vs last"])

    with tab1:
        c1, c2 = st.columns([1.1, 2.4])
        picked_children = c1.multiselect("Children", children, default=children)
        features_for_plot = [
            "mlu",
            "mluw",
            "ttr",
            "total_words",
            "unintelligible_ratio",
            "zero_vocalization_count",
            "total_utterances",
        ]
        feature = c1.selectbox("Feature", features_for_plot, index=0)
        subset = longitudinal[longitudinal["child"].isin(picked_children)]
        fig = px.line(
            subset,
            x="session_order",
            y=feature,
            color="child",
            markers=True,
            line_shape="spline",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(line_width=3, marker_size=10)
        fig.update_layout(xaxis_title="Session", yaxis_title=feature)
        c2.plotly_chart(style_fig(fig, height=440), width="stretch", config=ST_CHART_CONFIG)

    with tab2:
        picked_children = st.multiselect("Children", children, default=children, key="unified_comp_children")
        subset = scored[scored["child"].isin(picked_children)]
        fig = px.line(
            subset,
            x="session_order",
            y="composite_score",
            color="child",
            markers=True,
            line_shape="spline",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(line_width=3, marker_size=12)
        fig.add_hline(
            y=0,
            line_dash="dash",
            line_color=COLORS["muted"],
            annotation_text="cohort mean",
            annotation_position="bottom right",
        )
        fig.update_layout(
            xaxis_title="Session order",
            yaxis_title="Composite score (higher = better)",
        )
        st.plotly_chart(style_fig(fig, height=480), width="stretch", config=ST_CHART_CONFIG)
        info_box(
            "**Composite score** คือค่าเฉลี่ยของ 7 features ที่ z-scored แล้วปรับทิศทาง "
            "(สูง=ดี เช่น MLU/TTR/words; ต่ำ=ดี เช่น unintelligible/zero vocalization)."
        )

    with tab3:
        features_for_table = [
            "mlu",
            "mluw",
            "ttr",
            "total_words",
            "unintelligible_ratio",
            "zero_vocalization_count",
            "composite_score",
        ]
        rows = []
        for child, group in scored.groupby("child"):
            group = group.sort_values("session_order")
            for feature in features_for_table:
                delta = group[feature].iloc[-1] - group[feature].iloc[0]
                lower_better = feature in ("unintelligible_ratio", "zero_vocalization_count")
                improved = (delta < 0) if lower_better else (delta > 0)
                rows.append({
                    "child": child,
                    "feature": feature,
                    "first": round(group[feature].iloc[0], 3),
                    "last": round(group[feature].iloc[-1], 3),
                    "delta": round(delta, 3),
                    "improved": "yes" if improved else "no",
                })
        summary = pd.DataFrame(rows)
        st.dataframe(summary, width="stretch", hide_index=True)
        improved_rate = (summary["improved"] == "yes").mean()
        info_box(f"Improvement flags marked yes for {improved_rate:.0%} of child-feature comparisons.")


def page_research() -> None:
    hero(
        "Research Evidence and Safety",
        "หลักฐานที่ใช้วางกรอบงาน พร้อม safety, ethics และ limitations ที่ควรพูดให้ชัด",
        tags=["Literature", "Safety", "Ethics", "Limitations", "Next steps"],
    )

    lit_path = LITERATURE_DIR / "consensus_papers_2026-04-26.csv"
    if lit_path.exists():
        literature = pd.read_csv(lit_path, encoding="utf-8-sig").head(8)
    else:
        literature = pd.DataFrame([
            {
                "Title": "TRIPOD+AI / DECIDE-AI reporting",
                "Takeaway": "Report model purpose, data flow, validation, calibration, and human oversight.",
                "Year": "Guidance",
                "Journal": "Clinical AI reporting",
            },
            {
                "Title": "Megerian et al. AI-based ASD device",
                "Takeaway": "Indeterminate outputs can be a risk-control mechanism for clinical decision support.",
                "Year": "2022",
                "Journal": "NPJ Digital Medicine",
            },
        ])

    section_label("Literature cards")
    cols = st.columns(2)
    for index, row in literature.iterrows():
        col = cols[index % 2]
        col.markdown(
            f"""<div class="card">
                <span class="chip chip-td">{row.get("Year", "n/a")}</span>
                <span class="chip chip-dd">{row.get("Journal", "Research")}</span>
                <h3>{row.get("Title", "Untitled")}</h3>
                <p>{row.get("Takeaway", "No takeaway available.")}</p>
                <p style="font-size:.82rem;color:#6C757D">{row.get("Authors", "")}</p>
            </div>""",
            unsafe_allow_html=True,
        )

    section_label("Clinical safety")
    c1, c2, c3 = st.columns(3)
    c1.markdown(
        """<div class="card"><h3>Screening only</h3>
        <p>ใช้เป็น decision-support prototype ไม่ใช่ diagnostic device หรือ replacement for clinician assessment.</p></div>""",
        unsafe_allow_html=True,
    )
    c2.markdown(
        """<div class="card"><h3>Human in the loop</h3>
        <p>ผล prediction ต้องถูกอ่านพร้อม transcript, audio quality, developmental history และ clinical judgment.</p></div>""",
        unsafe_allow_html=True,
    )
    c3.markdown(
        f"""<div class="card"><h3>Uncertainty band</h3>
        <p>ช่วง {UNCERTAIN_LOW:.0%}-{UNCERTAIN_HIGH:.0%} รายงานเป็น uncertain เพื่อเลี่ยง over-confident screening.</p></div>""",
        unsafe_allow_html=True,
    )

    section_label("Ethics and limitations")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Ethics")
        st.markdown(
            """
            - Child audio and transcripts are sensitive data.
            - Parent-facing language must avoid diagnostic claims.
            - Model output should explain uncertainty and next-step referral, not label a child.
            - Uploaded audio should be temporary and removable after review.
            """
        )
    with c2:
        st.markdown("### Limitations")
        st.markdown(
            """
            - Dataset is small and mostly English-language CHAT.
            - Thai clinical validation has not been completed.
            - ASR and diarization can shift features, especially for child speech.
            - Cross-corpus performance can reflect corpus artifacts.
            """
        )

    section_label("Next steps")
    st.markdown("### What should happen before real clinical use")
    st.dataframe(
        pd.DataFrame([
            {"track": "Transcript QA", "next_step": "Benchmark WER/CER and feature drift on child speech audio."},
            {"track": "Thai validation", "next_step": "Collect Thai clinical samples with consent and external labels."},
            {"track": "Reporting", "next_step": "Prepare model card, dataset card, and clinician-facing limitations."},
            {"track": "Workflow", "next_step": "Add therapist progress report export and human review checklist."},
        ]),
        width="stretch",
        hide_index=True,
    )


def page_presentation() -> None:
    hide_sidebar = st.toggle("Presentation mode: hide sidebar", value=False)
    if hide_sidebar:
        st.markdown(
            """
            <style>
            section[data-testid="stSidebar"] { display: none; }
            .block-container { max-width: 1500px; padding-left: 3rem; padding-right: 3rem; }
            header[data-testid="stHeader"] { display: none; }
            </style>
            """,
            unsafe_allow_html=True,
        )

    steps = [
        {
            "title": "1. Problem",
            "subtitle": "ASD screening and progress tracking are slow, subjective, and hard to repeat.",
            "talk": "Position this as screening support and therapy progress tracking, not diagnosis.",
            "proof": "Parent demo, clinician dashboard, uncertainty band, and longitudinal progress pages.",
        },
        {
            "title": "2. Data",
            "subtitle": "TalkBank/ASDBank CHAT transcripts become child-level language features.",
            "talk": "Explain corpus mix, labels, and why transcripts are useful for reproducible analysis.",
            "proof": "`combined_features.csv`: classification; `longitudinal_features.csv`: progress.",
        },
        {
            "title": "3. Features",
            "subtitle": "13 interpretable speech-language markers clinicians can inspect.",
            "talk": "MLU, TTR, total words, unintelligible ratio, zero vocalization, question ratio, echolalia.",
            "proof": "Feature page shows definitions and live group means.",
        },
        {
            "title": "4. Model Trust",
            "subtitle": "Do not present only AUC; show calibration, threshold behavior, and robustness.",
            "talk": "Use the trust page to explain sensitivity/specificity tradeoffs and uncertainty.",
            "proof": "LogReg binary AUC around 0.93 with threshold and model-card transparency.",
        },
        {
            "title": "5. Audio Pipeline",
            "subtitle": "Audio can flow into Whisper, CHAT, features, and a screening result.",
            "talk": "Stress that audio-derived predictions need transcript QA before interpretation.",
            "proof": "Audio page produces CHAT preview, features, prediction, and download.",
        },
        {
            "title": "6. Progress",
            "subtitle": "Longitudinal sessions show whether therapy-linked language markers improve.",
            "talk": "Use first-vs-last deltas and composite trajectories as therapist-facing evidence.",
            "proof": "Progress page compares MLU/TTR/words and lower-is-better marker reductions.",
        },
        {
            "title": "7. Safety",
            "subtitle": "The safest claim is decision support with human oversight.",
            "talk": "Name limitations: small dataset, English-heavy transcripts, Thai validation needed.",
            "proof": "Research page documents evidence, ethics, limitations, and next steps.",
        },
    ]

    hero(
        "Advisor Demo Narrative",
        "Step-through walkthrough for presenting the project clearly in 3-5 minutes",
        tags=["Presentation mode", "Advisor demo", "Human-in-the-loop", "Safety-first"],
    )

    step_index = st.slider("Narrative step", 1, len(steps), 1) - 1
    step = steps[step_index]

    st.markdown(
        f"""<div class="card" style="padding:2rem">
            <span class="section-label">{step["title"]}</span>
            <h1 style="margin-top:.5rem">{step["subtitle"]}</h1>
            <p style="font-size:1.12rem;color:#4B5563"><b>Say:</b> {step["talk"]}</p>
            <p style="font-size:1rem;color:#6C757D"><b>Show:</b> {step["proof"]}</p>
        </div>""",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    metric_card(c1, "Classification rows", "122", "cross-sectional children")
    metric_card(c2, "Longitudinal sessions", "87", "therapy/progress rows", flavor="accent")
    metric_card(c3, "Feature schema", "13", "interpretable markers", flavor="td")
    metric_card(c4, "Binary AUC", "0.93", "LogReg validation", flavor="asd")

    section_label("Full demo flow")
    st.markdown("### What to click during the presentation")
    st.dataframe(
        pd.DataFrame([
            {"minute": "0:00", "page": "Dashboard", "message": "Project scope, dataset, and headline metrics."},
            {"minute": "0:45", "page": "Features", "message": "Why the 13 markers are clinically readable."},
            {"minute": "1:30", "page": "Screening", "message": "Prediction, uncertainty, XAI, and severity scoring."},
            {"minute": "2:20", "page": "Model Trust", "message": "Calibration, thresholds, robustness, and model card."},
            {"minute": "3:10", "page": "Audio", "message": "End-to-end pipeline with CHAT preview and privacy note."},
            {"minute": "4:00", "page": "Progress", "message": "First-vs-last trajectories for therapy tracking."},
            {"minute": "4:40", "page": "Reports", "message": "Research evidence, limitations, and next steps."},
        ]),
        width="stretch",
        hide_index=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="ASD Assessment Unified Dashboard",
        page_icon="A",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    df = load_combined()
    longitudinal = load_longitudinal()
    page = sidebar_nav()

    if page == "overview":
        page_overview(df, longitudinal)
    elif page == "dataset":
        page_dataset(df)
    elif page == "features":
        page_features(df)
    elif page == "eda":
        page_eda(df)
    elif page == "screening":
        page_screening(df)
    elif page == "trust":
        page_trust()
    elif page == "audio":
        page_audio(df)
    elif page == "reports":
        page_research()
    elif page == "progress":
        page_progress(longitudinal)
    elif page == "atlas":
        page_presentation()


if __name__ == "__main__":
    main()
