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
    "pink": "#FF8FB3",
    "blue": "#8EC5FF",
    "green": "#9BE7C2",
    "yellow": "#FFE28A",
    "TD": "#9BE7C2",
    "DD": "#FFE28A",
    "ASD": "#FF8FB3",
    "primary": "#FF8FB3",
    "accent": "#8EC5FF",
    "muted": "#64748B",
    "line": "#E9EDF5",
    "bg_card": "#FFFFFF",
    "bg_soft": "#FAFBFF",
    "text": "#0F172A",
}

PASTEL_SEQUENCE = [
    COLORS["pink"],
    COLORS["blue"],
    COLORS["green"],
    COLORS["yellow"],
    "#C7B8FF",
    "#FFC6A8",
]
PASTEL_CONTINUOUS_SCALE = [
    [0.0, "#8EC5FF"],
    [0.5, "#FFFFFF"],
    [1.0, "#FF8FB3"],
]

PLOTLY_TEMPLATE = "plotly_white"
ST_CHART_CONFIG = {"displayModeBar": False}


# ---------------------------------------------------------------------------
# CSS injection: project_dashboard/styles.css tokens ported for Streamlit
# ---------------------------------------------------------------------------
CSS = """
<style>
:root {
  color-scheme: light;
  --bg: #fbfcff;
  --bg-soft: #f7f9ff;
  --panel: #ffffff;
  --sidebar: #ffffff;
  --sidebar-soft: #fff8fb;
  --line: rgba(15, 23, 42, 0.07);
  --line-strong: rgba(15, 23, 42, 0.12);
  --ink: #0f172a;
  --muted: #64748b;
  --muted-soft: #94a3b8;
  --pink: #ff8fb3;
  --pink-soft: #fff0f6;
  --blue: #8ec5ff;
  --blue-soft: #edf6ff;
  --green: #9be7c2;
  --green-soft: #effcf6;
  --yellow: #ffe28a;
  --yellow-soft: #fff9df;
  --coral: var(--pink);
  --amber: var(--yellow);
  --lavender: #c7b8ff;
  --peach: #ffc6a8;
  --shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
  --shadow-soft: 0 10px 28px rgba(15, 23, 42, 0.055);
  --radius: 22px;
  --radius-sm: 16px;
  --font-stack: Inter, "Noto Sans Thai", ui-sans-serif, system-ui, -apple-system,
    BlinkMacSystemFont, "Segoe UI", sans-serif;
}

* { box-sizing: border-box; }

html { scroll-behavior: smooth; }

.stApp {
  color: var(--ink);
  background:
    radial-gradient(circle at 8% 5%, rgba(255, 143, 179, 0.14), transparent 24rem),
    radial-gradient(circle at 92% 2%, rgba(142, 197, 255, 0.18), transparent 28rem),
    linear-gradient(180deg, #ffffff 0%, var(--bg) 48%, #ffffff 100%);
  font-family: var(--font-stack);
  line-height: 1.5;
}

.block-container {
  max-width: 1380px;
  padding-top: 1.15rem;
  padding-bottom: 3rem;
}

h1, h2, h3, h4, p { margin-top: 0; }
h1, h2, h3, h4 { color: var(--ink); letter-spacing: 0; }
h1 { margin-bottom: 6px; font-size: 2.05rem; line-height: 1.1; font-weight: 850; }
h2 { margin-bottom: 4px; font-size: 1.18rem; line-height: 1.2; font-weight: 780; }
h3 { font-size: 1.02rem; font-weight: 760; }
p, .stCaptionContainer, .muted { color: var(--muted); }

button, input, select, textarea {
  font: inherit;
  max-width: 100%;
}

a { color: inherit; text-decoration: none; }
img { display: block; max-width: 100%; }

.dashboard-topbar {
  display: grid;
  grid-template-columns: minmax(180px, 0.8fr) minmax(280px, 1.15fr) auto;
  align-items: center;
  gap: 16px;
  margin-bottom: 18px;
  padding: 12px 16px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(14px);
}

.topbar-kicker {
  color: var(--pink);
  font-size: 0.72rem;
  font-weight: 850;
  letter-spacing: 0.11em;
  text-transform: uppercase;
}

.topbar-title {
  margin-top: 3px;
  color: var(--ink);
  font-size: 1rem;
  font-weight: 840;
}

.topbar-search {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 42px;
  padding: 0 14px;
  border: 1px solid var(--line);
  border-radius: 15px;
  color: var(--muted);
  background: var(--bg-soft);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.88);
}

.topbar-search span:first-child,
.topbar-action {
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 10px;
  color: var(--pink);
  background: var(--pink-soft);
  font-weight: 900;
  flex: 0 0 auto;
}

.topbar-profile {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  min-width: 230px;
}

.topbar-action {
  color: var(--ink);
  background: #ffffff;
  border: 1px solid var(--line);
}

.profile-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 0 5px var(--green-soft);
}

.profile-copy strong,
.profile-copy small {
  display: block;
  line-height: 1.2;
  white-space: nowrap;
}

.profile-copy small { color: var(--muted); font-size: 0.76rem; }

.hero {
  margin-bottom: 22px;
  padding: 28px 30px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  color: var(--ink);
  background:
    radial-gradient(circle at 82% 10%, rgba(255, 226, 138, 0.34), transparent 18rem),
    radial-gradient(circle at 8% 0%, rgba(255, 143, 179, 0.24), transparent 16rem),
    linear-gradient(135deg, #ffffff 0%, #fff8fb 45%, #eef7ff 100%);
  box-shadow: var(--shadow);
  position: relative;
  overflow: hidden;
}

.hero h1 {
  margin: 0 0 8px;
  color: var(--ink);
  font-size: 2.05rem !important;
  line-height: 1.12 !important;
  letter-spacing: 0 !important;
}

.hero .sub {
  max-width: 72rem;
  color: var(--muted);
  font-size: 1rem;
  line-height: 1.62;
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
  padding: 0 11px;
  color: #9f315e;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(255, 143, 179, 0.2);
  box-shadow: 0 7px 18px rgba(255, 143, 179, 0.12);
}

.section-label {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  margin-bottom: 8px;
  padding: 0 9px;
  border-radius: 999px;
  color: #9f315e;
  background: var(--pink-soft);
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
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr);
  align-items: center;
  gap: 16px;
  min-height: 120px;
  padding: 20px;
  overflow: hidden;
  border-left: 0;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}

.metric-card.compact {
  grid-template-columns: 1fr;
  align-content: start;
  justify-items: start;
  gap: 12px;
  min-height: 150px;
  padding: 18px;
}

.metric-card:hover {
  border-color: rgba(255, 143, 179, 0.2);
  box-shadow: 0 22px 52px rgba(15, 23, 42, 0.095);
  transform: translateY(-1px);
}

.metric-card::after {
  content: "";
  position: absolute;
  inset: auto -34px -40px auto;
  width: 110px;
  height: 110px;
  border-radius: 50%;
  background: rgba(142, 197, 255, 0.16);
  pointer-events: none;
}

.metric-icon {
  display: inline-grid;
  place-items: center;
  width: 54px;
  height: 54px;
  border-radius: 16px;
  color: #9f315e;
  background: linear-gradient(135deg, var(--pink-soft), rgba(255, 143, 179, 0.46));
  font-size: 0.82rem;
  font-weight: 900;
  letter-spacing: 0.03em;
}

.metric-body {
  min-width: 0;
  width: 100%;
  position: relative;
  z-index: 1;
}

.metric-card.accent .metric-icon {
  color: #1e5d95;
  background: linear-gradient(135deg, var(--blue-soft), rgba(142, 197, 255, 0.55));
}

.metric-card.td .metric-icon {
  color: #15734a;
  background: linear-gradient(135deg, var(--green-soft), rgba(155, 231, 194, 0.62));
}

.metric-card.dd .metric-icon {
  color: #7a5600;
  background: linear-gradient(135deg, var(--yellow-soft), rgba(255, 226, 138, 0.72));
}

.metric-card.asd .metric-icon {
  color: #9f315e;
  background: linear-gradient(135deg, var(--pink-soft), rgba(255, 143, 179, 0.58));
}

.metric-card .label {
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.25;
  font-weight: 850;
  letter-spacing: 0.02em;
  overflow-wrap: normal;
  word-break: normal;
  hyphens: none;
}

.metric-card .value {
  display: block;
  margin: 6px 0 4px;
  color: var(--ink);
  font-size: clamp(1.35rem, 1.8vw, 1.85rem);
  font-weight: 850;
  line-height: 1;
}

.metric-card .delta {
  max-width: 28ch;
  color: var(--muted);
  font-size: 0.82rem;
  line-height: 1.35;
  overflow-wrap: normal;
  word-break: normal;
  hyphens: none;
}

.metric-card.compact .metric-icon {
  width: 50px;
  height: 50px;
  border-radius: 15px;
}

.metric-card.compact .label {
  min-height: 2.45em;
}

.metric-card.compact .value {
  font-size: 1.6rem;
}

.metric-card.compact .delta {
  max-width: 100%;
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

.card h1,
.card h2,
.card h3,
.panel h1,
.panel h2,
.panel h3 {
  line-height: 1.22 !important;
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
  padding: 14px 16px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  color: var(--ink);
  background: var(--bg-soft);
}

.info-box { border-left: 4px solid var(--blue); background: var(--blue-soft); }
.warn-box { border-left: 4px solid var(--yellow); background: var(--yellow-soft); }
.success-box { border-left: 4px solid var(--green); background: var(--green-soft); }

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
  border: 1px solid rgba(15, 23, 42, 0.04);
}

.chip-td,
.ok-pill {
  color: #15734a;
  background: var(--green-soft);
}

.chip-dd,
.warn-pill {
  color: #7a5600;
  background: var(--yellow-soft);
}

.chip-asd {
  color: #9f315e;
  background: var(--pink-soft);
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
  border-radius: var(--radius-sm);
  background: var(--bg-soft);
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
  color: var(--pink);
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
  color: var(--ink);
  font-weight: 780;
  overflow-wrap: anywhere;
  line-height: 1.2;
}

.bar-track {
  height: 16px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--bg-soft);
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
  background: var(--sidebar);
  border-right: 1px solid var(--line);
  box-shadow: 10px 0 30px rgba(15, 23, 42, 0.035);
}

section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] small {
  color: var(--muted);
}

section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
  justify-content: flex-start;
  width: 100%;
  min-height: 48px;
  padding: 0 16px;
  border: 1px solid transparent;
  border-radius: 16px;
  color: var(--ink);
  background: transparent;
  font-weight: 760;
  box-shadow: none;
  transition: transform 180ms ease, background 180ms ease, color 180ms ease, border-color 180ms ease;
}

section[data-testid="stSidebar"] button[kind="secondary"],
section[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] {
  justify-content: center !important;
  width: 100% !important;
  min-height: 48px !important;
  border: 1px solid var(--line-strong) !important;
  border-radius: 16px !important;
  color: var(--muted) !important;
  background: #ffffff !important;
  box-shadow: none !important;
}

section[data-testid="stSidebar"] button[kind="secondary"] p,
section[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] p {
  color: var(--muted) !important;
  font-weight: 760 !important;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
  color: #9f315e;
  border-color: rgba(255, 143, 179, 0.22);
  background: var(--pink-soft);
  transform: translateY(-1px);
}

section[data-testid="stSidebar"] button[kind="secondary"]:hover,
section[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover {
  border-color: rgba(255, 143, 179, 0.32) !important;
  background: var(--pink-soft) !important;
  color: #9f315e !important;
}

section[data-testid="stSidebar"] button[kind="secondary"]:hover p,
section[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover p {
  color: #9f315e !important;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] {
  color: #9f315e;
  border-color: rgba(255, 143, 179, 0.28);
  background: linear-gradient(135deg, var(--pink-soft), #fff7fb);
  box-shadow: 0 12px 24px rgba(255, 143, 179, 0.15);
}

section[data-testid="stSidebar"] button[kind="primary"],
section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
  justify-content: center !important;
  width: 100% !important;
  min-height: 48px !important;
  border: 1px solid rgba(255, 143, 179, 0.34) !important;
  border-radius: 16px !important;
  color: #9f315e !important;
  background: linear-gradient(135deg, var(--pink-soft), #fff7fb) !important;
  box-shadow: 0 12px 24px rgba(255, 143, 179, 0.15) !important;
}

section[data-testid="stSidebar"] button[kind="primary"] p,
section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] p {
  color: #9f315e !important;
  font-weight: 820 !important;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 13px;
  margin-bottom: 22px;
  padding: 6px 4px 12px;
  border-bottom: 1px solid var(--line);
}

.sidebar-brand strong {
  color: var(--ink);
  font-size: 1rem;
}

.brand-icon {
  display: inline-grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background:
    radial-gradient(circle at 30% 30%, #ffffff 0 11%, transparent 12%),
    radial-gradient(circle at 70% 30%, #ffffff 0 11%, transparent 12%),
    radial-gradient(circle at 30% 70%, #ffffff 0 11%, transparent 12%),
    radial-gradient(circle at 70% 70%, #ffffff 0 11%, transparent 12%),
    linear-gradient(135deg, var(--pink), var(--blue));
  color: #ffffff;
  font-weight: 850;
  box-shadow: 0 12px 24px rgba(255, 143, 179, 0.24);
}

.sidebar-card {
  margin-top: 24px;
  padding: 18px;
  border-radius: var(--radius);
  border: 1px solid rgba(255, 143, 179, 0.18);
  background:
    radial-gradient(circle at 92% 5%, rgba(255, 226, 138, 0.42), transparent 45%),
    linear-gradient(135deg, #fff7fb, #eff8ff);
  box-shadow: var(--shadow-soft);
}

.sidebar-card span {
  color: #9f315e;
  font-size: 0.78rem;
  font-weight: 850;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.sidebar-card strong {
  display: block;
  margin: 10px 0 8px;
  color: var(--ink);
}

[data-testid="stDataFrame"] {
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: #ffffff;
  box-shadow: var(--shadow-soft);
}

[data-testid="stPlotlyChart"] {
  overflow: hidden;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: rgba(255, 255, 255, 0.94);
  box-shadow: var(--shadow-soft);
}

[data-testid="stPlotlyChart"] .gtitle {
  display: none;
}

.stSelectbox [data-baseweb="select"],
.stMultiSelect [data-baseweb="select"],
.stNumberInput input,
.stTextInput input,
.stTextArea textarea {
  border-radius: 15px;
  border-color: var(--line) !important;
  background: #ffffff;
}

.stSlider [data-baseweb="slider"] > div {
  color: var(--pink);
}

.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
  border-radius: 16px;
  border: 1px solid rgba(255, 143, 179, 0.24);
  background: #ffffff;
  color: var(--ink);
  font-weight: 780;
  min-height: 44px;
  white-space: normal;
  box-shadow: var(--shadow-soft);
  transition: transform 160ms ease, background 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {
  border-color: rgba(255, 143, 179, 0.42);
  color: #9f315e;
  background: var(--pink-soft);
  transform: translateY(-1px);
}

.stButton > button:focus-visible,
.stDownloadButton > button:focus-visible,
.stFormSubmitButton > button:focus-visible {
  outline: 3px solid rgba(142, 197, 255, 0.45);
  outline-offset: 2px;
}

.stButton > button:disabled,
.stDownloadButton > button:disabled,
.stFormSubmitButton > button:disabled {
  color: var(--muted-soft);
  background: var(--bg-soft);
  border-color: var(--line);
  box-shadow: none;
  transform: none;
}

.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
  color: #ffffff;
  border-color: transparent;
  background: linear-gradient(135deg, var(--pink), #ffa8c7);
}

section[data-testid="stSidebar"] .stButton > button {
  color: var(--ink);
  border: 1px solid transparent;
  background: transparent;
  box-shadow: none;
}

section[data-testid="stSidebar"] .stButton > button:hover {
  color: #9f315e;
  border-color: rgba(255, 143, 179, 0.22);
  background: var(--pink-soft);
}

section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  color: #9f315e;
  border-color: rgba(255, 143, 179, 0.28);
  background: linear-gradient(135deg, var(--pink-soft), #fff7fb);
  box-shadow: 0 12px 24px rgba(255, 143, 179, 0.15);
}

.stTabs [data-baseweb="tab-list"] {
  gap: 0.35rem;
  border-bottom: 1px solid var(--line);
}

.stTabs [data-baseweb="tab"] {
  border-radius: 999px;
  padding: 0.5rem 1.1rem;
  background: transparent;
  min-height: 40px;
}

.stTabs [aria-selected="true"] {
  background: var(--pink-soft) !important;
  color: #9f315e !important;
  font-weight: 800;
}

code {
  padding: 0.12rem 0.35rem;
  border-radius: 8px;
  color: #1e5d95;
  background: var(--blue-soft);
  font-size: 0.9em;
}

pre {
  margin: 0;
  overflow-x: auto;
  padding: 18px;
  border-radius: var(--radius);
  color: var(--ink);
  background: #ffffff;
  border: 1px solid var(--line);
  font-size: 0.84rem;
  line-height: 1.55;
}

@keyframes soft-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(155, 231, 194, 0.32); }
  50% { box-shadow: 0 0 0 8px rgba(155, 231, 194, 0); }
}

.live-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--green);
  animation: soft-pulse 1.8s ease-in-out infinite;
}

@media (max-width: 1180px) {
  .dashboard-topbar {
    grid-template-columns: minmax(180px, 1fr) auto;
  }

  .topbar-profile {
    justify-content: flex-end;
    min-width: 0;
  }

  .topbar-search {
    grid-column: 1 / -1;
  }

  .metric-row,
  .grid-three {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .grid-two {
    grid-template-columns: 1fr;
  }
}

@media (min-width: 761px) and (max-width: 900px) {
  .metric-card {
    grid-template-columns: 1fr;
    align-content: start;
    gap: 12px;
    height: 196px;
    min-height: 196px;
    padding: 18px;
  }

  .metric-icon {
    width: 48px;
    height: 48px;
    border-radius: 14px;
  }

  .metric-card .label {
    min-height: 2.4em;
  }

  .metric-card .delta {
    max-width: 100%;
  }
}

@media (max-width: 760px) {
  .block-container {
    padding: 1rem 1rem 2.2rem !important;
  }

  h1 { font-size: 1.7rem !important; line-height: 1.15 !important; }
  h2 { font-size: 1.12rem !important; }
  h3 { font-size: 1rem !important; }

  .dashboard-topbar {
    grid-template-columns: 1fr;
    gap: 10px;
    margin-bottom: 14px;
    padding: 12px;
    border-radius: 18px;
  }

  .topbar-kicker {
    font-size: 0.68rem;
  }

  .topbar-title {
    font-size: 0.95rem;
  }

  .topbar-search {
    display: none;
  }

  .topbar-profile {
    justify-content: flex-start;
    gap: 9px;
  }

  .topbar-action {
    width: 34px;
    height: 34px;
    border-radius: 12px;
  }

  .profile-copy strong {
    white-space: normal;
    font-size: 0.9rem;
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
    padding: 20px;
    margin-bottom: 18px;
    border-radius: 20px;
  }

  .hero h1 {
    font-size: 1.75rem !important;
    line-height: 1.16 !important;
  }

  .hero .sub {
    font-size: 0.95rem;
    line-height: 1.56;
  }

  .hero .tags {
    gap: 7px;
    margin-top: 14px;
  }

  .hero .tag {
    min-height: 26px;
    max-width: 100%;
  }

  .metric-card {
    grid-template-columns: 48px minmax(0, 1fr);
    min-height: 112px;
    padding: 16px;
  }

  .metric-icon {
    width: 48px;
    height: 48px;
    border-radius: 14px;
    font-size: 0.76rem;
  }

  .card {
    padding: 18px;
    border-radius: 20px;
  }

  .stTabs [data-baseweb="tab-list"] {
    overflow-x: auto;
    flex-wrap: nowrap;
  }

  section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
    min-height: 44px;
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
    ("overview", "Dashboard", "Overview from real project data"),
    ("dataset", "Dataset", "Corpus and group composition"),
    ("features", "Features", "Language feature reference"),
    ("eda", "EDA", "Exploratory analysis"),
    ("screening", "Screening", "Risk scoring workflow"),
    ("trust", "Model Trust", "Validation and reliability"),
    ("transcript_qa", "Transcript QA", "Transcript review and reports"),
    ("assistant", "AI Therapist Assistant", "Safe therapist-facing summaries"),
    ("clinician_workflow", "Clinician Workflow", "Compact decision-support flow"),
    ("audio", "Audio", "Audio-to-assessment flow"),
    ("reports", "Reports", "Figures and paper outputs"),
    ("progress", "Progress", "Longitudinal tracking"),
    ("atlas", "Atlas", "Project map"),
]
PAGE_TITLES = {
    key: label for key, label, _help_text in NAV_ITEMS
}

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


def top_header(page: str) -> None:
    page_title = PAGE_TITLES.get(page, "Dashboard")
    st.markdown(
        f"""
        <div class="dashboard-topbar">
          <div>
            <div class="topbar-kicker">Bloomy style dashboard</div>
            <div class="topbar-title">{page_title}</div>
          </div>
          <div class="topbar-search">
            <span>⌕</span>
            <span>Search dashboard, reports, transcripts...</span>
          </div>
          <div class="topbar-profile">
            <span class="topbar-action">◇</span>
            <span class="topbar-action">□</span>
            <span class="profile-dot"></span>
            <span class="profile-copy">
              <strong>Hello, Research Admin</strong>
              <small>Unified ASD dashboard</small>
            </span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_label(text: str) -> None:
    st.markdown(
        f'<span class="section-label">{text}</span>',
        unsafe_allow_html=True,
    )


def _metric_icon(label: str, flavor: str) -> str:
    if flavor == "td":
        return "OK"
    if flavor == "dd":
        return "!"
    if flavor == "asd":
        return "AI"
    if flavor == "accent":
        return "+"
    words = [part for part in label.replace("/", " ").replace("-", " ").split() if part]
    if not words:
        return "#"
    return "".join(word[0] for word in words[:2]).upper()


def metric_card(col, label: str, value: str, delta: str = "", flavor: str = "") -> None:
    compact_labels = {"TD", "DD", "ASD", "PPV", "NPV", "Sensitivity", "Specificity"}
    compact = "compact" if label in compact_labels else ""
    cls = f"metric-card {flavor} {compact}".strip()
    delta_html = f'<div class="delta">{delta}</div>' if delta else ""
    icon = _metric_icon(label, flavor)
    col.markdown(
        f'<div class="{cls}"><div class="metric-icon">{icon}</div>'
        f'<div class="metric-body"><div class="label">{label}</div>'
        f'<div class="value">{value}</div>{delta_html}</div></div>',
        unsafe_allow_html=True,
    )


def info_box(text: str, kind: str = "info") -> None:
    cls = {"info": "info-box", "warn": "warn-box", "success": "success-box"}[kind]
    st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)


def style_fig(fig, height: int | None = None) -> go.Figure:
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title={"text": ""},
        colorway=PASTEL_SEQUENCE,
        font={"family": 'Inter, "Noto Sans Thai", -apple-system, sans-serif', "color": COLORS["text"]},
        title_font={"size": 16, "color": COLORS["text"]},
        margin={"l": 12, "r": 12, "t": 40, "b": 12},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"gridcolor": "#F0F4FA", "zerolinecolor": "#F0F4FA"},
        yaxis={"gridcolor": "#F0F4FA", "zerolinecolor": "#F0F4FA"},
        legend={
            "bgcolor": "rgba(255,255,255,0.88)",
            "bordercolor": COLORS["line"],
            "borderwidth": 1,
            "font": {"color": COLORS["muted"]},
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
              <span class="brand-icon"></span>
              <span>
                <strong>ASD Flow</strong><br>
                <small>Pastel admin dashboard</small>
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
              <span>Workspace</span>
              <strong>AI Transcript Reviewer</strong>
              <p>ตรวจ .cha, speaker labels, ASR confidence และ CHAT syntax ก่อนสกัด features</p>
            </div>
            <p style="margin-top:18px;color:var(--muted)">v0.17.0 · Research prototype</p>
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
            color_discrete_sequence=PASTEL_SEQUENCE,
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
    st.dataframe(display.style.background_gradient(cmap="Pastel1", axis=0), width="stretch")


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
            color_continuous_scale=PASTEL_CONTINUOUS_SCALE,
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
                    "bgcolor": COLORS["bg_soft"],
                    "borderwidth": 0,
                    "steps": [
                        {"range": [0, UNCERTAIN_LOW * 100], "color": "#EFFCF6"},
                        {
                            "range": [UNCERTAIN_LOW * 100, UNCERTAIN_HIGH * 100],
                            "color": "#FFF9DF",
                        },
                        {"range": [UNCERTAIN_HIGH * 100, 100], "color": "#FFF0F6"},
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
                        <div style="font-size:0.75rem;color:var(--muted);
                                    text-transform:uppercase;letter-spacing:.06em">{label}</div>
                        <div style="font-size:2.4rem;font-weight:800;color:{score_color};
                                    line-height:1">{value:.1f}</div>
                        <div style="font-size:0.75rem;color:var(--muted);margin-top:.4rem">{hint}</div>
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
                        <div style="color:var(--muted);font-size:0.85rem;
                                    text-transform:uppercase;letter-spacing:.08em">
                            Prediction
                        </div>
                        <div style="font-size:2.2rem;font-weight:800;color:{color};
                                    margin:.3rem 0">
                            {pred_label}
                        </div>
                        <div style="font-size:1.1rem;color:var(--ink)">
                            P(ASD) = <b>{prob_asd:.3f}</b>
                        </div>
                        <div style="color:var(--muted);font-size:0.8rem;margin-top:.8rem">
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
    calibration_summary = load_metric_csv("calibration_summary.csv")
    decision = load_metric_csv("decision_curve.csv")
    fairness = load_metric_csv("fairness_metrics.csv")
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
            if not calibration_summary.empty:
                row = calibration_summary.iloc[0]
                info_box(
                    f"**ECE:** {float(row['ece']):.3f} · "
                    f"**Brier:** {float(row['brier_score']):.3f} · "
                    "read as readiness audit, not Thai validation"
                )

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
                color_discrete_sequence=PASTEL_SEQUENCE,
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

    section_label("Fairness audit")
    st.markdown("### Group-level rates and gaps")
    if fairness.empty:
        info_box("Fairness metrics missing. Run `python scripts/compute_fairness_metrics.py`.", kind="warn")
    else:
        display_cols = [
            "attribute", "group", "n", "positives", "predicted_positive",
            "tpr", "fpr", "demographic_parity",
            "tpr_difference", "fpr_difference", "demographic_parity_difference",
        ]
        st.dataframe(
            fairness[[col for col in display_cols if col in fairness.columns]],
            width="stretch",
            hide_index=True,
        )
        st.caption(
            "Fairness rows come from English-speaking public corpora. "
            "They support model governance review but do not establish Thai clinical accuracy."
        )

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
            color_discrete_sequence=PASTEL_SEQUENCE,
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
            color_discrete_sequence=PASTEL_SEQUENCE,
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

def page_transcript_qa_reports(longitudinal: pd.DataFrame) -> None:
    hero(
        "Transcript QA & Reports",
        "ตรวจคุณภาพ CHAT transcript และสร้างรายงาน progress tracking สำหรับนักบำบัด",
        tags=["AI Transcript Reviewer", "Human-in-the-loop", "Markdown/PDF", "Thai validation not yet completed"],
    )
    info_box(
        "หน้านี้เป็น decision support และ progress tracking เท่านั้น ไม่ใช่เครื่องมือสรุปผลทางการแพทย์ "
        "ต้องใช้ร่วมกับนักบำบัดหรือแพทย์ผู้เชี่ยวชาญเสมอ",
        kind="warn",
    )

    tab_review, tab_report = st.tabs(["CHAT transcript QA", "Therapist progress report"])

    with tab_review:
        uploaded = st.file_uploader(".cha file", type=["cha"], key="pastel_transcript_qa")
        if uploaded is None:
            st.info("Upload `.cha` เพื่อดู quality score, issue table, marker counts และ ASR confidence summary ถ้ามี")
        else:
            from src.transcript_reviewer import review_cha_text

            text = uploaded.getvalue().decode("utf-8", errors="replace")
            result = review_cha_text(text)
            c1, c2, c3, c4 = st.columns(4)
            flavor = "td" if result["status"] == "pass" else "dd" if result["status"] == "needs_review" else "asd"
            metric_card(c1, "Quality score", str(result["quality_score"]), "0-100 rule-based score", flavor=flavor)
            metric_card(c2, "Status", result["status"], "pass / needs_review / fail", flavor=flavor)
            metric_card(c3, "Child tiers", str(result["summary"]["child_utterance_count"]), "CHI utterances", flavor="accent")
            avg_conf = result["summary"].get("average_confidence")
            metric_card(c4, "ASR conf", "n/a" if avg_conf is None else f"{avg_conf:.2f}", "average metadata value")

            st.markdown("### Marker counts")
            st.dataframe(
                pd.DataFrame([
                    {"marker": marker, "count": count}
                    for marker, count in result["summary"]["marker_counts"].items()
                ]),
                width="stretch",
                hide_index=True,
            )
            st.markdown("### Issues")
            if result["issues"]:
                st.dataframe(pd.DataFrame(result["issues"]), width="stretch", hide_index=True)
            else:
                st.success("ไม่พบ issue จาก rule-based reviewer แต่ยังควรให้คนตรวจยืนยันก่อนใช้ต่อ")

    with tab_report:
        from src.therapist_report import (
            render_progress_report_markdown,
            save_progress_report,
            summarize_child_progress,
        )

        child = st.selectbox("Child", sorted(longitudinal["child"].astype(str).unique()), key="pastel_report_child")
        export_format = st.radio(
            "Export format",
            ["md", "pdf"],
            horizontal=True,
            format_func=lambda value: "Markdown" if value == "md" else "PDF",
        )
        summary = summarize_child_progress(longitudinal, child)
        report_md = render_progress_report_markdown(summary)
        cols = st.columns(3)
        metric_card(cols[0], "Sessions", str(summary["n_sessions"]), "longitudinal rows")
        metric_card(
            cols[1],
            "Improving",
            f"{summary['improving_metric_count']}/{summary['tracked_metric_count']}",
            "descriptive metrics",
            flavor="td",
        )
        age = summary["age_range_months"]
        metric_card(cols[2], "Age range", f"{age['first']} - {age['last']}", "months")
        st.markdown(report_md)
        if export_format == "pdf":
            try:
                pdf_path = save_progress_report(child, format="pdf")
                st.download_button("Download PDF", pdf_path.read_bytes(), file_name=pdf_path.name, mime="application/pdf")
            except Exception as exc:  # noqa: BLE001
                st.error(f"PDF export failed: {exc}")
        else:
            st.download_button(
                "Download Markdown",
                report_md.encode("utf-8"),
                file_name=f"{child.lower().replace(' ', '_')}_progress_report.md",
                mime="text/markdown",
            )


def page_speech_therapist_assistant(df: pd.DataFrame, longitudinal: pd.DataFrame) -> None:
    hero(
        "AI Speech Therapist Assistant",
        "สรุป transcript quality, speech-language patterns, risk estimate และ progress trend สำหรับนักบำบัด",
        tags=["Decision support only", "Speech-language patterns", "Human-in-the-loop"],
    )
    info_box(
        "Assistant นี้ไม่แทนนักบำบัดหรือแพทย์ และยังไม่ได้ validate กับข้อมูลเด็กไทย "
        "ควรใช้เป็น clinical decision support พร้อม expert review เท่านั้น",
        kind="warn",
    )

    from src.speech_therapist_assistant import (
        generate_case_brief,
        interpret_progress_summary,
        interpret_screening_result,
        interpret_transcript_review,
    )
    from src.therapist_report import summarize_child_progress
    from src.transcript_reviewer import review_cha_text

    tab_qa, tab_screening, tab_case = st.tabs(["Transcript QA", "Screening patterns", "Progress case brief"])

    with tab_qa:
        uploaded = st.file_uploader(".cha file", type=["cha"], key="pastel_assistant_qa")
        if uploaded is None:
            st.info("Upload `.cha` เพื่อให้ assistant สรุป QA level และ recommended actions")
        else:
            review = review_cha_text(uploaded.getvalue().decode("utf-8", errors="replace"))
            qa = interpret_transcript_review(review)
            cols = st.columns(3)
            metric_card(cols[0], "QA level", qa["qa_level"], "assistant interpretation")
            metric_card(cols[1], "Reviewer", review["status"], "rule-based status")
            metric_card(cols[2], "Score", str(review["quality_score"]), "0-100")
            st.write(qa["safe_summary_th"])
            st.markdown("#### Recommended actions")
            st.write("\n".join(f"- {item}" for item in qa["recommended_actions"]))

    with tab_screening:
        row_options = [
            f"{idx}: {row.get('participant_id', row.get('child', 'child'))} ({row.get('group', 'unknown')} / {row.get('corpus', 'unknown')})"
            for idx, row in df.iterrows()
        ]
        picked = st.selectbox("Feature row", row_options, key="pastel_assistant_row")
        picked_idx = int(picked.split(":", 1)[0])
        features = df.loc[picked_idx, FEATURES].to_dict()
        probability = None
        try:
            model = train_screening_model(df)
            probability = float(model.predict_proba(pd.DataFrame([features])[FEATURES].values)[0, 1])
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Risk estimate unavailable: {exc}")
        interpretation = interpret_screening_result(features, probability=probability)
        cols = st.columns(2)
        metric_card(cols[0], "Concern level", interpretation["concern_level"], "assistant output")
        metric_card(cols[1], "Risk estimate", "n/a" if probability is None else f"{probability:.3f}", "screening support")
        st.write(interpretation["safe_summary_th"])
        st.markdown("#### Key patterns")
        st.write("\n".join(f"- {item}" for item in interpretation["key_patterns"]) or "- ไม่พบ pattern หลักจาก rules")
        st.markdown("#### Recommended next steps")
        st.write("\n".join(f"- {item}" for item in interpretation["recommended_next_steps"]))

    with tab_case:
        child = st.selectbox("Child", sorted(longitudinal["child"].astype(str).unique()), key="pastel_assistant_child")
        summary = summarize_child_progress(longitudinal, child)
        progress = interpret_progress_summary(summary)
        brief = generate_case_brief(progress_summary=summary, language="th")
        cols = st.columns(2)
        metric_card(cols[0], "Progress", progress["progress_direction"], "assistant trend")
        metric_card(cols[1], "Sessions", str(summary["n_sessions"]), "longitudinal rows")
        st.write(progress["safe_summary_th"])
        st.markdown(brief)
        st.download_button(
            "Download case brief",
            brief.encode("utf-8"),
            file_name=f"{child.lower().replace(' ', '_')}_assistant_case_brief.md",
            mime="text/markdown",
        )


def page_clinician_workflow(df: pd.DataFrame, longitudinal: pd.DataFrame) -> None:
    hero(
        "Clinician Workflow Simulator",
        "สามขั้นตอนแบบย่อ: Transcript QA → Screening & Patterns → Progress & Case Brief",
        tags=["No data stored", "Decision support only", "Human-in-the-loop"],
    )
    info_box(
        "Simulator นี้ใช้สาธิต workflow เท่านั้น ไม่เก็บข้อมูลถาวร และต้องให้ผู้เชี่ยวชาญตีความเสมอ",
        kind="warn",
    )

    from src.speech_therapist_assistant import (
        generate_case_brief,
        interpret_progress_summary,
        interpret_screening_result,
        interpret_transcript_review,
    )
    from src.therapist_report import summarize_child_progress
    from src.transcript_reviewer import review_cha_text

    col_qa, col_screen, col_progress = st.columns(3)
    workflow_review = None

    with col_qa:
        st.markdown("### Transcript QA")
        uploaded = st.file_uploader(".cha file", type=["cha"], key="pastel_workflow_cha", label_visibility="collapsed")
        if uploaded is None:
            st.info("Upload `.cha` to review transcript readiness.")
        else:
            workflow_review = review_cha_text(uploaded.getvalue().decode("utf-8", errors="replace"))
            qa = interpret_transcript_review(workflow_review)
            metric_card(st, "QA level", qa["qa_level"], workflow_review["status"])
            st.write(qa["safe_summary_th"])

    with col_screen:
        st.markdown("### Screening & Patterns")
        sample_idx = st.selectbox(
            "Sample row",
            list(df.index),
            format_func=lambda i: f"{df.loc[i, 'participant_id']} ({df.loc[i, 'corpus']})",
            key="pastel_workflow_row",
        )
        features = df.loc[sample_idx, FEATURES].to_dict()
        probability = None
        try:
            model = train_screening_model(df)
            probability = float(model.predict_proba(pd.DataFrame([features])[FEATURES].values)[0, 1])
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Risk estimate unavailable: {exc}")
        screening = interpret_screening_result(features, probability=probability)
        metric_card(st, "Concern level", screening["concern_level"], "screening support")
        if probability is not None:
            st.caption(f"Risk estimate: {probability:.3f}")
        st.write(screening["safe_summary_th"])

    with col_progress:
        st.markdown("### Progress & Case Brief")
        child = st.selectbox("Child", sorted(longitudinal["child"].astype(str).unique()), key="pastel_workflow_child")
        summary = summarize_child_progress(longitudinal, child)
        progress = interpret_progress_summary(summary)
        metric_card(st, "Progress", progress["progress_direction"], f"{summary['n_sessions']} sessions")
        st.write(progress["safe_summary_th"])
        brief = generate_case_brief(
            features=features,
            probability=probability,
            transcript_review=workflow_review,
            progress_summary=summary,
            language="th",
        )
        st.download_button(
            "Download case brief",
            brief.encode("utf-8"),
            file_name=f"{child.lower().replace(' ', '_')}_workflow_case_brief.md",
            mime="text/markdown",
        )


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
                <p style="font-size:.82rem;color:var(--muted)">{row.get("Authors", "")}</p>
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
            <p style="font-size:1.12rem;color:var(--ink)"><b>Say:</b> {step["talk"]}</p>
            <p style="font-size:1rem;color:var(--muted)"><b>Show:</b> {step["proof"]}</p>
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
    top_header(page)

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
    elif page == "transcript_qa":
        page_transcript_qa_reports(longitudinal)
    elif page == "assistant":
        page_speech_therapist_assistant(df, longitudinal)
    elif page == "clinician_workflow":
        page_clinician_workflow(df, longitudinal)
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
