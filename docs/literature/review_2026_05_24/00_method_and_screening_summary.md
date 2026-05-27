# Corrected Literature Review Workflow Output

วันที่จัดทำ: 2026-05-24

## Corpus ที่ตรวจ

- Master list จาก ZIP: 88 papers
- PDF ที่มีใน ZIP: 79 papers
- No-PDF records: 9 papers
- ไฟล์ที่ใช้ตรวจ: `ASD_research_pdf_export.zip`, `manifest_pdfs.csv`, `no_pdf_papers.csv`, และ `docs/literature/screening/paper_screening_table.csv`

## เกณฑ์คัดเลือก

ยึด workflow จาก `tips.md` และ `literature_review_ai_workflow.md` โดยคัด 3 ชั้น:

1. Title/metadata screening: ต้องเกี่ยวกับ ASD/autism และเชื่อมกับ speech, audio, language, transcript, clinical screening, Thai context, หรือ AI decision support
2. Abstract/full-text-oriented screening: ต้องมี population, data modality, method/model, evaluation outcome หรือ clinical relevance ที่พอใช้ใน matrix ได้
3. Final synthesis screening: ให้ priority กับ paper ที่ตอบโจทย์ `asd-project` โดยตรง และลดน้ำหนัก paper ที่เป็น broad review, video-only, EEG-only, adult-only, preprint, opinion/editorial, หรือไม่มี PDF

## ผลการคัด

- Included final papers: 21
- Screening decision counts: {'include': 21, 'maybe': 4, 'exclude': 58, 'maybe_pdf_needed': 5}
- Final role counts: {'background_local': 4, 'reserve_candidate': 4, 'exclude': 58, 'core': 12, 'background_review': 4, 'future': 1, 'reserve_pdf_needed': 5}
- Quality among final papers: {'Strong': 7, 'Moderate': 12, 'Weak': 2}

ข้อสำคัญ: คะแนน quality ในรอบใหม่ตั้งใจไม่ inflate. Strong ถูกให้เฉพาะงานที่มี design/scale/validation น่าเชื่อถือหรือเป็น synthesis ที่ตรงประเด็นมาก ส่วนงาน small sample, preprint, conference, broad review, หรือไม่มี external validation จะลดเป็น Moderate/Weak ตามความเสี่ยง
