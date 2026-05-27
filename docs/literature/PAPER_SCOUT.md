# On-Demand ASD Literature Paper Scout

ใช้ไฟล์นี้เมื่ออยากค้นหา paper ใหม่ที่เกี่ยวข้องกับโปรเจกต์
AI-assisted speech/language assessment for autism spectrum disorder โดยไม่ตั้ง
recurring automation

## Run

ค้นแบบกว้าง:

```bash
python scripts/paper_scout.py
```

โฟกัส tag เดียว:

```bash
python scripts/paper_scout.py --tag video
python scripts/paper_scout.py --tag speech --tag audio
python scripts/paper_scout.py --tag clinical-validation
```

ถ้าต้องการบังคับ backend:

```bash
python scripts/paper_scout.py --backend openalex --tag video
python scripts/paper_scout.py --backend semantic-scholar --tag speech
```

บันทึกรายงาน Markdown:

```bash
python scripts/paper_scout.py --save
```

รายงานที่บันทึกจะอยู่ใน `docs/literature/scout_reports/`

## Scope

ค่าเริ่มต้นค้น paper ปี 2020-2026 ผ่าน Semantic Scholar Academic Graph API
ก่อน และ fallback ไป OpenAlex เมื่อถูก rate limit หรือ API ใช้งานไม่ได้ จากนั้นกันซ้ำกับ seed list เดิม:

```text
docs/literature/consensus_papers_2026-04-26.csv
```

Tag ที่รองรับ:

```text
speech
audio
language
video
behavior
questionnaire
multimodal
clinical-validation
ethics
privacy
Thai/local-context
```

## Screening Rules

สคริปต์ให้ความสำคัญกับ paper ที่มีองค์ประกอบครบ:

1. เกี่ยวกับ ASD / autism spectrum disorder
2. ใช้ AI, machine learning, deep learning, NLP, algorithm หรือ model
3. เกี่ยวกับ screening, assessment, diagnosis support, detection, classification หรือ severity
4. มี modality ที่เกี่ยวกับ project เช่น speech, audio, language, video, behavior, questionnaire หรือ multimodal

ผลคัดเบื้องต้นมี 3 แบบ:

```text
include
maybe
exclude
```

`include` ยังไม่ได้แปลว่าใช้เป็น citation ได้ทันที ต้องอ่าน abstract/full text และตรวจ method, dataset/source, metric, limitation และ clinical validity ก่อน

## Safety Rules

- ห้ามใช้ผลจากสคริปต์เป็น diagnostic claim
- ห้ามอ้าง sample size, metric, DOI หรือ conclusion ที่ไม่ได้อยู่ใน metadata หรือ full text จริง
- ถ้าข้อมูลไม่ชัด ให้ใช้ `not reported`
- วาง AI เป็น decision-support tool สำหรับ speech therapist เท่านั้น
- สำหรับ paper tag `video` หรือ `behavior` ให้ใช้เป็นแนวทาง future multimodal workflow ไม่ใช่หลักฐานแทน speech/language validation ของโปรเจกต์
