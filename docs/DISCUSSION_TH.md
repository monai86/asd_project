# 💬 ส่วนที่ต้องคุยกับอาจารย์

> **โปรเจกต์:** AI-Assisted Program for Clinical Assessment of Autism
> **วันที่ update ล่าสุด:** 23 เมษายน 2026

📖 **เอกสารคู่กัน:** [PROJECT_SUMMARY_TH.md](./PROJECT_SUMMARY_TH.md) — สรุปสิ่งที่ทำไปแล้วทั้งหมด

---

## 1. Workflow การใช้งานจริง 3 แบบ (ตามกลุ่มผู้ใช้)

### 🏥 Scenario A — นักบำบัด (speech-language pathologist)

**ใช้ได้ทันทีวันนี้ ✅**

```
1. บันทึกเสียง/วิดีโอเด็กขณะเล่น ~15–30 นาที
2. ถอดเสียง + annotate เป็น CHAT format (~3–5 เท่าของความยาว audio)
3. วางไฟล์ .cha ใน data/ → python src/data_loader.py
4. เปิด dashboard → หน้า Screening หรือ Progress tracker
```

เหมาะกับ: research, complex cases ที่คุ้มเวลา annotate

---

### 👩‍⚕️ Scenario B — หมอ/กุมารแพทย์ในคลินิก

**"Quick decision support" — ใช้ได้เลย**

```
1. เด็กเข้าตรวจ → หมอสังเกตการพูด 5–10 นาที
2. เปิด dashboard หน้า Screening
3. กรอก 11 ตัวเลขที่ประเมินคร่าว ๆ
4. กด Predict → ถ้า risk > 50% → ส่งต่อ specialist
```

ข้อดี: ไม่ต้อง transcribe — **screening ใน 5 นาที**
ข้อเสีย: ค่าประเมินด้วยสายตาแม่นยำน้อยกว่า transcribe จริง

---

### 👨‍👩‍👧 Scenario C — พ่อแม่ (home screening)

**Audio pipeline มีแล้วในโปรเจกต์ปัจจุบัน ✅** (ภาษาอังกฤษ — ภาษาไทยต้อง retrain)

```
1. บันทึกเสียงเด็กเล่น 10–30 นาที (มือถือ / web upload)
2. faster-whisper แปลงเสียง → text
3. Pitch-based diarization แยกเด็ก/ผู้ใหญ่
4. CHAT formatter ใส่ xxx / 0. / &=
5. data_loader.py → สกัด 11 features
6. LogReg (AUC 0.93) → P(ASD) + คำแนะนำ
```

Demo: เปิด dashboard → หน้า **🎤 Audio assessment** → upload `.wav` → รอ 1–3 นาที

**Gap ที่ยังเหลือ:**
- ภาษาไทย: Whisper รองรับไทย แต่ model ต้อง retrain ด้วยข้อมูลไทย
- Baseline เด็กไทย: ค่า MLU/TTR ปกติของเด็กไทยแต่ละช่วงอายุยังไม่มี
- UX สำหรับพ่อแม่: ตอนนี้เป็น researcher dashboard ต้องทำ mobile app แยก

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

Single prediction           →   Continuous monitoring
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

---

## 4. ประเด็นจริยธรรม

| ประเด็น | ทางแก้ |
|---------|--------|
| **False negative** (พลาด ASD) | Framing เป็น "screening" ไม่ใช่ diagnosis → human-in-the-loop เสมอ |
| **False positive** (alarm พ่อแม่) | แสดง confidence + คำแนะนำพบแพทย์ยืนยัน |
| **Bias** (เพศ/เชื้อชาติ) | Audit AUC ในแต่ละ subgroup ก่อน deploy |
| **Privacy** | Audio/transcript = sensitive → encryption + consent + IRB |
| **Transparency** | แสดง model coefficients ให้หมอเห็นว่าตัดสินจากอะไร (**ทำแล้วใน dashboard**) |

---

## 5. Features ที่ควรเพิ่มในอนาคต

| Feature | ความสำคัญ | ความยาก |
|---------|-----------|---------|
| **Echolalia ratio** (ตรวจ repeated utterances) | core ASD symptom | ปานกลาง |
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
9. **Publication:** ผลที่ได้ (AUC 0.93) คุณภาพดีพอ submit conference/journal หรือยัง?
10. **Deep learning:** ควรลอง fine-tune wav2vec2 หรือ BERT สำหรับ CHAT text ต่อไหม?
11. **Deployment:** อาจารย์ต้องการ URL สำหรับ demo จริง หรือแค่ local run?
