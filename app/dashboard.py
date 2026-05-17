"""
Interactive dashboard for the ASD-project.

Run:
    streamlit run app/dashboard.py
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

# Make `src` importable (audio pipeline + data loader helpers)
_PROJECT_ROOT_IMPORT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT_IMPORT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT_IMPORT))

from src.feature_schema import (  # noqa: E402
    FEATURES,
    MARKER_FEATURES,
    POSITIVE_FEATURES,
    UNCERTAIN_HIGH,
    UNCERTAIN_LOW,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts"

# Clinical / accessible palette
COLORS = {
    "TD":       "#2EC4B6",   # teal
    "DD":       "#FF9F1C",   # amber
    "ASD":      "#E71D36",   # coral red
    "primary":  "#4361EE",   # indigo
    "accent":   "#7209B7",   # violet
    "muted":    "#6C757D",
    "bg_card":  "#FFFFFF",
    "bg_soft":  "#F8F9FC",
    "text":     "#1F2937",
}

PLOTLY_TEMPLATE = "plotly_white"
st_chart_cfg = {"displayModeBar": False}

# Uncertainty band for binary screening output.
# Inspired by Megerian et al. (2022) — the FDA-cleared CADx device returns
# an "indeterminate" output when inputs are insufficiently granular.
# Probabilities inside [LOW, HIGH) are reported as Uncertain rather than
# committing to a binary decision the model is not confident enough to make.
def classify_risk(prob: float) -> tuple[str, str, str]:
    """Map P(ASD) to (label, kind, color).

    kind is one of {success, warn, danger} for info_box styling.
    """
    if prob >= UNCERTAIN_HIGH:
        return ("HIGH risk → recommend referral", "warn", COLORS["ASD"])
    if prob < UNCERTAIN_LOW:
        return ("LOW risk → likely typical", "success", COLORS["TD"])
    return ("UNCERTAIN → recommend further assessment", "warn", COLORS["DD"])


# ---------------------------------------------------------------------------
# Global CSS — polished look
# ---------------------------------------------------------------------------
CSS = f"""
<style>
/* ---------- page ---------- */
.stApp {{
    background:
        radial-gradient(1200px 600px at 0% 0%, #EEF2FF 0%, transparent 55%),
        radial-gradient(1000px 500px at 100% 0%, #F3E8FF 0%, transparent 60%),
        #F8F9FC;
}}
.block-container {{ padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1300px; }}

/* ---------- headings ---------- */
h1, h2, h3, h4 {{ color: {COLORS["text"]}; letter-spacing: -0.01em; }}
h1 {{ font-weight: 800; }}
h2 {{ margin-top: 1.8rem; font-weight: 700; }}
h3 {{ font-weight: 600; }}

/* ---------- hero ---------- */
.hero {{
    background: linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["accent"]} 100%);
    color: white;
    padding: 2rem 2.2rem;
    border-radius: 18px;
    margin-bottom: 1.2rem;
    box-shadow: 0 10px 30px rgba(67, 97, 238, 0.25);
}}
.hero h1 {{ color: #FFF; margin: 0 0 0.35rem 0; font-size: 2rem; font-weight: 800; }}
.hero .sub {{ color: rgba(255, 255, 255, 0.85); font-size: 1rem; }}
.hero .tags {{ margin-top: 0.9rem; display: flex; gap: 0.4rem; flex-wrap: wrap; }}
.hero .tag {{
    background: rgba(255, 255, 255, 0.18);
    border: 1px solid rgba(255, 255, 255, 0.35);
    color: #fff; padding: 0.25rem 0.7rem; border-radius: 999px; font-size: 0.85rem;
}}

/* ---------- section label ---------- */
.section-label {{
    display: inline-block;
    padding: 0.15rem 0.7rem;
    background: #EEF2FF;
    color: {COLORS["primary"]};
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.8rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
}}

/* ---------- card ---------- */
.card {{
    background: {COLORS["bg_card"]};
    padding: 1.25rem 1.4rem;
    border-radius: 14px;
    border: 1px solid #E5E7EB;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04), 0 4px 20px rgba(0,0,0,0.04);
    height: 100%;
}}
.metric-card {{
    background: {COLORS["bg_card"]};
    padding: 1.1rem 1.2rem;
    border-radius: 14px;
    border: 1px solid #E5E7EB;
    border-left: 4px solid {COLORS["primary"]};
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}}
.metric-card .label {{ color: {COLORS["muted"]}; font-size: 0.82rem; text-transform: uppercase;
                       letter-spacing: 0.08em; font-weight: 600; }}
.metric-card .value {{ color: {COLORS["text"]}; font-size: 1.9rem; font-weight: 800;
                       line-height: 1.2; margin-top: 0.2rem; }}
.metric-card .delta {{ color: {COLORS["muted"]}; font-size: 0.85rem; margin-top: 0.1rem; }}
.metric-card.accent {{ border-left-color: {COLORS["accent"]}; }}
.metric-card.td     {{ border-left-color: {COLORS["TD"]}; }}
.metric-card.dd     {{ border-left-color: {COLORS["DD"]}; }}
.metric-card.asd    {{ border-left-color: {COLORS["ASD"]}; }}

/* ---------- info / warning boxes ---------- */
.info-box {{
    background: #EEF2FF;
    border-left: 4px solid {COLORS["primary"]};
    padding: 0.9rem 1.1rem;
    border-radius: 10px;
    color: {COLORS["text"]};
    margin: 0.5rem 0;
}}
.warn-box {{
    background: #FFF7ED;
    border-left: 4px solid #F97316;
    padding: 0.9rem 1.1rem;
    border-radius: 10px;
    color: {COLORS["text"]};
    margin: 0.5rem 0;
}}
.success-box {{
    background: #ECFDF5;
    border-left: 4px solid #10B981;
    padding: 0.9rem 1.1rem;
    border-radius: 10px;
    color: {COLORS["text"]};
    margin: 0.5rem 0;
}}

/* ---------- tag chips ---------- */
.chip {{
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-right: 0.35rem;
}}
.chip-td  {{ background: #E6FAF7; color: {COLORS["TD"]}; }}
.chip-dd  {{ background: #FFF4E1; color: #B47610; }}
.chip-asd {{ background: #FDE4E7; color: {COLORS["ASD"]}; }}

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] {{ background: #FFFFFF; border-right: 1px solid #E5E7EB; }}
section[data-testid="stSidebar"] .stRadio label {{
    font-weight: 500; padding: 0.25rem 0; font-size: 0.95rem;
}}

/* ---------- dataframes ---------- */
[data-testid="stDataFrame"] {{
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #E5E7EB;
}}

/* ---------- buttons ---------- */
.stButton button[kind="primary"] {{
    background: linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["accent"]} 100%);
    border: none; border-radius: 10px; padding: 0.55rem 1.3rem; font-weight: 600;
    box-shadow: 0 4px 12px rgba(67, 97, 238, 0.3);
}}
.stButton button[kind="primary"]:hover {{ transform: translateY(-1px); }}

/* ---------- tabs ---------- */
.stTabs [data-baseweb="tab-list"] {{ gap: 0.3rem; }}
.stTabs [data-baseweb="tab"] {{
    border-radius: 10px 10px 0 0; padding: 0.5rem 1.1rem; background: transparent;
}}
.stTabs [aria-selected="true"] {{
    background: {COLORS["bg_card"]} !important;
    color: {COLORS["primary"]} !important;
    font-weight: 700;
}}

/* ---------- code ---------- */
code {{ background: #EEF2FF; color: {COLORS["primary"]};
         padding: 0.12rem 0.35rem; border-radius: 5px; font-size: 0.9em; }}
</style>
"""


# ---------------------------------------------------------------------------
# Feature documentation
# ---------------------------------------------------------------------------
FEATURE_DOCS = {
    "age_months": {
        "title": "Age (months)",
        "icon": "🧍",
        "group": "Demographics",
        "desc": "อายุของเด็กในหน่วยเดือน แปลงจาก CHAT format `5;03.10` (ปี;เดือน.วัน)",
        "clinical": "ใช้เป็น **control variable** — ภาษาเด็กพัฒนาเร็วมากช่วง 2–5 ปี ต้องคุมอายุก่อนเปรียบเทียบกลุ่ม",
        "direction": "neutral",
    },
    "total_utterances": {
        "title": "Total utterances",
        "icon": "💬",
        "group": "Productivity",
        "desc": "จำนวนประโยคที่เด็กพูดทั้งหมด (นับบรรทัด `*CHI:` ทุกบรรทัด)",
        "clinical": "เด็ก ASD มักพูดน้อยกว่า — social communication deficit เป็น core symptom ใน DSM-5",
        "direction": "สูง = ดี",
    },
    "total_words": {
        "title": "Total words",
        "icon": "📝",
        "group": "Productivity",
        "desc": "จำนวนคำที่เด็กพูด (ตัด punctuation ออก) — proxy ของ vocabulary production",
        "clinical": "ในผลเรา: ASD 296 vs DD 517 → **ASD พูดน้อยกว่าแม้อายุใกล้กัน** นักบำบัดใช้ประเมิน session goals",
        "direction": "สูง = ดี",
    },
    "mlu": {
        "title": "MLU (morphemes) ⭐",
        "icon": "📏",
        "group": "Complexity",
        "desc": "Mean Length of Utterance — จำนวน morphemes เฉลี่ยต่อประโยค (เช่น `cats` = 2 morphemes)",
        "clinical": (
            "**Gold standard** การประเมินพัฒนาภาษามา 50+ ปี (Brown 1973). ใช้แบ่ง Brown's stages I–V. "
            "ผลเรา: ASD 2.27 vs DD 3.57 — ASD ต่ำกว่าชัดเจนแม้อายุเท่ากัน"
        ),
        "direction": "สูง = ดี",
    },
    "mluw": {
        "title": "MLU (words)",
        "icon": "📐",
        "group": "Complexity",
        "desc": "เหมือน MLU แต่นับเป็นคำแทน morpheme (คำนวณง่ายกว่า)",
        "clinical": "นักบำบัดไทยมักใช้ MLUw เพราะไม่ต้อง parse morphology",
        "direction": "สูง = ดี",
    },
    "ttr": {
        "title": "TTR (Type-Token Ratio) ⭐",
        "icon": "🎨",
        "group": "Lexical diversity",
        "desc": "สูตร: `unique_words / total_words` — วัดความหลากหลายของคำ",
        "clinical": (
            "TTR ต่ำ → ใช้คำซ้ำ ๆ อาจบ่ง **echolalia** (core ASD symptom, พบ 75%). "
            "ใน Rollins: Carl TTR 0.02 → 0.34 ใน 4 sessions"
        ),
        "direction": "สูง = ดี",
    },
    "unintelligible_count": {
        "title": "Unintelligible count",
        "icon": "🔇",
        "group": "ASD markers",
        "desc": "นับประโยคที่มี `xxx` (ฟังไม่รู้เรื่อง) หรือ `yyy` (ฟังไม่ออกแต่รู้หน่วยเสียง)",
        "clinical": "Articulation/phonological disorder comorbidity. ลดลง = บำบัดได้ผล",
        "direction": "ต่ำ = ดี",
    },
    "unintelligible_ratio": {
        "title": "Unintelligible ratio",
        "icon": "📊",
        "group": "ASD markers",
        "desc": "สัดส่วน unintelligible / total utterances (normalize แล้ว)",
        "clinical": "ใช้เปรียบเทียบข้ามเด็กที่มีจำนวน utterances ต่างกัน",
        "direction": "ต่ำ = ดี",
    },
    "zero_vocalization_count": {
        "title": "Zero vocalizations",
        "icon": "🤐",
        "group": "ASD markers",
        "desc": "นับประโยค `0 .` = เด็กตอบโดยไม่ใช้เสียง (ชี้, พยักหน้า, gesture)",
        "clinical": (
            "สัญญาณ non-verbal ASD (~30% ของเด็ก ASD อายุ 5+). "
            "Josh session 1: 122 → session 4: 43 (ลดลงชัดเจน = กำลังพัฒนา)"
        ),
        "direction": "ต่ำ = ดี",
    },
    "nonverbal_vocalization_count": {
        "title": "Non-verbal vocalizations",
        "icon": "🎵",
        "group": "ASD markers",
        "desc": "นับ markers แบบ `&=gasp`, `&=laugh`, `&=cry` (เสียงที่ไม่ใช่คำ)",
        "clinical": "ASD มี unusual vocalization patterns. **ระวัง:** หัวเราะเยอะ = social engagement ดี",
        "direction": "บริบทขึ้นอยู่",
    },
    "question_ratio": {
        "title": "Question ratio",
        "icon": "❓",
        "group": "Pragmatic",
        "desc": "สัดส่วนประโยคที่ลงท้ายด้วย `?` ของเด็ก",
        "clinical": "สะท้อน social initiation + joint attention. ASD ถามคำถามน้อยกว่า TD (core pragmatic deficit)",
        "direction": "สูง = ดี",
    },
    "echolalia_count": {
        "title": "Echolalia count",
        "icon": "🔁",
        "group": "ASD markers",
        "desc": "นับครั้งที่เด็กพูด *ซ้ำ* คำพูดของผู้ใหญ่/ตัวเอง verbatim ภายใน 5 ประโยคก่อนหน้า (ต้อง ≥2 คำ)",
        "clinical": "Echolalia เป็น core ASD marker ตั้งแต่ Kanner 1943 — ASD มัก repeat โดยไม่เข้าใจ context (Prizant 1983)",
        "direction": "สูง = ASD",
    },
    "echolalia_ratio": {
        "title": "Echolalia ratio",
        "icon": "🔁",
        "group": "ASD markers",
        "desc": "echolalia_count ÷ total_utterances (normalize ตามความยาว session)",
        "clinical": "ASD มีค่าเฉลี่ย ~2× ของ TD/DD ใน dataset ของเรา (Eigsti+Nadig+NYU+Quigley+Flusberg)",
        "direction": "สูง = ASD",
    },
}


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def hero(title: str, subtitle: str, tags: list[str] | None = None) -> None:
    tag_html = ""
    if tags:
        tag_html = '<div class="tags">' + "".join(
            f'<span class="tag">{t}</span>' for t in tags
        ) + '</div>'
    st.markdown(
        f'<div class="hero"><h1>{title}</h1>'
        f'<div class="sub">{subtitle}</div>{tag_html}</div>',
        unsafe_allow_html=True,
    )


def metric_card(col, label: str, value: str,
                delta: str = "", flavor: str = "") -> None:
    cls = f"metric-card {flavor}".strip()
    col.markdown(
        f'<div class="{cls}"><div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
        + (f'<div class="delta">{delta}</div>' if delta else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def section_label(text: str) -> None:
    st.markdown(f'<span class="section-label">{text}</span>',
                unsafe_allow_html=True)


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
        legend={"bgcolor": "rgba(255,255,255,0.8)", "bordercolor": "#E5E7EB",
                "borderwidth": 1},
    )
    if height is not None:
        fig.update_layout(height=height)
    return fig


# ---------------------------------------------------------------------------
# Data + model caching
# ---------------------------------------------------------------------------
@st.cache_data
def load_combined() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "combined_features.csv")


@st.cache_data
def load_longitudinal() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "longitudinal_features.csv").sort_values(
        ["child", "session_order"]
    )


@st.cache_resource
def train_screening_model(df: pd.DataFrame):
    bundle_path = ARTIFACT_DIR / "screening_model.joblib"
    if bundle_path.exists():
        try:
            bundle = joblib.load(bundle_path)
            if bundle.get("features") == FEATURES:
                return bundle["model"]
        except Exception:  # noqa: BLE001
            pass

    X = df[FEATURES].values
    y = (df["group"] == "ASD").astype(int).values
    pipe = Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("sc", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000,
                                   class_weight="balanced",
                                   random_state=42)),
    ])
    pipe.fit(X, y)
    return pipe


@st.cache_data
def load_model_card() -> dict:
    card_path = ARTIFACT_DIR / "model_card.json"
    if not card_path.exists():
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
        return json.loads(card_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"model_version": "model-card-unreadable"}


def _compute_composite(df: pd.DataFrame) -> pd.DataFrame:
    direction = {
        "mlu": +1, "mluw": +1, "ttr": +1,
        "total_words": +1, "total_utterances": +1,
        "unintelligible_ratio": -1, "zero_vocalization_count": -1,
    }
    df = df.copy()
    z = pd.DataFrame(index=df.index)
    for f, d in direction.items():
        x = df[f].astype(float)
        mu, sd = x.mean(), x.std(ddof=0)
        z[f] = 0.0 if sd == 0 else d * (x - mu) / sd
    df["composite_score"] = z.mean(axis=1).round(3)
    return df


# ---------------------------------------------------------------------------
# Severity scoring (inspired by Eni et al. 2025 — ASDSpeech)
# ---------------------------------------------------------------------------
#
# Goal: turn the binary screening output into clinically useful *graded*
# scores so a speech therapist can read "how much" rather than only "yes/no".
#
# Three 0–10 scores are produced:
#   1. severity_overall: sigmoid(logit) * 10
#         - same direction as P(ASD), gives ASD severity in a 0–10 scale
#           comparable in spirit to ADOS-2 total scoring.
#   2. communication_strength: mean z-score of positive features mapped to 0–10
#         - higher = richer language (MLU, TTR, words, questions).
#   3. marker_burden: mean z-score of ASD-marker features mapped to 0–10
#         - higher = more ASD markers (echolalia, unintelligible, zero vocal).
#
# A z-score is mapped to a 0–10 score with sigmoid(z) * 10 so that
#   z = 0   -> 5  (population mean)
#   z = +2  -> ~8.8
#   z = -2  -> ~1.2
# bounded to [0, 10] without clipping artefacts.

def _sigmoid(x: float) -> float:
    # Numerically stable; we never see |x|>50 in practice.
    if x >= 0:
        z = np.exp(-x)
        return float(1.0 / (1.0 + z))
    z = np.exp(x)
    return float(z / (1.0 + z))


# ---------------------------------------------------------------------------
# Parent concern checklist (multi-modal input, modality #2)
# ---------------------------------------------------------------------------
# This is a project-authored concern checklist, not a copy or modification of
# M-CHAT-R/F. It gives parents a structured way to record observations while
# keeping the app safely framed as screening support.

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
    """Return (concerning_count, severity_0_10).

    `answers` is a list parallel to PARENT_CHECKLIST_ITEMS, each "yes" / "no" / ""
    where "" means not answered.
    """
    n_concerning = 0
    for ans, (_q, concerning) in zip(answers, PARENT_CHECKLIST_ITEMS):
        if ans == concerning:
            n_concerning += 1
    return n_concerning, n_concerning  # already 0–10 since 10 items


def fuse_severity(speech_score: float, checklist_score: float,
                  w_speech: float = 0.5) -> float:
    """Late-fusion of speech-derived severity and parent concern score."""
    w_checklist = 1.0 - w_speech
    return round(w_speech * speech_score + w_checklist * checklist_score, 1)


def compute_severity(model, df_train: pd.DataFrame, x_row: np.ndarray) -> dict:
    """Return graded 0–10 severity scores for a single child input.

    Parameters
    ----------
    model : sklearn Pipeline (Imputer -> Scaler -> LogReg)
    df_train : training feature DataFrame used to derive z-score statistics
    x_row : shape (1, n_features) raw input matching FEATURES order
    """
    imp = model.named_steps["imp"]
    sc = model.named_steps["sc"]
    clf = model.named_steps["clf"]

    x_imp = imp.transform(x_row)
    x_scaled = sc.transform(x_imp)[0]
    logit = float(clf.intercept_[0] + (clf.coef_[0] * x_scaled).sum())
    severity_overall = _sigmoid(logit) * 10.0

    def _subscore(feature_names: list[str], sign: int) -> float:
        zs = []
        for f in feature_names:
            if f not in df_train.columns:
                continue
            mu = float(df_train[f].mean())
            sd = float(df_train[f].std(ddof=0))
            if sd == 0:
                continue
            xv = float(x_row[0, FEATURES.index(f)])
            zs.append(sign * (xv - mu) / sd)
        if not zs:
            return 5.0
        z_mean = float(np.mean(zs))
        return _sigmoid(z_mean) * 10.0

    communication = _subscore(POSITIVE_FEATURES, sign=+1)
    marker = _subscore(MARKER_FEATURES, sign=+1)

    return {
        "severity_overall": round(severity_overall, 1),
        "communication_strength": round(communication, 1),
        "marker_burden": round(marker, 1),
        "logit": round(logit, 3),
    }


# ===========================================================================
# PAGES
# ===========================================================================
PARENT_CONCERN_ITEMS = [
    ("ไม่ค่อยตอบสนองเมื่อเรียกชื่อ", 1),
    ("ไม่ค่อยชี้เพื่อขอของหรือชวนดูสิ่งที่สนใจ", 1),
    ("ไม่ค่อยเล่นสมมติ เช่น ป้อนตุ๊กตา หรือแกล้งคุยโทรศัพท์", 1),
    ("สบตาน้อยหรือไม่ค่อยยิ้มตอบขณะเล่นด้วย", 1),
    ("ไม่ค่อยสนใจเล่นหรือมองเด็กคนอื่น", 1),
    ("พูดซ้ำคำ/ประโยคเดิมบ่อยจนสื่อสารยาก", 1),
    ("พูดน้อยกว่าที่คาดสำหรับวัย หรือยังไม่ใช้วลี/ประโยค", 1),
    ("มีเสียง/ท่าทางซ้ำ ๆ เช่น โบกมือ หมุนตัว หรือเรียงของซ้ำ", 1),
    ("ไวต่อเสียง แสง สัมผัส หรือ routine เปลี่ยนแล้วลำบากมาก", 1),
    ("ผู้ปกครองรู้สึกกังวลเรื่องการสื่อสารหรือพัฒนาการ", 2),
]


def _parent_concern_level(score: int, age_months: float, audio_uploaded: bool) -> tuple[str, str, str]:
    if score >= 7:
        return (
            "Recommend professional assessment",
            "ควรนัดปรึกษากุมารแพทย์พัฒนาการเด็ก นักแก้ไขการพูด หรือนักจิตวิทยาเด็ก เพื่อประเมินต่ออย่างเป็นระบบ",
            "warn",
        )
    if score >= 4 or (age_months < 36 and score >= 3):
        return (
            "Needs monitoring",
            "ควรติดตามพฤติกรรม 2-4 สัปดาห์ จดตัวอย่างสถานการณ์ และปรึกษาผู้เชี่ยวชาญหากยังคงกังวล",
            "info",
        )
    if audio_uploaded:
        return (
            "Inconclusive",
            "มีไฟล์เสียงประกอบ แต่ Parent Mode ยังไม่ใช้เสียงเพื่อสรุปผลโดยตรง ต้องให้ clinician/research workflow ตรวจ transcript ก่อน",
            "warn",
        )
    return (
        "Low concern",
        "ยังไม่พบสัญญาณกังวลเด่นจาก checklist นี้ แต่หากผู้ปกครองกังวลควรปรึกษาผู้เชี่ยวชาญเสมอ",
        "success",
    )


def page_parent_public() -> None:
    hero(
        "Parent Public Demo",
        "แบบลองใช้สำหรับผู้ปกครอง: ช่วยจัดระเบียบข้อสังเกตและแนะนำ next step โดยไม่เก็บข้อมูลถาวร",
        tags=["Public web", "No data retention", "Not diagnostic", "Thai-first", "Audio optional"],
    )

    info_box(
        "**สำคัญ:** หน้านี้เป็น screening support / education demo เท่านั้น "
        "ไม่ใช่การวินิจฉัย ASD และไม่แทนการประเมินโดยแพทย์หรือนักบำบัด",
        kind="warn",
    )

    left, right = st.columns([1.1, 0.9])
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### ข้อมูลเบื้องต้น")
        c1, c2 = st.columns(2)
        age_months = c1.number_input("อายุเด็ก (เดือน)", 12.0, 120.0, 36.0, step=1.0)
        language_context = c2.selectbox(
            "ภาษาที่ใช้ในบ้าน",
            ["ไทยเป็นหลัก", "ไทย+อังกฤษ", "อังกฤษเป็นหลัก", "อื่น ๆ / หลายภาษา"],
        )
        main_concern = st.text_area(
            "ผู้ปกครองกังวลเรื่องอะไรที่สุด",
            placeholder="เช่น ไม่ค่อยตอบชื่อ พูดซ้ำ ไม่ชี้บอกความต้องการ...",
            height=86,
        )

        st.markdown("### Parent Concern Checklist")
        st.caption(
            "Checklist นี้เขียนขึ้นสำหรับ demo ของโปรเจกต์ ไม่ใช่ M-CHAT-R/F "
            "หากต้องการใช้ M-CHAT อย่างเป็นทางการควรใช้จากแหล่ง official"
        )
        concern_score = 0
        checked_items = []
        for idx, (item, weight) in enumerate(PARENT_CONCERN_ITEMS, 1):
            checked = st.checkbox(item, key=f"parent_concern_{idx}")
            if checked:
                concern_score += weight
                checked_items.append(item)

        st.markdown("### Optional audio")
        audio_consent = st.checkbox(
            "ฉันยืนยันว่ามีสิทธิ์ใช้ไฟล์เสียงนี้ และเข้าใจว่าเสียงเด็กเป็นข้อมูลอ่อนไหว",
        )
        parent_audio = st.file_uploader(
            "อัปโหลดเสียงประกอบ (optional)",
            type=["wav", "mp3", "m4a", "flac", "ogg"],
            disabled=not audio_consent,
            help="Parent Mode จะไม่เก็บไฟล์ถาวร และยังไม่ใช้เสียงเพื่อวินิจฉัย",
        )
        if parent_audio is not None:
            st.caption(
                f"รับไฟล์ `{parent_audio.name}` ขนาด {parent_audio.size / 1024 / 1024:.2f} MB "
                "ใน memory ของ session นี้เท่านั้น. สำหรับการถอดเสียงเต็ม ให้ใช้หน้า Audio Assessment "
                "ที่มี transcript QA ก่อน prediction."
            )

        submitted = st.button("ดูคำแนะนำ", type="primary", width='stretch')
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Summary for parent")
        if submitted:
            level, recommendation, kind = _parent_concern_level(
                concern_score, age_months, parent_audio is not None,
            )
            info_box(f"**{level}**<br>{recommendation}", kind=kind)
            st.metric("Concern score", f"{concern_score}/11")
            st.markdown("#### สิ่งที่ควรเตรียมไปคุยกับผู้เชี่ยวชาญ")
            next_steps = [
                "ตัวอย่างสถานการณ์ที่เกิดบ่อย เช่น เรียกชื่อแล้วไม่หัน หรือพูดซ้ำประโยคเดิม",
                "ช่วงอายุที่เริ่มสังเกตเห็น และพฤติกรรมเปลี่ยนไปอย่างไร",
                "ภาษาในบ้านและบริบทการสื่อสาร เช่น ไทย/อังกฤษ/หลายภาษา",
                "วิดีโอหรือเสียงสั้น ๆ เฉพาะเมื่อได้รับ consent และปลอดภัยต่อ privacy",
            ]
            st.write(pd.DataFrame({"next_step": next_steps}))
            summary = {
                "age_months": age_months,
                "language_context": language_context,
                "concern_level": level,
                "concern_score": concern_score,
                "checked_items": checked_items,
                "main_concern": main_concern,
                "recommendation": recommendation,
                "privacy_note": "This public demo does not intentionally persist uploaded audio or parent-entered data.",
            }
            st.download_button(
                "Download parent summary (JSON)",
                data=pd.Series(summary).to_json(force_ascii=False, indent=2).encode("utf-8"),
                file_name="parent_screening_support_summary.json",
                mime="application/json",
            )
        else:
            st.caption(
                "กรอกข้อมูลฝั่งซ้ายแล้วกดดูคำแนะนำ ระบบจะสรุประดับ concern "
                "เป็นภาษาที่ใช้คุยกับผู้เชี่ยวชาญต่อได้"
            )
        st.markdown("</div>", unsafe_allow_html=True)


def page_overview(df: pd.DataFrame, longitudinal: pd.DataFrame) -> None:
    hero(
        "AI-Assisted Clinical Assessment of Autism",
        "Term-paper prototype — วิเคราะห์ CHAT transcripts จาก ASDBank "
        "เพื่อคัดกรอง ASD และติดตามพัฒนาการจากการบำบัด",
        tags=["Eigsti", "Nadig", "NYU-Emerson", "Flusberg", "13 features",
              "5 corpora", "122 children"],
    )

    # top metrics
    c1, c2, c3, c4 = st.columns(4)
    metric_card(c1, "Cross-sectional",
                f"{len(df)}", "children in classification set")
    metric_card(c2, "Longitudinal",
                f"{longitudinal['child'].nunique()}", "children with sessions", flavor="accent")
    metric_card(c3, "Features / child", f"{len(FEATURES)}",
                "extracted per transcript", flavor="td")
    metric_card(c4, "Best AUC",
                "0.93", "LogReg (ASD vs non-ASD)", flavor="asd")

    st.markdown("")

    # two-column layout
    left, right = st.columns([1.2, 1])

    with left:
        section_label("Group distribution")
        st.markdown("### Samples by group × corpus")
        counts = df.groupby(["corpus", "group"]).size().reset_index(name="n")
        fig = px.bar(
            counts, x="group", y="n", color="corpus",
            barmode="group", text="n",
            category_orders={"group": ["TD", "DD", "ASD"]},
            color_discrete_sequence=[COLORS["primary"], COLORS["accent"],
                                     COLORS["TD"]],
        )
        fig.update_traces(textposition="outside", textfont_size=13,
                          marker_line_width=0)
        st.plotly_chart(style_fig(fig, height=380),
                        width='stretch', config=st_chart_cfg)

    with right:
        section_label("Per-group counts")
        st.markdown("### Total by group")
        g_counts = df["group"].value_counts()
        ca, cb, cc = st.columns(3)
        metric_card(ca, "TD", f"{g_counts.get('TD', 0)}",
                    "typical development", flavor="td")
        metric_card(cb, "DD", f"{g_counts.get('DD', 0)}",
                    "developmental delay", flavor="dd")
        metric_card(cc, "ASD", f"{g_counts.get('ASD', 0)}",
                    "autism spectrum", flavor="asd")

        st.markdown("")
        section_label("Pipeline status")
        info_box(
            "✅ Features extracted &nbsp; ✅ EDA done &nbsp; ✅ Classifiers trained "
            "&nbsp; ✅ Deep learning &nbsp; ✅ Progress tracking",
            kind="success",
        )

    st.markdown("")
    section_label("Quick stats per group (mean)")
    st.markdown("### Key linguistic markers")

    tbl = (df.groupby("group")[FEATURES]
           .mean().round(2)
           .reindex(["TD", "DD", "ASD"]))
    display = tbl[["age_months", "mlu", "mluw", "ttr",
                   "total_words", "total_utterances",
                   "unintelligible_ratio"]].rename(
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
    st.dataframe(display.style.background_gradient(cmap="Blues", axis=0),
                 width='stretch')


def page_feature_ref(df: pd.DataFrame) -> None:
    hero(
        "📘 Feature reference",
        "ความหมายและความสำคัญทาง clinical ของแต่ละ feature "
        "ที่สกัดจาก CHAT transcripts",
        tags=["13 features", "CHI utterances only"],
    )

    # Summary chips at top
    section_label("Overview")
    st.markdown("### Feature summary with live statistics")
    rows = []
    for feat in FEATURES:
        if feat not in df.columns:
            continue
        by_group = df.groupby("group")[feat].mean().to_dict()
        rows.append({
            "Feature": feat,
            "Group": FEATURE_DOCS[feat]["group"],
            "Direction": FEATURE_DOCS[feat]["direction"],
            "ASD": round(by_group.get("ASD", float("nan")), 2),
            "DD":  round(by_group.get("DD",  float("nan")), 2),
            "TD":  round(by_group.get("TD",  float("nan")), 2),
        })
    tbl = pd.DataFrame(rows)
    st.dataframe(tbl, width='stretch', hide_index=True)

    st.markdown("")
    section_label("Deep dive")
    st.markdown("### อธิบายทีละ feature")

    picked = st.selectbox(
        "เลือก feature",
        FEATURES,
        format_func=lambda f: f"{FEATURE_DOCS[f]['icon']}  {f}  —  "
                              f"{FEATURE_DOCS[f]['title']}",
    )
    doc = FEATURE_DOCS[picked]

    # Info card + stats side by side
    left, right = st.columns([1.3, 1])

    with left:
        st.markdown(
            f'<div class="card">'
            f'<h3 style="margin:0">{doc["icon"]} {doc["title"]}</h3>'
            f'<div style="margin:0.3rem 0 0.9rem 0">'
            f'<span class="chip chip-td">{doc["group"]}</span>'
            f'<span class="chip chip-dd">{doc["direction"]}</span>'
            f'</div>'
            f'<p><b>นิยาม:</b><br>{doc["desc"]}</p>'
            f'<p style="margin-bottom:0"><b>ความสำคัญ clinical:</b><br>'
            f'{doc["clinical"]}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with right:
        if picked in df.columns:
            sub = df.dropna(subset=[picked, "group"])
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"#### Stats for `{picked}`")
            ca, cb = st.columns(2)
            ca.metric("Mean (all)", f"{sub[picked].mean():.3f}")
            cb.metric("Std (all)", f"{sub[picked].std():.3f}")
            by_group = sub.groupby("group")[picked].mean().reindex(
                ["TD", "DD", "ASD"])
            fig = go.Figure(go.Bar(
                x=by_group.index, y=by_group.values,
                marker_color=[COLORS["TD"], COLORS["DD"], COLORS["ASD"]],
                text=[f"{v:.2f}" for v in by_group.values],
                textposition="outside",
            ))
            fig.update_layout(showlegend=False,
                              yaxis_title=f"{picked} (mean)")
            st.plotly_chart(style_fig(fig, height=240),
                            width='stretch', config=st_chart_cfg)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("")
    if picked in df.columns:
        section_label("Distribution")
        st.markdown(f"### `{picked}` — การกระจายตัวตามกลุ่ม")
        sub = df.dropna(subset=[picked, "group"])
        fig = px.violin(
            sub, x="group", y=picked, color="group",
            box=True, points="all",
            category_orders={"group": ["TD", "DD", "ASD"]},
            color_discrete_map=COLORS,
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(style_fig(fig, height=420),
                        width='stretch', config=st_chart_cfg)


def page_eda(df: pd.DataFrame) -> None:
    hero(
        "🔎 Exploratory Data Analysis",
        "เปรียบเทียบ features ระหว่างกลุ่ม TD / DD / ASD แบบ interactive",
    )

    # Filters
    with st.container():
        c1, c2 = st.columns(2)
        groups_sel = c1.multiselect(
            "Groups", options=["TD", "DD", "ASD"],
            default=["TD", "DD", "ASD"],
        )
        corpora_sel = c2.multiselect(
            "Corpora", options=sorted(df["corpus"].unique()),
            default=sorted(df["corpus"].unique()),
        )
    filt = df[df["group"].isin(groups_sel) & df["corpus"].isin(corpora_sel)]
    st.caption(f"Showing **{len(filt)}** of {len(df)} rows after filter")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["🔬 Scatter", "📊 Distribution", "🔥 Correlation", "📄 Raw data"]
    )

    with tab1:
        c1, c2 = st.columns(2)
        x_feat = c1.selectbox("X-axis", FEATURES,
                              index=FEATURES.index("mlu"))
        y_feat = c2.selectbox("Y-axis", FEATURES,
                              index=FEATURES.index("ttr"))
        fig = px.scatter(
            filt, x=x_feat, y=y_feat, color="group",
            size="total_words", size_max=28,
            hover_data=["participant_id", "corpus", "age_months"],
            color_discrete_map=COLORS,
        )
        fig.update_traces(marker={"opacity": 0.8,
                                  "line": {"width": 1, "color": "white"}})
        st.plotly_chart(style_fig(fig, height=520),
                        width='stretch', config=st_chart_cfg)

    with tab2:
        feat = st.selectbox("Feature", FEATURES,
                            index=FEATURES.index("mlu"), key="dist_feat")
        c1, c2 = st.columns(2)
        fig1 = px.violin(
            filt, x="group", y=feat, color="group",
            box=True, points="all",
            category_orders={"group": ["TD", "DD", "ASD"]},
            color_discrete_map=COLORS,
        )
        fig1.update_layout(showlegend=False)
        c1.plotly_chart(style_fig(fig1, height=430),
                        width='stretch', config=st_chart_cfg)
        fig2 = px.histogram(
            filt, x=feat, color="group", barmode="overlay", nbins=25,
            color_discrete_map=COLORS, opacity=0.7,
        )
        c2.plotly_chart(style_fig(fig2, height=430),
                        width='stretch', config=st_chart_cfg)

    with tab3:
        corr = filt[FEATURES].corr(numeric_only=True).round(2)
        fig = px.imshow(
            corr, text_auto=True, aspect="auto",
            color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
        )
        st.plotly_chart(style_fig(fig, height=600),
                        width='stretch', config=st_chart_cfg)

    with tab4:
        st.dataframe(filt, width='stretch', hide_index=True)


def page_screening(df: pd.DataFrame) -> None:
    hero(
        "🩺 Screening Tool",
        "กรอก language profile ของเด็ก → AI ทำนายความเสี่ยง ASD",
        tags=["Logistic Regression", "AUC 0.931", "5-fold CV validated",
              "XAI", "Uncertainty band", "Severity scoring", "Parent checklist"],
    )

    model = train_screening_model(df)

    left, right = st.columns([1, 1.3])

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📝 Child profile")
        with st.form("screen_form"):
            c1, c2 = st.columns(2)
            age = c1.number_input("Age (months)", 12.0, 120.0, 48.0, step=1.0)
            n_utt = c2.number_input("Utterances (CHI)", 10, 1000, 180, step=10)

            c1, c2 = st.columns(2)
            n_words = c1.number_input("Total words", 0, 5000, 400, step=20)
            ttr = c2.number_input("TTR", 0.0, 1.0, 0.4, step=0.01)

            c1, c2 = st.columns(2)
            mlu = c1.number_input("MLU (morph)", 0.0, 10.0, 2.5, step=0.1)
            mluw = c2.number_input("MLU (words)", 0.0, 10.0, 2.3, step=0.1)

            c1, c2 = st.columns(2)
            unint = c1.number_input("Unintelligible (xxx/yyy)", 0, 500, 10)
            unint_r = c2.number_input("Unint. ratio", 0.0, 1.0, 0.05, step=0.01)

            c1, c2 = st.columns(2)
            zero = c1.number_input("Zero vocal. (`0 .`)", 0, 500, 5)
            nonverb = c2.number_input("Non-verbal (&=)", 0, 500, 8)

            c1, c2 = st.columns(2)
            q_ratio = c1.number_input("Question ratio", 0.0, 1.0, 0.08,
                                       step=0.01)
            echo = c2.number_input("Echolalia (count)", 0, 500, 3,
                                    help="ครั้งที่เด็กพูดซ้ำประโยคที่ผู้ใหญ่หรือ "
                                         "ตัวเองพึ่งพูด (≥2 คำ ภายใน 5 ประโยคก่อนหน้า)")
            echo_r = st.number_input("Echolalia ratio", 0.0, 1.0, 0.02,
                                      step=0.01,
                                      help="echolalia_count ÷ total_utterances")

            # --- Modality #2: project-authored parent concern checklist -----
            checklist_answers: list[str] = []
            with st.expander("📋 Parent concern checklist (optional)"):
                st.caption(
                    "ตอบ 10 ข้อนี้เพื่อเพิ่ม signal จากผู้ปกครองแบบปลอดภัย "
                    "รายการนี้เขียนขึ้นสำหรับ demo ไม่ใช่ M-CHAT-R/F. "
                    "ข้ามได้ — ระบบจะใช้แค่ speech features"
                )
                for i, (q, _concerning) in enumerate(PARENT_CHECKLIST_ITEMS):
                    ans = st.radio(
                        f"**{i + 1}.** {q}",
                        options=["", "yes", "no"],
                        format_func=lambda v: {"": "— ไม่ตอบ —",
                                                "yes": "ใช่",
                                                "no": "ไม่"}[v],
                        index=0,
                        horizontal=True,
                        key=f"parent_checklist_{i}",
                    )
                    checklist_answers.append(ans)

            submitted = st.form_submit_button("🎯 Predict risk",
                                               type="primary",
                                               width='stretch')
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🎯 Prediction")

        if submitted:
            x = np.array([[age, n_utt, mlu, mluw, ttr, n_words,
                           unint, unint_r, zero, nonverb, q_ratio,
                           echo, echo_r]])
            prob = float(model.predict_proba(x)[0, 1])
            pred, kind, color = classify_risk(prob)

            # Gauge — bands aligned with the uncertainty zone
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
                        {"range": [0, UNCERTAIN_LOW * 100],   "color": "#ECFDF5"},
                        {"range": [UNCERTAIN_LOW * 100,
                                   UNCERTAIN_HIGH * 100],     "color": "#FFF7ED"},
                        {"range": [UNCERTAIN_HIGH * 100, 100], "color": "#FEE2E2"},
                    ],
                    "threshold": {
                        "line": {"color": color, "width": 5},
                        "thickness": 0.8, "value": prob * 100,
                    },
                },
            ))
            fig.update_layout(
                template=PLOTLY_TEMPLATE, height=300,
                margin={"l": 20, "r": 20, "t": 10, "b": 10},
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, width='stretch', config=st_chart_cfg)

            info_box(f"**{pred}**  ·  ASD probability = {prob:.1%}",
                     kind=kind)
            st.caption(
                f"Uncertain band = "
                f"[{UNCERTAIN_LOW:.0%}, {UNCERTAIN_HIGH:.0%}) — "
                "predictions inside this range are reported as "
                "indeterminate to avoid over-confident screening "
                "(Megerian et al. 2022)."
            )
            info_box(
                "⚠️ Research prototype — not for clinical use. "
                f"Trained/evaluated on {len(df)} TalkBank/ASDBank rows; "
                "not externally validated in Thai clinical cohorts.",
                kind="warn",
            )

            # --- Severity breakdown (graded scores) ---
            sev = compute_severity(model, df, x)
            st.markdown("#### 📊 Graded severity scores (0–10)")
            sc1, sc2, sc3 = st.columns(3)

            def _sev_color(v: float, reverse: bool = False) -> str:
                if reverse:
                    if v >= 6.5: return COLORS["TD"]
                    if v >= 3.5: return COLORS["DD"]
                    return COLORS["ASD"]
                if v >= 6.5: return COLORS["ASD"]
                if v >= 3.5: return COLORS["DD"]
                return COLORS["TD"]

            def _score_card(col, label, value, color, hint):
                col.markdown(
                    f"""<div class="card" style="text-align:center;padding:1rem">
                        <div style="font-size:0.75rem;color:#6C757D;
                                    text-transform:uppercase;letter-spacing:.06em">{label}</div>
                        <div style="font-size:2.4rem;font-weight:800;color:{color};
                                    line-height:1">{value:.1f}</div>
                        <div style="font-size:0.75rem;color:#6B7280;margin-top:.4rem">{hint}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

            _score_card(sc1, "ASD severity",
                        sev["severity_overall"],
                        _sev_color(sev["severity_overall"]),
                        "0 = no risk · 10 = highest risk")
            _score_card(sc2, "Communication strength",
                        sev["communication_strength"],
                        _sev_color(sev["communication_strength"], reverse=True),
                        "↑ MLU, TTR, words, questions")
            _score_card(sc3, "ASD-marker burden",
                        sev["marker_burden"],
                        _sev_color(sev["marker_burden"]),
                        "↑ echolalia, unintelligible, 0-vocal")
            st.caption(
                "Scores are derived from your dataset's z-scores via "
                "sigmoid mapping (5 = population mean). Inspired by "
                "Eni et al. (2025) *ASDSpeech* — graded scoring is more "
                "useful clinically than binary yes/no."
            )

            # --- Multi-modal fusion (speech + parent concern checklist) ---
            n_answered = sum(1 for a in checklist_answers if a)
            if n_answered >= 5:
                n_concerning, checklist_score = parent_checklist_severity(checklist_answers)
                combined = fuse_severity(
                    sev["severity_overall"], checklist_score, w_speech=0.5,
                )
                st.markdown("#### 🔗 Multi-modal severity (speech + parent concern)")
                mc1, mc2, mc3 = st.columns(3)
                _score_card(
                    mc1, "Speech-only",
                    sev["severity_overall"],
                    _sev_color(sev["severity_overall"]),
                    "from CHAT features",
                )
                _score_card(
                    mc2, "Parent concern",
                    float(checklist_score),
                    _sev_color(float(checklist_score)),
                    f"{n_concerning}/10 concerning answers",
                )
                _score_card(
                    mc3, "Combined (50/50)",
                    combined,
                    _sev_color(combined),
                    "late-fusion average",
                )
                st.caption(
                    f"คุณตอบ {n_answered}/10 ข้อ — ระบบรวม speech severity "
                    "กับ parent concern checklist ด้วย late-fusion (Abbas et al. 2020, "
                    "Megerian et al. 2022). หลายโมดอล signals = แม่นยำขึ้น"
                )
            elif n_answered > 0:
                info_box(
                    f"ตอบ parent checklist เพียง {n_answered}/10 ข้อ — "
                    "ต้องตอบอย่างน้อย 5 ข้อจึงจะคำนวณ multi-modal score",
                    kind="warn",
                )

            # --- Per-prediction explanation (SHAP-equivalent for LogReg) ---
            # For a linear model with standardised features:
            #   logit(P) = intercept + sum_i (coef_i * x_scaled_i)
            # so each (coef_i * x_scaled_i) is the SHAP value of feature i.
            st.markdown("#### 🔍 ทำไม AI ทำนายแบบนี้?")
            st.caption(
                "SHAP-equivalent contribution ของแต่ละ feature ต่อ log-odds "
                "(สำหรับ Logistic Regression: coef × standardised value)"
            )
            imp = model.named_steps["imp"]
            sc = model.named_steps["sc"]
            clf = model.named_steps["clf"]
            x_imp = imp.transform(x)
            x_scaled = sc.transform(x_imp)[0]
            contribs = clf.coef_[0] * x_scaled
            intercept = float(clf.intercept_[0])

            order = np.argsort(np.abs(contribs))
            f_sorted = [FEATURES[i] for i in order]
            c_sorted = contribs[order]
            x_sorted = x[0][order]

            shap_colors = [COLORS["ASD"] if v > 0 else COLORS["TD"]
                           for v in c_sorted]
            hover = [
                f"{f}: input={xv:.2f}<br>contribution={cv:+.3f}"
                for f, xv, cv in zip(f_sorted, x_sorted, c_sorted)
            ]
            shap_fig = go.Figure(go.Bar(
                x=c_sorted, y=f_sorted, orientation="h",
                marker_color=shap_colors,
                text=[f"{v:+.2f}" for v in c_sorted],
                textposition="outside",
                hovertext=hover, hoverinfo="text",
            ))
            shap_fig.update_layout(
                xaxis_title="Contribution to log-odds (ASD)",
                yaxis_title="",
                height=380,
            )
            st.plotly_chart(style_fig(shap_fig),
                            width='stretch', config=st_chart_cfg)

            logit = intercept + float(contribs.sum())
            st.caption(
                f"intercept = {intercept:+.2f}  ·  "
                f"sum(contributions) = {contribs.sum():+.2f}  ·  "
                f"logit = {logit:+.2f}  →  P(ASD) = {prob:.1%}"
            )
        else:
            st.markdown(
                '<div style="padding:2rem;text-align:center;color:#9CA3AF">'
                "Fill in the form and click **Predict risk** "
                "to see the AI prediction.</div>",
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("")
    section_label("Model interpretation")
    st.markdown("### Which features drive the prediction?")
    coef = model.named_steps["clf"].coef_[0]
    coef_df = pd.DataFrame({"feature": FEATURES, "coefficient": coef.round(3)})
    coef_df = coef_df.reindex(
        coef_df["coefficient"].abs().sort_values(ascending=True).index
    )
    colors = [COLORS["ASD"] if v > 0 else COLORS["TD"] for v in coef_df["coefficient"]]
    fig = go.Figure(go.Bar(
        x=coef_df["coefficient"], y=coef_df["feature"], orientation="h",
        marker_color=colors,
        text=coef_df["coefficient"].round(2), textposition="outside",
    ))
    fig.update_layout(xaxis_title="Coefficient (standardized)",
                      yaxis_title="")
    st.plotly_chart(style_fig(fig, height=420),
                    width='stretch', config=st_chart_cfg)
    st.caption(
        f'<span style="color:{COLORS["ASD"]}">■</span> Positive ⇒ feature สูง ผลัก prediction → ASD &nbsp;·&nbsp;'
        f'<span style="color:{COLORS["TD"]}">■</span> Negative ⇒ feature สูง ผลัก prediction → non-ASD',
        unsafe_allow_html=True,
    )


def page_audio_upload(df: pd.DataFrame) -> None:
    """End-to-end audio pipeline: .wav -> Whisper -> .cha -> features -> prediction."""
    hero(
        "🎤 Audio Assessment",
        "อัปโหลดเสียงบันทึก session ของเด็ก → AI ถอดเสียง + สกัด features + ทำนาย ASD risk",
        tags=["Whisper ASR", "TH+EN code-switch", "ECAPA speaker embedding",
              "End-to-end", "Echolalia detection", "Severity scoring"],
    )

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📤 Upload session audio")
    st.caption(
        "รองรับ `.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`. "
        "แนะนำบันทึกในห้องเงียบ 15–30 นาที โดยมีเด็ก + ผู้ใหญ่ 1 คน (2-speaker setup)"
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
        help=(
            "tiny: เร็วสุด · base: เบา · "
            "**small** (default): สมดุลตรงสำหรับ child speech & Thai · "
            "medium: แม่นสุด แต่ช้า 3x บน CPU"
        ),
    )
    strategy = c3.selectbox(
        "Language",
        ["auto", "english", "thai", "dual_pass", "thai_specialized"],
        index=0,
        format_func=lambda s: {
            "auto": "Auto-detect",
            "english": "English only",
            "thai": "Thai only",
            "dual_pass": "Dual-pass EN+TH (best)",
            "thai_specialized": "Thai-specialized model",
        }[s],
        help=(
            "เลือก strategy: auto=Whisper detect · dual_pass=รันสองรอบเลือกตัวชนะ · "
            "thai_specialized=ใช้ Thai-fine-tuned model (ดาวน์โหลดครั้งแรก)"
        ),
    )
    c4.markdown('<div style="padding-top:1.6rem"></div>', unsafe_allow_html=True)
    run_btn = c4.button("🚀 Run pipeline", width='stretch', type="primary",
                        disabled=audio_file is None)

    # Optional metadata
    with st.expander("📋 Child metadata (optional — kept in CHAT header)"):
        mc1, mc2, mc3, mc4 = st.columns(4)
        child_id = mc1.text_input("Child ID", value="CHI001")
        child_age = mc2.number_input("Age (months)", 0.0, 120.0, 48.0, step=1.0)
        child_sex = mc3.selectbox("Sex", ["", "male", "female"], index=0)
        child_group = mc4.selectbox("Group", ["ASD", "TD", "DD"], index=0)

    # Speaker enrollment (optional, boosts diarization accuracy)
    with st.expander("🎙️ Speaker enrollment (optional — บูสต์ความแม่น child detection)"):
        st.caption(
            "อัปไฟล์เสียงเด็กสั้น ๆ (5-10 วินาที) เช่น เด็กพูดชื่อตัวเอง — ระบบจะจับคู่กับ cluster ที่ใช่เด็กอัตโนมัติ ผ่าน ECAPA-TDNN embedding"
        )
        enrollment_file = st.file_uploader(
            "Child reference audio",
            type=["wav", "mp3", "m4a", "flac", "ogg"],
            label_visibility="collapsed",
            key="enrollment_audio",
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # Use session_state so the result survives reruns triggered by the
    # post-edit data_editor; only re-run the pipeline when the user
    # clicks "Run pipeline" again.
    audio_signature = None
    if audio_file is not None:
        audio_signature = (audio_file.name, getattr(audio_file, "size", 0),
                            model_size, strategy)
    cached_sig = st.session_state.get("audio_pipe_sig")
    cached_result = st.session_state.get("audio_pipe_result")
    cached_tmp_audio = st.session_state.get("audio_pipe_tmp_audio")
    cached_tmp_cha = st.session_state.get("audio_pipe_tmp_cha")
    cached_meta = st.session_state.get("audio_pipe_meta", {})

    have_cached = (
        cached_sig == audio_signature
        and cached_result is not None
        and cached_tmp_cha is not None
        and Path(cached_tmp_cha).exists()
    )

    if not run_btn and not have_cached:
        st.info(
            "💡 **วิธีใช้:** อัปโหลด session audio → กด Run pipeline → ระบบจะ:\n\n"
            "1. ถอดเสียงด้วย **Whisper** (word-level timestamps + confidence · TH+EN code-switching)\n"
            "2. แยกผู้พูด child vs adult ด้วย **ECAPA-TDNN embedding** (no HF token)\n"
            "3. สร้าง **CHAT transcript** (.cha) ตามมาตรฐาน TalkBank + CHATTER validate\n"
            "4. สกัด **13 features** (MLU, TTR, unintelligible rate, echolalia, ...) \n"
            "5. ทำนาย **ASD risk** ด้วย Logistic Regression (AUC 0.931)"
        )
        return
    if audio_file is None and not have_cached:
        return

    if run_btn or not have_cached:
        # --- Run pipeline ---
        with st.spinner(f"กำลังประมวลผลเสียงด้วย Whisper-{model_size}... "
                        "(อาจใช้เวลา 1-3 นาที ขึ้นกับความยาวของไฟล์)"):
            try:
                # Save uploaded file to a temp location the pipeline can read
                suffix = Path(audio_file.name).suffix or ".wav"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
                    tf.write(audio_file.read())
                    tmp_audio = Path(tf.name)

                tmp_cha = tmp_audio.with_suffix(".cha")

                # Save enrollment file if provided
                tmp_enrollment = None
                if enrollment_file is not None:
                    en_suffix = Path(enrollment_file.name).suffix or ".wav"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=en_suffix) as ef:
                        ef.write(enrollment_file.read())
                        tmp_enrollment = Path(ef.name)

                from src.audio_pipeline import audio_to_cha  # lazy import

                result = audio_to_cha(
                    tmp_audio,
                    output_path=tmp_cha,
                    model_size=model_size,
                    strategy=strategy,
                    prefer_pyannote=False,   # keep the dashboard dependency-light
                    enrollment_audio_path=tmp_enrollment,
                    child_id=child_id,
                    child_age_months=child_age if child_age > 0 else None,
                    child_sex=child_sex or None,
                    child_group=child_group,
                )
            except ImportError as e:
                st.error(
                    f"**Audio pipeline dependencies missing.**\n\n{e}\n\n"
                    "Install with: `pip install faster-whisper librosa soundfile`"
                )
                return
            except Exception as e:  # noqa: BLE001
                st.error(f"Pipeline failed: {e}")
                return

        # Cache for subsequent reruns triggered by the post-edit table
        st.session_state["audio_pipe_sig"] = audio_signature
        st.session_state["audio_pipe_result"] = result
        st.session_state["audio_pipe_tmp_audio"] = tmp_audio
        st.session_state["audio_pipe_tmp_cha"] = tmp_cha
        st.session_state["audio_pipe_meta"] = {
            "child_id": child_id, "child_age": child_age,
            "child_sex": child_sex, "child_group": child_group,
        }
    else:
        result = cached_result
        tmp_audio = Path(cached_tmp_audio)
        tmp_cha = Path(cached_tmp_cha)
        # Restore metadata that drives downstream rendering
        child_id = cached_meta.get("child_id", child_id)
        child_age = cached_meta.get("child_age", child_age)
        child_sex = cached_meta.get("child_sex", child_sex)
        child_group = cached_meta.get("child_group", child_group)

    # --- Stats ---
    section_label("Pipeline output")
    c1, c2, c3, c4 = st.columns(4)
    metric_card(c1, "Duration", f"{result.total_duration_sec:.0f} s", "audio length")
    metric_card(c2, "Child utterances",
                f"{result.n_child_utterances}", "*CHI: lines", flavor="accent")
    metric_card(c3, "Adult utterances",
                f"{result.n_adult_utterances}", "*MOT: lines", flavor="td")
    metric_card(c4, "Total segments",
                f"{result.n_child_utterances + result.n_adult_utterances}",
                "Whisper segments")

    if result.n_child_utterances == 0:
        st.warning(
            "⚠️ ไม่พบ child speech — ลองใช้ model ใหญ่ขึ้น (`small`) หรือตรวจสอบว่า "
            "audio มีเสียงเด็กจริง ๆ (pitch heuristic ต้องการ F0 > 230Hz)"
        )

    # --- Quality report (language mix + CHATTER validation) ---
    _utts = result.utterances or []
    _lang_counts: dict[str, int] = {}
    for _u in _utts:
        _lang_counts[(_u.language or "?")] = _lang_counts.get(_u.language or "?", 0) + 1
    _quality_bits: list[str] = []
    if _lang_counts:
        _total = sum(_lang_counts.values())
        _lang_str = " · ".join(
            f"{k}: {v / _total:.0%}" for k, v in sorted(_lang_counts.items())
        )
        _quality_bits.append(f"**Language mix:** {_lang_str}")
    _v = result.validation
    if _v is not None:
        if _v.skipped:
            _quality_bits.append(f"**CHATTER:** skipped ({_v.skip_reason})")
        elif _v.ok:
            _quality_bits.append(
                f"**CHATTER:** ✅ passed (auto-fixed {_v.fixed_count})"
            )
        else:
            _quality_bits.append(
                f"**CHATTER:** ⚠️ {_v.n_errors} error(s), "
                f"{_v.n_warnings} warning(s) (auto-fixed {_v.fixed_count})"
            )
    if _quality_bits:
        st.caption(" · ".join(_quality_bits))
        if _v is not None and not _v.skipped and not _v.ok:
            with st.expander("🔍 CHATTER issues"):
                for _iss in (_v.errors + _v.warnings)[:50]:
                    st.text(str(_iss))

    # --- Two tabs: features+prediction vs raw CHAT ---
    tab_pred, tab_cha, tab_segs = st.tabs(
        ["🩺 Features + Prediction", "📄 CHAT transcript", "🔊 Segments"]
    )

    # ---- Tab 1: feed through data_loader + classifier ----
    with tab_pred:
        try:
            from src.data_loader import _extract_features  # lazy import
            feats = _extract_features(tmp_cha)
        except Exception as e:  # noqa: BLE001
            st.error(f"Feature extraction failed: {e}")
            feats = None

        if feats is None:
            st.error(
                "ไม่สามารถสกัด features ได้ (อาจเพราะ child utterances ว่างเปล่า)"
            )
        else:
            # Build a single-row DataFrame matching training columns
            feat_row = {k: feats.get(k) for k in FEATURES}
            feat_row["age_months"] = child_age if child_age > 0 else feats.get("age_months")
            feat_df = pd.DataFrame([feat_row])

            st.markdown("#### Extracted features")
            st.dataframe(feat_df, width='stretch', hide_index=True)

            # Predict
            model = train_screening_model(df)
            try:
                X = feat_df[FEATURES].values
                prob_asd = float(model.predict_proba(X)[0, 1])
                _label_full, _kind, color = classify_risk(prob_asd)
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
                            ⚠️ นี่เป็น screening tool — ไม่ใช่ diagnostic.
                            ผลต้องได้รับการยืนยันจากแพทย์ผู้เชี่ยวชาญ
                        </div>
                       </div>""",
                    unsafe_allow_html=True,
                )
            except Exception as e:  # noqa: BLE001
                st.error(f"Prediction failed: {e}")

            # Download button for the CSV row (integrates with batch analysis later)
            st.download_button(
                "⬇️ Download features (CSV)",
                data=feat_df.to_csv(index=False).encode("utf-8"),
                file_name=f"{child_id}_features.csv",
                mime="text/csv",
            )

    # ---- Tab 2: raw CHAT ----
    with tab_cha:
        st.code(result.chat_text, language="text")
        st.download_button(
            "⬇️ Download .cha",
            data=result.chat_text.encode("utf-8"),
            file_name=f"{child_id}.cha",
            mime="text/plain",
        )

    # ---- Tab 3: editable post-edit table ----
    with tab_segs:
        st.markdown("#### ✏️ Post-edit transcript")
        st.caption(
            "แก้ speaker / ภาษา / ข้อความ / ลบ segment ที่ผิด → กด **Re-export .cha** "
            "เพื่อสร้างไฟล์ใหม่และคำนวณ features ใหม่"
        )

        # Build editable DataFrame; min word confidence per segment as quality flag
        seg_rows = []
        for i, u in enumerate(result.utterances):
            min_conf = (
                min((w.probability for w in u.words), default=1.0)
                if u.words else 1.0
            )
            seg_rows.append({
                "delete": False,
                "start (s)": round(u.start, 2),
                "end (s)": round(u.end, 2),
                "speaker": u.speaker or "MOT",
                "lang": (u.language or "").lower(),
                "min_conf": round(min_conf, 2),
                "n_words": len(u.words),
                "text": u.text,
            })
        seg_df = pd.DataFrame(seg_rows)

        edited = st.data_editor(
            seg_df,
            width='stretch',
            hide_index=True,
            num_rows="fixed",
            column_config={
                "delete": st.column_config.CheckboxColumn(
                    "🗑️", help="Mark to delete on Re-export"),
                "speaker": st.column_config.SelectboxColumn(
                    "speaker",
                    options=["CHI", "MOT", "FAT", "INV", "SIS", "GRA"],
                    required=True,
                ),
                "lang": st.column_config.SelectboxColumn(
                    "lang",
                    options=["", "en", "th"],
                ),
                "min_conf": st.column_config.NumberColumn(
                    "min conf", format="%.2f",
                    help="Lowest word-level confidence in this segment",
                ),
                "text": st.column_config.TextColumn(
                    "text", width="large",
                ),
                "start (s)": st.column_config.NumberColumn(disabled=True),
                "end (s)": st.column_config.NumberColumn(disabled=True),
                "n_words": st.column_config.NumberColumn(disabled=True),
            },
            key="seg_editor",
        )

        ec1, ec2 = st.columns([1, 4])
        re_export = ec1.button("💾 Re-export .cha", type="primary",
                               width='stretch', key="re_export_btn")

        if re_export:
            from src.audio_pipeline.chat_formatter import utterances_to_chat
            from src.audio_pipeline.chatter_validator import validate_chat_file
            # Apply edits back to the utterance objects
            new_utts = []
            for i, row in edited.iterrows():
                if row["delete"]:
                    continue
                u = result.utterances[i]
                u.speaker = row["speaker"]
                u.language = row["lang"] or u.language
                u.text = row["text"]
                # The original word-level timings are kept; text-only edits
                # won't update them but the CHAT body uses .text when words
                # are missing.
                new_utts.append(u)

            new_chat = utterances_to_chat(
                new_utts,
                child_id=child_id,
                child_age_months=child_age if child_age > 0 else None,
                child_sex=child_sex or None,
                child_group=child_group,
                media_filename=tmp_audio.name,
            )
            tmp_cha.write_text(new_chat, encoding="utf-8")
            new_report = validate_chat_file(
                tmp_cha, auto_fix_first=True, save_fixed=True,
            )

            st.success(
                f"✅ Re-exported {len(new_utts)} utterances "
                f"({len(result.utterances) - len(new_utts)} deleted) · "
                f"{new_report.summary()}"
            )
            st.code(tmp_cha.read_text(encoding="utf-8"), language="text")
            st.download_button(
                "⬇️ Download edited .cha",
                data=tmp_cha.read_text(encoding="utf-8").encode("utf-8"),
                file_name=f"{child_id}_edited.cha",
                mime="text/plain",
                key="dl_edited_cha",
            )

    st.markdown("---")
    if st.button("Delete cached audio/transcript for this session", type="secondary"):
        for key in ("audio_pipe_tmp_audio", "audio_pipe_tmp_cha"):
            cached_path = st.session_state.get(key)
            if cached_path:
                Path(cached_path).unlink(missing_ok=True)
        for key in (
            "audio_pipe_sig", "audio_pipe_result", "audio_pipe_tmp_audio",
            "audio_pipe_tmp_cha", "audio_pipe_meta",
        ):
            st.session_state.pop(key, None)
        st.success("Deleted cached temporary audio/transcript files for this session.")

    st.caption(
        "Privacy note: temporary files are kept only so the segment editor survives "
        "Streamlit reruns. Use the delete button above after review, especially for "
        "child audio or identifiable transcripts."
    )


def page_progress(longitudinal: pd.DataFrame) -> None:
    hero(
        "📈 Progress Tracker",
        "ติดตามพัฒนาการของเด็ก ASD ตลอดหลาย sessions ของการบำบัด",
        tags=["Longitudinal tracking", f"{longitudinal['child'].nunique()} children", f"{len(longitudinal)} sessions", "Rollins + Flusberg"],
    )

    children = sorted(longitudinal["child"].unique())
    scored = _compute_composite(longitudinal)

    # Summary cards
    section_label("Children")
    st.markdown("### Per-child summary")
    cols = st.columns(len(children))
    for col, c in zip(cols, children):
        g = scored[scored["child"] == c].sort_values("session_order")
        first = g["composite_score"].iloc[0]
        last = g["composite_score"].iloc[-1]
        delta = last - first
        emoji = "📈" if delta > 0 else "📉"
        metric_card(
            col, f"{emoji} {c}", f"{last:+.2f}",
            f"Δ {delta:+.2f} over {len(g)} sessions",
            flavor="td" if delta > 0 else "asd",
        )

    st.markdown("")

    tab1, tab2, tab3 = st.tabs(
        ["📊 Feature trajectories", "🎯 Composite score", "📋 First vs last"]
    )

    with tab1:
        c1, c2 = st.columns([1.2, 2.5])
        picked_c = c1.multiselect("Children", children, default=children)
        feats_for_plot = ["mlu", "mluw", "ttr", "total_words",
                          "unintelligible_ratio", "zero_vocalization_count",
                          "total_utterances"]
        feat = c1.selectbox("Feature", feats_for_plot, index=0)
        sub = longitudinal[longitudinal["child"].isin(picked_c)]
        fig = px.line(
            sub, x="session_order", y=feat, color="child",
            markers=True, line_shape="spline",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(line_width=3, marker_size=10)
        fig.update_layout(xaxis_title="Session", yaxis_title=feat)
        c2.plotly_chart(style_fig(fig, height=440),
                        width='stretch', config=st_chart_cfg)

    with tab2:
        picked_c = st.multiselect("Children", children, default=children,
                                   key="comp_children")
        sub = scored[scored["child"].isin(picked_c)]
        fig = px.line(
            sub, x="session_order", y="composite_score",
            color="child", markers=True, line_shape="spline",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(line_width=3, marker_size=12)
        fig.add_hline(y=0, line_dash="dash", line_color=COLORS["muted"],
                      annotation_text="cohort mean",
                      annotation_position="bottom right")
        fig.update_layout(
            xaxis_title="Session order",
            yaxis_title="Composite score (higher = better)",
        )
        st.plotly_chart(style_fig(fig, height=480),
                        width='stretch', config=st_chart_cfg)

        info_box(
            "**Composite score** คือค่าเฉลี่ยของ 7 features ที่ z-scored "
            "แล้วปรับทิศทาง (สูง=ดี เช่น mlu, ttr, total_words  ·  "
            "ต่ำ=ดี เช่น unintelligible_ratio, zero_vocalization)",
        )

    with tab3:
        feats_for_plot = ["mlu", "mluw", "ttr", "total_words",
                          "unintelligible_ratio", "zero_vocalization_count",
                          "composite_score"]
        rows = []
        for c, g in scored.groupby("child"):
            g = g.sort_values("session_order")
            for f in feats_for_plot:
                delta = g[f].iloc[-1] - g[f].iloc[0]
                rows.append({
                    "child": c, "feature": f,
                    "first": round(g[f].iloc[0], 3),
                    "last": round(g[f].iloc[-1], 3),
                    "delta": round(delta, 3),
                    "improved": "✅" if (
                        (delta > 0 and f not in
                         ("unintelligible_ratio", "zero_vocalization_count"))
                        or (delta < 0 and f in
                            ("unintelligible_ratio", "zero_vocalization_count"))
                    ) else "❌",
                })
        st.dataframe(pd.DataFrame(rows),
                     width='stretch', hide_index=True)


# ===========================================================================
# MAIN
# ===========================================================================
NAV_PAGES = {
    "👨‍👩‍👧  Parent public demo": "parent",
    "📊  Overview":          "overview",
    "📘  Feature reference": "features",
    "🔎  EDA":               "eda",
    "🩺  Screening tool":    "screening",
    "🎤  Audio assessment":  "audio",
    "📈  Progress tracker":  "progress",
}


def main() -> None:
    st.set_page_config(
        page_title="ASD Assessment Dashboard",
        page_icon="🧩",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    df = load_combined()
    longitudinal = load_longitudinal()

    # Sidebar
    with st.sidebar:
        st.markdown(
            '<div style="padding:0.5rem 0 1rem 0">'
            '<div style="font-size:2rem">🧩</div>'
            '<div style="font-weight:800;font-size:1.1rem;line-height:1.2">'
            'ASD Assessment</div>'
            '<div style="color:#6C757D;font-size:0.85rem">'
            'AI-assisted clinical tool</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")
        selected = st.radio(
            "Navigate",
            list(NAV_PAGES.keys()),
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.markdown(
            '<div style="color:#6C757D;font-size:0.8rem">'
            '<b>Dataset</b><br>'
            f'{len(df)} children · {len(longitudinal)} longitudinal sessions'
            "</div>",
            unsafe_allow_html=True,
        )
        with st.expander("⚙️  Pipeline commands"):
            st.code(
                "python src/data_loader.py\n"
                "python src/eda.py\n"
                "python src/classifier.py\n"
                "python src/deep_learning.py\n"
                "python src/progress_tracking.py",
                language="bash",
            )

    page = NAV_PAGES[selected]
    if page == "parent":
        page_parent_public()
    elif page == "overview":
        page_overview(df, longitudinal)
    elif page == "features":
        page_feature_ref(df)
    elif page == "eda":
        page_eda(df)
    elif page == "screening":
        page_screening(df)
    elif page == "audio":
        page_audio_upload(df)
    elif page == "progress":
        page_progress(longitudinal)


if __name__ == "__main__":
    main()
