---
name: asd-advisor-report-writer
description: Prepare advisor-facing Thai and bilingual progress reports for asd-project, including project summaries, discussion points, methodology explanations, references, changelog notes, presentation talking points, and clinically careful wording. Use when updating docs/PROJECT_SUMMARY_TH.md, docs/DISCUSSION_TH.md, docs/SUMMARY_TH.md, docs/REFERENCES.md, README.md, CHANGELOG.md, slide outlines, meeting notes, or term-paper narrative about ASD speech-language assessment.
---

# ASD Advisor Report Writer

## Purpose

Turn technical project changes into clear advisor-facing Thai explanations. Keep the narrative academically careful, clinically safe, and easy to discuss in a meeting.

## Files To Inspect

- `README.md` for current feature scope and headline claims.
- `CHANGELOG.md` for version history.
- `docs/PROJECT_SUMMARY_TH.md` for Thai progress summary.
- `docs/DISCUSSION_TH.md` for advisor discussion points.
- `docs/SUMMARY_TH.md` for original Thai summary.
- `docs/REFERENCES.md` and `docs/literature/` for citations.
- `docs/DEPLOYMENT.md`, `docs/AUDIO_PIPELINE.md`, and `docs/DEVELOPMENT.md` when deployment, audio, or workflow changed.
- `reports/figures/` and `reports/metrics/` when results or charts changed.

## Writing Workflow

1. Identify what changed and why it matters for the term paper.
2. Separate technical facts, results, limitations, and next steps.
3. Write Thai first when the target is advisor discussion; include English technical terms in parentheses when useful.
4. Use cautious clinical language: screening, risk estimate, decision support, further assessment.
5. Link claims to evidence: code output, metric file, figure, or reference.
6. Preserve the project's version/update workflow. Coordinate with `project-update-workflow` when code or docs changed.
7. End advisor notes with concrete questions or decisions needed.

## Preferred Structure

For progress summaries:

- เป้าหมายของงาน
- สิ่งที่ทำเพิ่ม
- ผลลัพธ์สำคัญ
- ข้อจำกัด
- สิ่งที่อยากขอคำแนะนำจากอาจารย์
- งานถัดไป

For discussion documents:

- ประเด็นที่ต้องตัดสินใจ
- ทางเลือก
- ข้อดี/ข้อเสีย
- ความเสี่ยง
- ข้อเสนอแนะ

For method explanations:

- Input data
- Processing pipeline
- Features extracted
- Model/evaluation
- Explainability and uncertainty
- Clinical limitation

## Style Rules

- Keep Thai prose natural, concise, and professional.
- Avoid claiming diagnostic certainty.
- Prefer "แบบจำลองช่วยคัดกรอง" over "ระบบวินิจฉัย".
- Explain ML metrics in plain language when writing for non-technical readers.
- Use bullets for meeting prep and paragraphs for report narrative.
- Keep citations in the style already used in `docs/REFERENCES.md`.

## Output Format

When editing docs, report:

- Files updated.
- Main narrative changes.
- Claims made safer or clarified.
- References added or still needed.
- Questions prepared for advisor.

Read [references/thai-clinical-language.md](references/thai-clinical-language.md) for preferred Thai wording.
