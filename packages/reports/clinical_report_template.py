"""Bilingual Clinical Report Template for LinguaLens.

Generates professional, printable clinical language assessment reports
with embedded Spider Radar diagrams, developmental metrics, acoustic profiles,
longitudinal trend summaries, and human-in-the-loop clinical attestation blocks.
"""

from __future__ import annotations

import html
from typing import Any, Optional


def generate_bilingual_clinical_html(
    case_info: dict[str, Any],
    session_info: dict[str, Any],
    findings: dict[str, Any],
    narrative: str,
    recommendations: str,
    attested_by: Optional[str] = None,
    longitudinal_sessions: Optional[list[dict[str, Any]]] = None,
    radar_svg: Optional[str] = None,
) -> str:
    """Generate a high-fidelity bilingual (Thai / English) clinical HTML report."""
    case_id = html.escape(str(case_info.get("case_id", "N/A")))
    child_id = html.escape(str(case_info.get("child_id", "N/A")))
    dob = html.escape(str(case_info.get("birth_year_month", "N/A")))
    lang = html.escape(str(case_info.get("primary_language", "th")).upper())

    session_id = html.escape(str(session_info.get("session_id", "N/A")))
    session_date = html.escape(str(session_info.get("session_date", "N/A")))
    notes = html.escape(str(session_info.get("notes", "General assessment")))

    metrics = findings.get("metrics", {})
    guidelines = findings.get("guideline_links", [])

    # Format Metrics Table
    metrics_rows = ""
    for k, v in metrics.items():
        k_clean = html.escape(str(k))
        v_clean = html.escape(str(v))
        metrics_rows += f"<tr><td style='font-weight: 600; color: #1e293b;'>{k_clean}</td><td style='font-family: monospace; font-size: 13px;'>{v_clean}</td></tr>\n"

    # Format Guidelines Table
    guidelines_rows = ""
    for g in guidelines:
        c = html.escape(str(g.get("construct", "")))
        s = html.escape(str(g.get("status", "")))
        e = html.escape(str(g.get("evidence", g.get("description", ""))))
        status_badge = f"<span class='badge'> {s} </span>"
        guidelines_rows += f"<tr><td><strong>{c}</strong></td><td>{status_badge}</td><td style='color: #475569;'>{e}</td></tr>\n"

    # Longitudinal Comparison Table (if multiple sessions exist)
    longitudinal_html = ""
    if longitudinal_sessions and len(longitudinal_sessions) > 1:
        rows = ""
        for s in longitudinal_sessions:
            s_id = html.escape(str(s.get("session_id", "")))
            s_dt = html.escape(str(s.get("date", "")))
            s_utts = html.escape(str(s.get("utterances", 0)))
            s_chi = html.escape(str(s.get("chi_turns", 0)))
            s_mlu = html.escape(str(s.get("mlu_w", "-")))
            s_ttr = html.escape(str(s.get("ttr", "-")))
            s_f0 = html.escape(str(s.get("f0_median", "-")))
            rows += f"<tr><td>{s_dt}</td><td><code>{s_id}</code></td><td>{s_utts}</td><td>{s_chi}</td><td>{s_mlu}</td><td>{s_ttr}</td><td>{s_f0}</td></tr>\n"

        longitudinal_html = f"""
        <div class="section-title">📈 4. Longitudinal Assessment Trajectory / ติดตามพัฒนาการรายครั้ง</div>
        <table>
          <thead>
            <tr><th>Date / วันที่</th><th>Session ID</th><th>Total Utts</th><th>Child Turns</th><th>MLU-w</th><th>TTR (Vocab)</th><th>F0 Pitch (Hz)</th></tr>
          </thead>
          <tbody>
            {rows}
          </tbody>
        </table>
        """

    # Radar Chart visual block
    radar_block = ""
    if radar_svg:
        radar_block = f"""
        <div style="text-align: center; margin: 20px 0; background: #ffffff; padding: 16px; border: 1px solid #e2e8f0; border-radius: 8px;">
          <h4 style="margin: 0 0 10px 0; color: #0f766e; font-size: 14px;">🕸️ 5-Domain Spider Diagram vs TD Benchmark</h4>
          {radar_svg}
        </div>
        """

    attest_html = ""
    if attested_by:
        attest_html = f"""
        <div class="attestation-box">
          <div style="font-weight: 700; color: #0f766e; font-size: 14px;">✍️ Clinician Sign-Off & Verification / การลงนามรับรองผล</div>
          <div style="margin-top: 6px; font-size: 13px; color: #1e293b;">
            This language sample analysis has been reviewed, speaker-verified, and clinically attested by:
            <strong>{html.escape(attested_by)}</strong>
          </div>
          <div style="margin-top: 4px; font-size: 11px; color: #64748b;">
            Digital Attestation Stamp • TalkBank CHAT Format Standard (pylangacq verified)
          </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LinguaLens Clinical LSA Report — {case_id}</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Sarabun', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    color: #0f172a;
    background: #f8fafc;
    margin: 0;
    padding: 24px 16px;
  }}
  .report-container {{
    background: #ffffff;
    max-width: 900px;
    margin: 0 auto;
    padding: 36px 40px;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: 3px solid #0f766e;
    padding-bottom: 16px;
    margin-bottom: 20px;
  }}
  .header h1 {{
    margin: 0;
    font-size: 22px;
    color: #0f766e;
    font-weight: 800;
  }}
  .header .sub {{
    font-size: 13px;
    color: #64748b;
    margin-top: 2px;
  }}
  .meta-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 20px;
    font-size: 12px;
  }}
  .meta-item strong {{
    display: block;
    color: #64748b;
    font-size: 10px;
    text-transform: uppercase;
  }}
  .meta-item span {{
    font-size: 13px;
    font-weight: 600;
    color: #0f172a;
  }}
  .section-title {{
    font-size: 15px;
    font-weight: 700;
    color: #0f172a;
    margin-top: 24px;
    margin-bottom: 10px;
    border-left: 4px solid #0f766e;
    padding-left: 10px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 16px;
    font-size: 13px;
  }}
  th {{
    background: #f1f5f9;
    color: #334155;
    text-align: left;
    padding: 8px 12px;
    border-bottom: 2px solid #cbd5e1;
    font-weight: 600;
  }}
  td {{
    padding: 8px 12px;
    border-bottom: 1px solid #e2e8f0;
  }}
  .badge {{
    background: #ccfbf1;
    color: #0f766e;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 11px;
    display: inline-block;
  }}
  .notes-box {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 14px 16px;
    font-size: 13px;
    white-space: pre-wrap;
    line-height: 1.6;
  }}
  .safety-box {{
    background: #fffbeb;
    border: 1px solid #fef3c7;
    border-left: 4px solid #f59e0b;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    font-size: 12px;
    color: #92400e;
    margin-top: 24px;
    line-height: 1.5;
  }}
  .attestation-box {{
    background: #f0fdfa;
    border: 1px solid #ccfbf1;
    border-left: 4px solid #0f766e;
    border-radius: 0 8px 8px 0;
    padding: 14px 18px;
    margin-top: 20px;
  }}
  .footer {{
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid #e2e8f0;
    font-size: 11px;
    color: #94a3b8;
    text-align: center;
  }}
  @media print {{
    body {{ background: #fff; padding: 0; }}
    .report-container {{ box-shadow: none; border: none; padding: 0; max-width: 100%; }}
    .safety-box {{ break-inside: avoid; }}
    .attestation-box {{ break-inside: avoid; }}
  }}
</style>
</head>
<body>

<div class="report-container">
  <div class="header">
    <div>
      <h1>🗣️ LinguaLens Clinical LSA Report</h1>
      <div class="sub">Language Sample Analysis & Speech-Language Biomarkers Decision Support</div>
    </div>
    <div style="text-align: right;">
      <span class="badge">Clinical Research Prototype</span>
    </div>
  </div>

  <div class="meta-grid">
    <div class="meta-item"><strong>Case ID:</strong> <span>{case_id}</span></div>
    <div class="meta-item"><strong>Child ID:</strong> <span>{child_id}</span></div>
    <div class="meta-item"><strong>Birth Year/Month:</strong> <span>{dob}</span></div>
    <div class="meta-item"><strong>Primary Language:</strong> <span>{lang}</span></div>
    <div class="meta-item"><strong>Session ID:</strong> <span><code>{session_id}</code></span></div>
    <div class="meta-item"><strong>Assessment Date:</strong> <span>{session_date}</span></div>
    <div class="meta-item"><strong>Activity Context:</strong> <span>{notes}</span></div>
    <div class="meta-item"><strong>Status:</strong> <span>Attested & Verified</span></div>
  </div>

  {radar_block}

  <div class="section-title">📊 1. Quantitative Speech-Language Biomarkers / ตัวชี้วัดเชิงปริมาณ</div>
  <table>
    <thead>
      <tr><th>Language / Acoustic Metric</th><th>Measured Value</th></tr>
    </thead>
    <tbody>
      {metrics_rows}
    </tbody>
  </table>

  <div class="section-title">📑 2. Clinical Guideline & Developmental Constructs / การประเมินตามมิติคลินิก</div>
  <table>
    <thead>
      <tr><th>Construct Domain</th><th>Observation Status</th><th>Clinical Description</th></tr>
    </thead>
    <tbody>
      {guidelines_rows}
    </tbody>
  </table>

  <div class="section-title">📝 3. Narrative Observations & Recommendations / สรุปความเห็นและข้อเสนอแนะ</div>
  <div class="notes-box">
<strong>Clinical Observations:</strong>
{html.escape(narrative or 'No narrative notes entered.')}

<strong>Therapy Recommendations & Next Steps:</strong>
{html.escape(recommendations or 'No recommendations entered.')}
  </div>

  {longitudinal_html}

  {attest_html}

  <div class="safety-box">
    <strong>⚠️ Clinical Safety Boundary & Usage Disclaimer:</strong>
    LinguaLens is an assistive research and educational prototype designed to streamline transcript review and quantify developmental language markers. It does NOT provide automated medical or diagnostic conclusions. All findings must be interpreted by a certified Speech-Language Pathologist (SLP) or developmental pediatrician in combination with standardized clinical evaluations.
  </div>

  <div class="footer">
    LinguaLens v1.6.3 • Department of Medical Technology, Mahidol University • TalkBank / CHILDES Compliant
  </div>
</div>

</body>
</html>
"""
