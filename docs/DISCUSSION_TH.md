# 💬 ส่วนที่ต้องคุยกับอาจารย์

> **โปรเจกต์:** AI-Assisted Program for Clinical Assessment of Autism
> **วันที่ update ล่าสุด:** 5 มิถุนายน 2026

📖 **เอกสารคู่กัน:** [PROJECT_SUMMARY_TH.md](./PROJECT_SUMMARY_TH.md) — สรุปสิ่งที่ทำทั้งหมด

📌 **Interactive project dashboard รวมเนื้อหา:** `app/dashboard_unified.py` (Pastel)
📌 **Roadmap ถัดไป:** [NEXT_STEPS_TH.md](./NEXT_STEPS_TH.md)
📌 **สถานะล่าสุด:** ใช้ Pastel unified dashboard เป็น public surface หลัก พร้อม Parent Public Demo, versioned model bundle, Model Trust/Fairness metrics, AI Transcript Reviewer, Therapist Progress Report, AI Speech Therapist Assistant, Clinician Workflow Simulator, Thai Validation Readiness Pack และใน v1.5.0 ได้รวมระบบ Supabase Postgres Repository และ Storage Upload Pipeline สำหรับใช้งานฐานข้อมูลและการจัดเก็บไฟล์จริงอย่างปลอดภัย

---

## 1. Workflow การใช้งานจริง 3 แบบ (ตามกลุ่มผู้ใช้)

### 🏥 Scenario A — นักบำบัด (speech-language pathologist)

**ใช้เป็น research/demo workflow ได้ทันที แต่ยังไม่ใช่ clinical deployment**

```
1. บันทึกเสียง/วิดีโอเด็กขณะเล่น ~15–30 นาที
2. ถอดเสียง + annotate เป็น CHAT format (~3–5 เท่าของความยาว audio)
3. วางไฟล์ .cha ใน data/ → python src/data_loader.py
4. เปิด dashboard → หน้า Screening หรือ Progress tracker
```

เหมาะกับ: research, teaching demo และการเตรียม workflow สำหรับ future validation โดยต้องมี human review

---

### 👩‍⚕️ Scenario B — หมอ/กุมารแพทย์ในคลินิก

**"Quick decision support" — ใช้เป็น prototype demo เท่านั้น**

```
1. เด็กเข้าตรวจ → หมอสังเกตการพูด 5–10 นาที
2. เปิด dashboard หน้า Screening
3. กรอก feature ที่ประเมินคร่าว ๆ เพื่อดูตัวอย่าง risk estimate
4. อ่านผลเป็น screening support / decision support และส่งต่อ specialist เมื่อมีความกังวลทางคลินิก
```

ข้อดี: สาธิตแนวคิด decision support ได้เร็วโดยไม่ต้อง transcribe
ข้อเสีย: ค่าประเมินด้วยสายตาแม่นยำน้อยกว่า transcribe จริง
ข้อจำกัด: ยังไม่ได้ validate กับข้อมูลเด็กไทยและไม่ใช่เครื่องมือวินิจฉัย

---

### 👨‍👩‍👧 Scenario C — พ่อแม่ (public web demo)

**Parent Public Demo มีแล้วในโปรเจกต์ปัจจุบัน ✅** (no-data-retention, ไม่ใช่ diagnosis)

```
1. ผู้ปกครองกรอกอายุ ภาษาในบ้าน และสิ่งที่กังวล
2. ตอบ Parent Concern Checklist ที่โปรเจกต์เขียนเอง
3. Optional audio upload มี privacy/consent gate
4. ระบบสรุป concern level + next steps ที่ควรคุยกับผู้เชี่ยวชาญ
5. ดาวน์โหลด parent summary ได้ โดยไม่เก็บข้อมูลถาวร
```

Demo: เปิด dashboard → หน้า **🎤 Audio assessment** → upload `.wav` → รอ 1–3 นาที

**Gap ที่ยังเหลือ:**
- ภาษาไทย: Whisper รองรับไทย แต่ model ยังต้อง validate/retrain ด้วยข้อมูลไทย
- Baseline เด็กไทย: ค่า MLU/TTR ปกติของเด็กไทยแต่ละช่วงอายุยังไม่มี
- Public deployment: ถ้าจะเปิดให้เก็บข้อมูลจริง ต้องมี consent, auth, retention policy และ IRB/data governance

---

## 2. สิ่งที่ต้องเพิ่มก่อนใช้งานจริง

```
Current prototype           →   Production system
══════════════════              ═════════════════
Manual .cha files           ✅  Auto audio → CHAT pipeline (เสร็จแล้ว)
Whisper upload page         →   รองรับภาษาไทย + Thai-speech fine-tune

122 English-speaking kids   →   External validation กับข้อมูลไทย
                                (ร่วมกับ รพ. + IRB approval)

Researcher dashboard        ✅  Docker + Streamlit Cloud
+ audio assessment          →   Mobile app สำหรับพ่อแม่ + EHR integration

Single screening estimate   →   Continuous monitoring
                                (alert เมื่อเด็ก regress)

                            +   MEDICAL DEVICE APPROVAL (อย. / FDA / IRB)
```

---

## 3. Roadmap สมจริง 6–12 เดือน

| Milestone | สิ่งที่ต้องทำ | ทรัพยากร | สถานะ |
|-----------|--------------|----------|--------|
| **M1 (เดือน 1–2)** | Whisper → CHAT auto-annotator | 1 developer | ✅ เสร็จแล้ว (EN) |
| **M2 (เดือน 3–4)** | เก็บข้อมูลไทย 50+ เด็ก | รพ. + IRB | ⏳ รอ advisor |
| **M3 (เดือน 5–6)** | Retrain + external validation | ML engineer | ⏳ รอ M2 |
| **M4 (เดือน 7–8)** | Mobile app MVP | Mobile dev + UX | ⏳ |
| **M5 (เดือน 9–12)** | Pilot study + publication + medical approval | Clinical team + PI | ⏳ รอ M2–M4 |

### Demo surface ปัจจุบัน

ตอนนี้ใช้หน้า Pastel unified dashboard เป็นหน้าหลักหน้าเดียวเพื่อรวมภาพรวมของโปรเจกต์ทั้งหมดและโชว์ความน่าเชื่อถือของโมเดล หน้าใหม่นี้มีตัวกรองและกราฟ interactive สำหรับ:

- project story และเหตุผลที่ใช้ CHAT transcript
- dataset explorer, group/corpus composition และ realtime-style project signal
- feature reference ครบ 13 ตัว พร้อม EDA scatter/distribution/correlation/raw data
- screening tool, uncertainty, XAI, severity score และ parent concern checklist
- Model Trust: leaderboard, sensitivity/specificity/PPV/NPV, threshold playground, confusion matrix, calibration/Brier, fairness audit, decision curve, uncertainty zone, subgroup robustness, leave-one-corpus-out และ model card
- Project overview: data inventory, corpus explorer, research evidence, glossary และ presentation mode
- audio/CHAT → feature → model → report workflow พร้อม segment QA preview
- model results, report figures, progress trajectories และ first-vs-last tracking
- clinical safety และข้อจำกัด
- limitations และ next steps
- Clinical Readiness: current prototype status, Thai validation prerequisites, transcript QA workflow, therapist report workflow, AI Speech Therapist Assistant, fairness/calibration readiness และ safe-use boundary

### v0.18.0: Clinical Readiness & Thai Validation Readiness Pack

สิ่งที่เพิ่มใหม่:

- `src/transcript_reviewer.py` ตรวจ `.cha` แบบ rule-based และรายงาน quality score / issue table / marker counts
- `src/therapist_report.py` สร้าง Thai-safe Markdown progress report จาก `longitudinal_features.csv`
- Streamlit หน้า **Transcript QA & Reports** สำหรับ upload transcript และสร้าง report
- Pastel dashboard หน้า **Clinical Readiness** สำหรับเล่าว่า workflow พร้อมรับ validation data ในอนาคต แต่ยังไม่พิสูจน์ Thai clinical accuracy
- `docs/THAI_VALIDATION_READINESS_TH.md` อธิบาย current status, สิ่งที่พร้อมแล้ว, สิ่งที่ยังต้องทำ, pilot design และ safe claim wording

### AI Speech Therapist Assistant

Assistant ใหม่ทำหน้าที่เป็น clinical decision-support สำหรับนักบำบัดด้านภาษาและการสื่อสาร โดยสรุป:

- transcript quality จาก AI Transcript Reviewer
- speech-language patterns จาก 14-feature schema
- screening risk estimate จากโมเดลปัจจุบันเมื่อมี probability
- progress trend จาก longitudinal sessions
- therapist-facing case brief สำหรับใช้คุยต่อกับผู้เชี่ยวชาญ

ขอบเขตที่ต้องพูดชัด:

- ไม่แทนนักบำบัดหรือแพทย์
- ไม่พิสูจน์ Thai clinical accuracy หากยังไม่มีข้อมูล validation เด็กไทย
- ต้องมี human-in-the-loop ก่อนใช้ประกอบการตัดสินใจจริง
- ใช้คำว่า screening support, speech-language pattern, risk estimate, progress tracking และ recommend further expert assessment

ข้อความที่ต้องพูดให้ชัดกับอาจารย์:

> ตอนนี้ยังไม่มี Thai validation data ดังนั้นระบบนี้ยังไม่ validated สำหรับเด็กไทย และไม่ใช่เครื่องมือวินิจฉัย ASD แต่ demo แสดงว่า technical workflow, governance, reporting และ safety layer พร้อมสำหรับการทำ validation ในอนาคต

### v0.19.0: Clinical Readiness Enhancements

สิ่งที่เพิ่มในรอบนี้เน้นความพร้อมของ workflow และ governance โดยไม่เพิ่มหรืออ้างอิง Thai child data:

- AI Transcript Reviewer ตรวจ Thai text mismatch กับ `@Languages` และสรุป average ASR/diarization confidence หาก transcript มี metadata
- `src/fairness_metrics.py` และ `scripts/compute_fairness_metrics.py` สร้าง ECE, Brier score, TPR/FPR difference และ demographic parity difference จากข้อมูลเดิม
- Streamlit เพิ่ม **Model Trust & Fairness** และ **🩺 Clinician Workflow Simulator**
- Therapist Progress Report export เป็น Markdown หรือ PDF เพื่อสาธิตเอกสาร progress tracking สำหรับนักบำบัด
- Pastel dashboard แสดง calibration summary และ fairness audit table ใน Model Trust section

ข้อความที่ควรใช้เมื่ออธิบาย v0.19.0:

> v0.19.0 ทำให้ระบบพร้อมสำหรับการตรวจสอบคุณภาพ transcript, fairness/calibration audit และ workflow review มากขึ้น แต่ metric เหล่านี้ยังมาจาก English-speaking public corpora จึงเป็น readiness evidence ไม่ใช่หลักฐานความแม่นยำในเด็กไทย

---

## 4. ประเด็นจริยธรรม

| ประเด็น | ทางแก้ |
|---------|--------|
| **False negative** (พลาด ASD) | Framing เป็น "screening" ไม่ใช่ diagnosis → human-in-the-loop เสมอ |
| **False positive** (alarm พ่อแม่) | แสดง confidence + คำแนะนำพบแพทย์ยืนยัน |
| **Bias** (เพศ/เชื้อชาติ) | Audit subgroup metrics, fairness difference และ calibration ก่อน deploy |
| **Privacy** | Audio/transcript = sensitive → encryption + consent + IRB |
| **Transparency** | แสดง model coefficients ให้หมอเห็นว่าตัดสินจากอะไร (**ทำแล้วใน dashboard**) |
| **Thai validation gap** | ระบุชัดว่า no Thai validation data yet และต้อง external validation/calibration ก่อนใช้งานจริง |

---

## 5. Features ที่ควรเพิ่มในอนาคต

### ✅ ที่ทำไปแล้ว (v0.10.0 - v0.14.0)
- **Echolalia detection** (count/ratio) — ✅ implemented
- **Per-estimate explainability** (SHAP-equivalent) — ✅ implemented
- **Uncertainty band** (40-60%) — ✅ implemented
- **Graded severity scoring** (0-10) — ✅ implemented
- **Multi-modal input** (project-authored parent concern checklist + late-fusion) — ✅ implemented

### ที่ยังทำไม่ได้
| Feature | ความสำคัญ | ความยาก |
|---------|-----------|---------|
| **AI Transcript Reviewer** | ลดความผิดพลาดก่อนสกัด feature | ✅ implemented v0.18.0 |
| **Therapist Progress Report** | ทำให้ progress tracking ใช้คุยกับนักบำบัดได้ในฐานะ decision support | ✅ implemented v0.18.0, PDF export v0.19.0 |
| **Fairness/calibration audit** | แสดง ECE, Brier, TPR/FPR difference และ demographic parity readiness | ✅ implemented v0.19.0 |
| **Clinician Workflow Simulator** | รวม transcript QA, screening pattern และ progress brief ใน workflow เดียว | ✅ implemented v0.19.0 |
| **Pronoun reversal** (`I`/`you` สลับ) | typical ASD marker | ง่าย |
| **Prosody features** (ถ้ามี audio) | monotone speech | ต้องมี audio |
| **Turn-taking latency** | social communication | ต้อง `%tim` annotation |
| **Response-to-question rate** | social responsiveness | ปานกลาง |

---

## 6. คำถามที่ต้องคุยกับอาจารย์

1. **Scope:** โปรเจกต์ควรเน้น Screening หรือ Progress tracking?
2. **Data:** อาจารย์มี connection กับ รพ. ที่มี video/audio data เด็ก ASD ไทยหรือไม่?
3. **Target scale:** ถ้าจะต่อยอด ควรใช้ assessment scale ไทยอะไร (REELS, TDMI, ADOS)?
4. **Deliverable:** Term paper ต้องเป็น report อย่างเดียว หรือต้องมี demo ใช้งานได้?
5. **Timeline:** ถ้าขยาย scope ต่อ จะมีเวลากี่สัปดาห์?
6. **Audio pipeline:** อาจารย์สนใจ demo ที่ upload `.wav` เข้า dashboard จริง ๆ ไหม?
7. **Thai baseline:** มีข้อมูล normative MLU/TTR สำหรับเด็กไทยไหม หรือต้องวัดเอง?
8. **Collaboration:** ถ้าจะ collect data จาก รพ. ต้องผ่าน IRB ของมหิดลหรือของ รพ.?
9. **Publication:** ผลที่ได้ (AUC 0.935 + Model Trust metrics + CI/subgroup reliability) คุณภาพดีพอ submit conference/journal หรือยัง?
10. **Deep learning:** ควรลอง fine-tune wav2vec2 หรือ BERT สำหรับ CHAT text ต่อไหม?
11. **Deployment:** อาจารย์ต้องการ URL สำหรับ demo จริง หรือแค่ local run?
12. **Transcript QA:** ถ้าใช้ ASR สร้าง `.cha` ควรให้ AI reviewer ช่วยตรวจจุดเสี่ยงก่อน human review หรือไม่?
13. **Therapist report:** รายงาน tracking ควร export เป็น Markdown/PDF/DOCX หรือดูผ่าน dashboard ก็พอ?
14. **Thai validation:** feasibility pilot 30-50 cases ควรออกแบบกลุ่ม ASD / TD / developmental delay อย่างไร?
15. **Clinical claims:** wording แบบไหนที่อาจารย์เห็นว่าปลอดภัยที่สุดสำหรับ term paper โดยไม่ทำให้ดูเหมือน diagnostic device?
16. **Assistant workflow:** อาจารย์อยากให้ AI Speech Therapist Assistant เน้น transcript QA, feature interpretation หรือ progress case brief เป็นหลัก?
