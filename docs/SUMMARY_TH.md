# สรุปโปรเจกต์ (ภาษาไทย) — Index

> **ชื่อโปรเจกต์:** การประยุกต์ใช้ปัญญาประดิษฐ์เพื่อสนับสนุนการประเมินทางคลินิกสำหรับเด็กออทิสติก
> *(AI-Assisted Program for Clinical Assessment of Autism)*
>
> **ผู้จัดทำ:** นักศึกษาคณะเทคนิคการแพทย์ ปี 3 มหาวิทยาลัยมหิดล
> **ประเภท:** Term Paper
> **วันที่ update ล่าสุด:** 17 พฤษภาคม 2026

---

## 📂 เอกสารหลัก

| ไฟล์ | เนื้อหา |
|------|---------|
| [PROJECT_SUMMARY_TH.md](./PROJECT_SUMMARY_TH.md) | สรุปสิ่งที่ทำทั้งหมด — dataset, features, ผลลัพธ์, โครงสร้างระบบ, วิธีรัน |
| [DISCUSSION_TH.md](./DISCUSSION_TH.md) | ส่วนคุยกับอาจารย์ — scenarios, roadmap, จริยธรรม, Model Trust และคำถาม |

---

> **Public demo:** Hugging Face app ใช้ Pastel dashboard เป็นหน้าหลักสำหรับผู้ปกครอง/คลินิกและคู่มือพรีเซนต์สั้นอยู่ใน `docs/PRESENTER_GUIDE_TH.md`

> เนื้อหาด้านล่างเป็น summary เดิมที่ปรับตัวเลขหลักให้ตรงกับ v0.17.0 แล้ว; สำหรับรายละเอียดล่าสุดที่สุดให้เปิด `PROJECT_SUMMARY_TH.md`, `DISCUSSION_TH.md` และ `app/dashboard_unified.py`

---

## 1. ที่มาและเป้าหมาย

จากการปรึกษาอาจารย์ อาจารย์เสนอแนว 3 ทาง:

1. **Video assessment** — ให้ AI วิเคราะห์วิดีโอเด็กขณะคุยกับนักบำบัด แล้วให้คะแนนตาม scale
2. **Progress tracking** — ประเมินว่าเด็กที่เข้ารับการบำบัดทุกสัปดาห์มีพัฒนาการดีขึ้นหรือไม่
3. **Screening tool** — ช่วยพ่อแม่ประเมินเบื้องต้นว่าลูกเสี่ยง ASD หรือไม่

**ข้อจำกัดที่พบ:** ไม่มี video dataset สาธารณะที่ใช้ได้ จึงใช้ **ข้อความถอดเสียง (CHAT transcripts)** จาก
[TalkBank / ASDBank](https://asd.talkbank.org/) แทน ซึ่งครอบคลุม **แนวทาง 2 + 3** ได้ดี

---

## 2. ชุดข้อมูลที่ใช้

### 2.1 Cross-sectional (ใช้ฝึก classifier)

| Corpus | Design | จำนวน | กลุ่ม |
|--------|--------|-------|-------|
| **Eigsti** | Cross-sectional | 48 คน | ASD 16, DD 16, TD 16 |
| **Nadig** | Cross-sectional | 38 คน | ASD 13, TD 25 (ตรวจจาก `@ID` header) |
| **NYU-Emerson** | Cross-sectional + video/audio | 30 คน | ASD 30 (ทั้งหมด) |
| **Flusberg** | Longitudinal → ใช้ session 1 | 6 คน | ASD 6 |
| **รวม** | | **122 คน** | **ASD 65 · TD 41 · DD 16** |

### 2.2 Longitudinal (ใช้ติดตามพัฒนาการ)

| Corpus | เด็ก | Sessions |
|--------|------|----------|
| **Rollins** | 5 | 21 sessions |
| **Flusberg** | 6 | 64 sessions |
| **Quigley** (partial) | 2 | 2 sessions |
| **รวม** | **12 เด็ก** | **87 sessions** |

**ข้อค้นพบสำคัญจาก data:**
- Nadig **ไม่ใช่ ASD ทั้งหมด** ตามที่ `0types.txt` บอก — มี TD 25 คน, ASD 13 คน เป็น case-control design ต้องอ่าน label จาก `@ID` header โดยตรง
- **QuigleyMcNally** เป็น **mother speech** (`*MOT:`) ไม่มี child utterances — เลยงดอกออกจาก classification dataset (จะ extract ได้แค่ 2 ไฟล์ใน longitudinal)
- ใช้ **session 1** ของ Flusberg ใน classifier เพื่อหลีกเลี่ยง **repeated measures bias**

---

## 3. Features ที่สกัดออกมาจากไฟล์ `.cha`

ใช้ library `pylangacq` อ่านไฟล์ CHAT (รูปแบบ transcripts มาตรฐานของ CHILDES/TalkBank) แล้วคำนวณ feature รวม **11 ตัว** ต่อไฟล์ (ต่อเด็ก 1 คน)

### 3.1 ตารางสรุป

| กลุ่ม | Feature | ตัวอย่างค่า | แนวที่คาดหวัง |
|------|---------|-------------|---------------|
| **Demographics** | `age_months` | 48.0 | (control ตัวแปร) |
| | `sex` | male / female | (control ตัวแปร) |
| **Productivity** | `total_utterances` | 180 | TD > ASD |
| | `total_words` | 400 | TD > ASD |
| **Complexity** | `mlu` (morphemes) | 2.5 | TD > ASD |
| | `mluw` (words) | 2.3 | TD > ASD |
| **Lexical diversity** | `ttr` | 0.40 | TD > ASD (โดยทั่วไป) |
| **ASD markers** | `unintelligible_count` | 10 | ASD > TD |
| | `unintelligible_ratio` | 0.06 | ASD > TD |
| | `zero_vocalization_count` | 5 | ASD > TD |
| | `nonverbal_vocalization_count` | 8 | ASD > TD |
| **Pragmatic** | `question_ratio` | 0.08 | TD > ASD |

### 3.2 อธิบายทีละ feature แบบละเอียด

> **หมายเหตุ:** ทุก feature คำนวณจาก **เฉพาะคำพูดของเด็ก (`*CHI:`)** ไม่นับคำพูดของผู้ตรวจ (`*INV:`) หรือผู้ปกครอง (`*MOT:`)

---

#### 🧍 Demographics (ใช้เป็น control variable)

**`age_months` — อายุเป็นเดือน**
- **ความหมาย:** อายุเด็กที่บันทึก transcript นั้น แปลงจาก CHAT format `5;03.10` (5 ปี, 3 เดือน, 10 วัน) เป็นเดือน (63.33)
- **ทำไมสำคัญ:** ภาษาเด็กพัฒนาเร็วมากระหว่าง 2–5 ปี ต้อง **control** อายุก่อน เพราะเด็ก ASD อายุ 5 ขวบจะพูดเก่งกว่าเด็ก TD อายุ 3 ขวบ แม้กลุ่ม TD จะ "ปกติกว่า"
- **ใน classifier:** เป็น feature ที่ช่วยแยก ASD/TD เพราะกลุ่มตัวอย่างเรา ASD และ TD มีอายุเฉลี่ยต่างกัน (ASD 58 เดือน vs TD 36 เดือน)

**`sex` — เพศ**
- **ความหมาย:** ชาย/หญิง
- **ทำไมสำคัญ:** ASD พบในเด็กชายมากกว่าหญิง **4:1** (epidemiology) การ report นี้ช่วยให้เห็น bias ของ dataset
- **ไม่ใช้ใน model ปัจจุบัน** (เพราะอาจเกิด bias) แต่เก็บไว้ใน CSV เพื่อใช้วิเคราะห์เพิ่ม

---

#### 🗣️ Productivity — ปริมาณการพูด (เด็กพูดเยอะแค่ไหน?)

**`total_utterances` — จำนวนประโยค (utterances) ทั้งหมด**
- **ความหมาย:** นับแต่ละบรรทัด `*CHI:` เป็น 1 utterance
- **ตัวอย่าง:**
  - `*CHI: hi .` = 1 utterance
  - `*CHI: I want it .` = 1 utterance
- **ทำไมสำคัญ (clinical):**
  - เด็ก ASD มักพูด **น้อยกว่า** (social communication deficit เป็น core symptom ตาม DSM-5)
  - ถ้าเด็กพูด 50 utterances ใน session 30 นาที อาจเป็นสัญญาณ **expressive language delay**

**`total_words` — จำนวนคำทั้งหมดที่เด็กพูด**
- **ความหมาย:** นับเฉพาะ content words (ตัด punctuation ออก: `.`, `?`, `!`, `+...`)
- **ทำไมสำคัญ:**
  - เป็น proxy ของ **vocabulary production**
  - ในผลเรา: ASD 296 คำ vs DD 517 คำ → **ASD พูดน้อยกว่า DD แม้อายุใกล้กัน** ซึ่งตรงกับ literature
  - นักบำบัดใช้ตัวเลขนี้ประเมินเป้าหมายในแต่ละ session

---

#### 📏 Complexity — ความซับซ้อนของประโยค

**`mlu` — Mean Length of Utterance (morphemes)** ⭐ สำคัญที่สุด
- **ความหมาย:** จำนวน morphemes (หน่วยคำเล็กสุด) เฉลี่ยต่อประโยค
  - คำเช่น `cats` = 2 morphemes (cat + s)
  - `walking` = 2 morphemes (walk + ing)
- **ทำไมสำคัญ (Brown 1973):**
  - MLU เป็น **gold standard** ของการประเมินการพัฒนาภาษามา **50+ ปี**
  - ใช้แบ่งระยะพัฒนาเป็น **Brown's stages I–V**:
    | Stage | MLU | อายุปกติ |
    |-------|-----|----------|
    | I | 1.0–2.0 | 12–26 เดือน |
    | II | 2.0–2.5 | 27–30 เดือน |
    | III | 2.5–3.0 | 31–34 เดือน |
    | IV | 3.0–3.75 | 35–40 เดือน |
    | V | 3.75–4.5 | 41–46 เดือน |
  - เด็ก ASD อายุ 5 ขวบที่มี MLU = 1.5 → **ช้ากว่าปกติ 2 ปี**
- **ในผลเรา:** ASD 2.27 ± 1.20 vs DD 3.57 ± 1.00 (ASD ต่ำกว่าอย่างชัดเจน แม้อายุเท่ากัน)
- **ใน classifier:** เป็น feature อันดับต้น ๆ ที่สำคัญ (ดู feature importance plot)

**`mluw` — Mean Length of Utterance (words)**
- **ความหมาย:** เหมือน `mlu` แต่นับเป็นคำแทน morpheme
- **ทำไมสำคัญ:** ง่ายกว่า MLU เพราะไม่ต้อง parse morphology อาจารย์/นักบำบัดคำนวณเองได้
- **เปรียบเทียบ:** `mlu` ≥ `mluw` เสมอ (เพราะ 1 คำอาจมีหลาย morpheme)

---

#### 🎨 Lexical Diversity — ความหลากหลายของคำ

**`ttr` — Type-Token Ratio** ⭐
- **สูตร:** `unique_words / total_words`
- **ตัวอย่าง:** ประโยค `"the cat sat on the mat"` มี 6 tokens แต่ 5 unique words → TTR = 5/6 = 0.83
- **ความหมาย:**
  - TTR สูง → เด็กใช้คำหลากหลาย (vocabulary กว้าง)
  - TTR ต่ำ → เด็กใช้คำซ้ำ ๆ (อาจบ่งบอก **echolalia** หรือ **repetitive speech** ใน ASD)
- **ทำไมสำคัญ (clinical):**
  - Repetitive speech เป็น 1 ใน core symptom ASD (restricted & repetitive behaviors ตาม DSM-5 criterion B)
  - TTR ต่ำมาก (<0.2) บ่ง **echolalia** ซึ่งพบในเด็ก ASD 75%
- **ใน Rollins:** Carl พัฒนา TTR จาก 0.02 → 0.34 ใน 4 sessions ซึ่งแปลว่าเด็กเริ่มใช้คำหลากหลายขึ้นหลังบำบัด

---

#### 🚨 ASD Markers — สัญญาณที่มักพบในเด็ก ASD

**`unintelligible_count` / `unintelligible_ratio` — จำนวน/สัดส่วนคำที่ฟังไม่รู้เรื่อง**
- **ความหมาย:** นับประโยคที่มี `xxx` หรือ `yyy`
  - `xxx` = ฟังแล้วไม่เข้าใจว่าเด็กพูดคำว่าอะไร (unintelligible)
  - `yyy` = ฟังไม่ออก แต่ทราบหน่วยเสียง (phonologically coded but not recognizable)
- **ตัวอย่าง:**
  ```
  *CHI: xxx .        # เด็กพูดแต่ไม่รู้ว่าพูดอะไร
  *CHI: xxx ball .   # พูดคำไม่ชัด 1 คำ แล้วตามด้วย "ball"
  ```
- **ทำไมสำคัญ (clinical):**
  - **Articulation/phonological disorder** พบร่วมกับ ASD ได้บ่อย
  - Ratio สูง → เด็กพูดไม่ชัด อาจต้องการ **speech therapy** เพิ่ม
  - ถ้า ratio ลดลงระหว่าง sessions → บำบัดได้ผล ✅
- **ในผลเรา:** ASD 0.111 vs TD 0.103 (ใกล้กันอย่างน่าสนใจ)

**`zero_vocalization_count` — จำนวนครั้งที่เด็กไม่เปล่งเสียง**
- **ความหมาย:** นับประโยคที่เป็น `0 .` (ศูนย์) ซึ่งใน CHAT หมายความว่า **เด็กตอบโดยไม่ใช้เสียง** (อาจชี้, พยักหน้า, ทำท่าทาง)
- **ตัวอย่าง:**
  ```
  *INV: where's the ball?
  *CHI: 0 .
  %act: points to ball   # เด็กชี้ไป แต่ไม่พูด
  ```
- **ทำไมสำคัญ (clinical):**
  - สัญญาณ **non-verbal ASD** (~30% ของเด็ก ASD อายุ 5+ ยังพูดน้อยหรือไม่พูด)
  - ใช้แทน spoken language ด้วย **gestures** เป็นตัวบ่งชี้การพัฒนา expressive language
  - ลดลง = เด็กเริ่มใช้คำพูดแทน gesture ✅
- **ในผลเรา (Rollins):** Josh session 1 มี 122 zero vocalizations → session 4 เหลือ 43 (ลดลงชัดเจน)

**`nonverbal_vocalization_count` — จำนวนเสียงที่ไม่ใช่คำ**
- **ความหมาย:** นับ markers แบบ `&=gasp`, `&=laugh`, `&=cry`, `&=cough` (เสียงที่ได้ยิน แต่ไม่ใช่คำพูดที่มีความหมาย)
- **ตัวอย่าง:**
  ```
  *CHI: &=laugh .
  *CHI: &=gasp wow .
  ```
- **ทำไมสำคัญ (clinical):**
  - เด็กเล็กใช้เสียงที่ไม่ใช่คำเยอะกว่าเด็กโต (stepping stone ของ verbal development)
  - เด็ก ASD มักมี **unusual vocalization patterns** เช่น repetitive humming, squealing
  - **แต่ระวัง:** สูงไม่ได้แปลว่าแย่เสมอ — เด็กที่หัวเราะ (`&=laugh`) เยอะคือมี social engagement ที่ดี

---

#### 💬 Pragmatic — การใช้ภาษาเชิงสังคม

**`question_ratio` — สัดส่วนประโยคที่เป็นคำถาม**
- **สูตร:** `จำนวน utterances ที่ลงท้ายด้วย '?' / total utterances`
- **ทำไมสำคัญ (clinical):**
  - การถามคำถามสะท้อน **social initiation** และ **joint attention** (ความสามารถในการดึงความสนใจคนอื่น)
  - เด็ก ASD มักถามคำถาม **น้อยกว่า** เด็ก TD (core deficit ใน ASD)
  - Wh-questions (what, where, why) พัฒนาช้าในเด็ก ASD
- **ข้อจำกัด:** feature นี้นับรวมทั้ง genuine questions และ echoed questions เด็กพูดซ้ำ) ต่อไปควรแยก

---

### 3.3 Features สำหรับ Progress Tracking (Rollins)

นอกจาก features ข้างต้น Rollins มี **metadata เพิ่ม** สำหรับ longitudinal analysis:

| Feature | ความหมาย |
|---------|----------|
| `child` | ชื่อเด็ก (Carl / Josh / Mars / Roger / Sid) — ใช้ group ต่อคน |
| `session_id` | รหัสเซสชันจาก filename (YYMMDD format) เช่น `020800` = ปี 02 เดือน 08 |
| `session_order` | ลำดับเซสชัน 1, 2, 3, ... เรียงตามเวลา |
| `composite_score` | **คะแนนรวม** ของ features ทั้งหมดหลังจาก z-score และปรับทิศทาง (ดูสูตรด้านล่าง) |

#### Composite Score คำนวณยังไง?

```
composite = mean over 7 features of:
    direction × (feature - mean) / std
```

โดย `direction = +1` สำหรับ features ที่ **สูง = ดี** (`mlu`, `mluw`, `ttr`, `total_words`, `total_utterances`)
และ `direction = -1` สำหรับ features ที่ **ต่ำ = ดี** (`unintelligible_ratio`, `zero_vocalization_count`)

**ผลลัพธ์:** คะแนนรวมเดียว ๆ ที่:
- **+** = เด็กพูดดีขึ้น (มากกว่าค่าเฉลี่ย)
- **−** = เด็กยังต่ำกว่าค่าเฉลี่ย
- **เพิ่มขึ้นเรื่อย ๆ** = กำลังพัฒนา ✅

---

### 3.4 Features ที่ควรเพิ่มในอนาคต (ถ้ามีเวลา)

| Feature ที่อยาก | ความสำคัญ | ความยาก |
|----------------|-----------|---------|
| **Echolalia ratio** (ตรวจ repeated utterances) | core ASD symptom | ปานกลาง |
| **Pronoun reversal** (`I`/`you` สลับ) | typical ASD marker | ง่าย |
| **Prosody features** (ถ้ามี audio) | monotone speech | ต้องมี audio |
| **Turn-taking latency** | social communication | ต้อง `%tim` annotation |
| **Joint attention markers** | core ASD | ต้องดู `%act` tier |
| **Response-to-question rate** | social responsiveness | ปานกลาง |

---

## 4. ผลลัพธ์หลัก

### 4.1 Classification (Screening — แนวทางที่ 3)

ทดสอบด้วย **Stratified 5-fold Cross-Validation** บน **122 คน** (เพิ่มขึ้นจาก 86 → 142%)

#### งาน A: Binary (ASD vs non-ASD) ← งานจริงของ screening tool

| Model | Accuracy | F1-macro | ROC-AUC |
|-------|----------|----------|---------|
| **Logistic Regression** | **87.7%** | **0.877** | **0.931** ⬆️ |
| SVM (RBF) | 85.3% | 0.852 | 0.924 |
| Random Forest | 82.8% | 0.828 | 0.906 |

**ข้อสรุป:**
- **Logistic Regression** ให้ผลดีที่สุด (**AUC 0.931**) พร้อม Model Trust metrics
- Accuracy = **87.7%**, F1-macro = **0.877**
- Sensitivity = **0.846**, specificity = **0.912**, PPV = **0.917**, NPV = **0.839**
- Brier score = **0.098** และมี threshold/calibration/decision curve สำหรับ audit

#### งาน B: Multi-class (ASD / DD / TD) — งานยากกว่า

| Model | Accuracy | F1-macro |
|-------|----------|----------|
| **Random Forest** | **82.8%** ⬆️ | **0.775** |
| Logistic Regression | 78.7% | 0.743 |
| SVM | 74.6% | 0.706 |

Random baseline ของ 3 classes = 33% → model เราดีกว่าอย่างชัดเจน

### 4.2 Progress Tracking (แนวทางที่ 2)

ข้อมูล **Longitudinal รวม**: **12 เด็ก × 87 sessions** (Rollins 5 + Flusberg 6 + Quigley 2) — เพิ่มจากเดิม 5 เด็ก

**9/12 เด็กแสดง IMPROVING pattern** (composite score เพิ่มขึ้น):

| เด็ก | Corpus | Features ที่ดีขึ้น | Composite score (start → end) |
|------|--------|-------------------|-------------------------------|
| **Roger** | Rollins | **7/7** | -1.50 → +0.72 (Δ **+2.22**) 🏆 |
| **Sid** | Rollins | **7/7** | -1.51 → -0.90 (Δ +0.61) |
| **Carl** | Rollins | 6/7 | -1.51 → -0.23 (Δ **+1.28**) |
| Rick | Flusberg | 5/7 | -0.11 → +0.49 (Δ +0.60) |
| Josh | Rollins | 5/7 | -1.50 → -1.06 (Δ +0.45) |
| Mars | Rollins | 5/7 | -1.46 → -1.21 (Δ +0.25) |
| Stuart | Flusberg | 5/7 | -0.31 → -0.16 (Δ +0.16) |
| Mark | Flusberg | 4/7 | +0.01 → +0.23 (Δ +0.22) |
| Jack | Flusberg | 4/7 | +0.06 → +0.16 (Δ +0.10) |
| Brett | Flusberg | 3/7 | +0.69 → +0.70 (Δ +0.01) |

**Trends ที่มีนัยสำคัญทางสถิติ (p < 0.05):**
- **Mars**: `total_words` เพิ่ม 46 คำ/session (r = 0.98, p = 0.004) ⭐
- **Carl**: `ttr` (ความหลากหลายคำ) พุ่งขึ้นต่อเนื่อง (r = 0.97, p = 0.03)
- **Rick** (Flusberg): `mluw` เพิ่มต่อเนื่อง 11 sessions (r = 0.89, p = 0.0002) ⭐
- **Rick** (Flusberg): `mlu` เพิ่ม 11 sessions (r = 0.89, p = 0.0002) ⭐

**ข้อสรุป:** AI สามารถ **quantify พัฒนาการของเด็ก** ได้จริง โดยไม่ต้องให้นักบำบัดมานั่งประเมินเอง — ตรงกับสิ่งที่อาจารย์ถามในคราวที่แล้ว

---

## 5. สถาปัตยกรรมระบบ

```
.cha files (CHAT transcripts)
        ↓  pylangacq
    Feature extraction (13 features/ไฟล์)
        ↓
  ┌─────────────────┬──────────────────┐
  ↓                 ↓                  ↓
 EDA         Classification      Progress Tracking
(plots)    (LogReg / MLP / ...)  (linear regression +
                                  composite score)
        ↓
 Pastel Dashboard + Parent Public Demo + Model Trust
```

---

## 6. ไฟล์ในโปรเจกต์

```
asd-project/
├── data/                                 ข้อมูลดิบ + CSVs ที่สกัดแล้ว
│   ├── Eigsti/ Nadig/ NYU-Emerson/       ไฟล์ .cha ต้นฉบับ
│   ├── Flusberg/ Rollins/ QuigleyMcNally/
│   ├── combined_features.csv             122 แถว สำหรับ classification
│   └── longitudinal_features.csv         87 แถว สำหรับ progress tracking
│
├── src/
│   ├── data_loader.py                .cha → CSV
│   ├── eda.py                        สำรวจข้อมูล + 5 plots
│   ├── classifier.py                 3 models × 2 tasks (sklearn)
│   ├── deep_learning.py              PyTorch MLP + Bi-LSTM
│   └── progress_tracking.py          วิเคราะห์ Rollins
│
├── app/
│   └── dashboard.py                  Streamlit interactive dashboard
│
├── reports/
│   ├── figures/                      15+ plots (.png)
│   └── metrics/                      ผลลัพธ์เป็น CSVs
│
├── requirements.txt
├── README.md
└── SUMMARY_TH.md                     ไฟล์นี้
```

---

## 7. วิธีรัน

```bash
# 1. ติดตั้ง dependencies
pip install -r requirements.txt

# 2. สกัด features จากไฟล์ .cha (รันครั้งเดียว)
python src/data_loader.py

# 3. สำรวจข้อมูล (สร้าง plots)
python src/eda.py

# 4. Train classifiers แบบดั้งเดิม
python src/classifier.py

# 5. Train deep learning models
python src/deep_learning.py

# 6. วิเคราะห์ progress ของ Rollins
python src/progress_tracking.py

# 7. เปิด dashboard แบบ interactive
streamlit run app/dashboard.py
```

---

## 8. การใช้งานจริง (Real-world Deployment)

### 8.1 Model ทำอะไรได้บ้างในตอนนี้?

| Model | Input | Output | Use case |
|-------|-------|--------|----------|
| **LogReg Screening** | 13 features ของเด็ก 1 คน | ASD probability + uncertainty + model card | คัดกรองเบื้องต้น |
| **Multi-class LogReg** | 13 features | ASD / DD / TD + probabilities | Differential support |
| **Progress tracker** | Features ของเด็กคนเดียว × หลาย sessions | Trajectory + composite score + trends | ประเมินผลบำบัด |
| **Deep MLP** | 13 features | ASD probability (ROC-AUC 0.932) | Alternative classifier |
| **Utterance Bi-LSTM** | CHI utterance sequence | ASD probability (ROC-AUC 0.719) | Sequence baseline |

> **หัวใจสำคัญ:** ตอนนี้ input คือ **13 features ที่สกัดจาก CHAT transcripts** — ถ้าใช้ audio-derived transcript ต้องมี transcript QA ก่อนใช้ผล prediction จริง

---

### 8.2 Workflow 3 แบบตามกลุ่มผู้ใช้

#### 🏥 Scenario A — **นักบำบัด** (speech-language pathologist)

**ใช้ได้ทันทีวันนี้ ✅**

```
1. บันทึกวิดีโอ/เสียงเด็กขณะเล่น ~15–30 นาที
2. ถอดเสียง + annotate เป็น CHAT format (~3–5 เท่าของความยาว audio)
3. วางไฟล์ .cha ใน data/ แล้วรัน python src/data_loader.py
4. เปิด dashboard → หน้า Screening หรือ Progress tracker
```

**เหมาะกับ:** research, complex cases ที่คุ้มเวลา annotate
**ไม่เหมาะกับ:** routine clinical use (annotation นานเกินไป)

---

#### 👩‍⚕️ Scenario B — **หมอ/กุมารแพทย์** ในคลินิก

**ใช้ได้เลยในรูปแบบ "quick decision support"**

```
1. เด็กเข้าตรวจ — หมอสังเกตการพูด 5–10 นาที
2. เปิด dashboard หน้า Screening
3. กรอก 13 ตัวเลขที่ประเมินคร่าว ๆ:
   • age_months (ทราบจาก record)
   • total_utterances, MLU, TTR  (ประเมินคร่าวจาก 5 นาที)
   • zero_vocalization_count (นับครั้งเด็กไม่ตอบ)
4. กด Predict → ถ้า risk > 50% → ส่งต่อ specialist
```

**ข้อดี:** ไม่ต้อง transcribe — **screening ใน 5 นาที**
**ข้อเสีย:** ค่าประเมินด้วยสายตาแม่นยำน้อยกว่า transcribe จริง

---

#### 👨‍👩‍👧 Scenario C — **พ่อแม่** (public demo)

**Parent Public Demo มีแล้วในโปรเจกต์ปัจจุบัน ✅** (no-data-retention, ไม่ใช่ diagnosis)

```
1. ผู้ปกครองกรอกอายุ ภาษาในบ้าน และสิ่งที่กังวล
2. ตอบ Parent Concern Checklist ที่โปรเจกต์เขียนเอง
3. Optional audio upload มี privacy/consent gate
4. ระบบสรุป concern level + next steps ที่ควรคุยกับผู้เชี่ยวชาญ
5. ดาวน์โหลด parent summary ได้ โดยไม่เก็บข้อมูลถาวร
```

**Demo จริง:** เปิด dashboard → หน้า "🎤 Audio assessment" → upload `.wav` → รอ 1–3 นาที → ได้ `.cha` + features + prediction พร้อม download

**Gap ที่ยังเหลือ:**
- **ภาษาไทย:** Whisper รองรับไทย แต่ model เรา train ด้วยอังกฤษ → ต้อง retrain
- **Baseline เด็กไทย:** ค่า MLU/TTR ปกติของเด็กไทยแต่ละช่วงอายุยังไม่มี
- **UX สำหรับพ่อแม่:** มี public demo แล้ว แต่ถ้าจะใช้จริงต้องมี consent/auth/retention policy และ external validation

---

### 8.3 สิ่งที่ต้องเพิ่มก่อนใช้งานจริง

```
Current prototype           →   Production system
══════════════════          →   ═════════════════
Manual .cha files           ✅  Auto audio → CHAT pipeline (เสร็จแล้ว)
+ Whisper upload page       →   รองรับภาษาไทย + Thai-speech fine-tune

122 English-speaking kids   →   External validation กับข้อมูลไทย
                                (ร่วมกับ รพ. + IRB approval)

Researcher dashboard        ✅  Docker + Streamlit Cloud / HF Spaces
+ audio assessment          →   Mobile app สำหรับพ่อแม่
                                + EHR integration

Single prediction           →   Continuous monitoring
                                (alert เมื่อเด็ก regress)

                            +   MEDICAL DEVICE APPROVAL
                                (อย. / FDA / IRB)
```

---

### 8.4 ตัวอย่าง API แบบง่าย (ถ้าจะ deploy)

**Step 1 — Save model** (หลัง train เสร็จ):

```python
import joblib
# หลัง pipe.fit(X, y) ใน classifier.py
joblib.dump(pipe, 'models/screening_logreg.pkl')
```

**Step 2 — FastAPI endpoint:**

```python
# serve.py
from fastapi import FastAPI
import joblib, numpy as np

app = FastAPI()
model = joblib.load('models/screening_logreg.pkl')

FEATURE_ORDER = [
    "age_months", "total_utterances", "mlu", "mluw", "ttr",
    "total_words", "unintelligible_count", "unintelligible_ratio",
    "zero_vocalization_count", "nonverbal_vocalization_count",
    "question_ratio",
]

@app.post("/screen")
def screen(features: dict):
    x = np.array([[features[k] for k in FEATURE_ORDER]])
    prob = float(model.predict_proba(x)[0, 1])
    return {
        "asd_probability": prob,
        "risk_level": "high" if prob >= 0.5 else "low",
        "recommendation": ("refer_to_specialist"
                           if prob >= 0.5 else "continue_monitoring"),
    }
```

**Step 3 — Run:**
```bash
uvicorn serve:app --port 8000
```

จากนั้น mobile app / EHR สามารถ POST JSON เข้ามาได้ → ได้ผลกลับเป็น JSON

---

### 8.5 Integration กับ รพ.

**Lightweight (เริ่มได้เลย):**
- Standalone web tool → หมอเปิด dashboard ใน browser
- ผลออกมา 1 บรรทัดใน medical note: *"AI screening: ASD probability 72%"*

**Full system (ระยะกลาง):**
- Microservice รับ audio → คืน screening result + rationale
- Log ทุก prediction → re-training แบบ active learning
- Hook เข้า HIS/EMR ผ่าน FHIR standard

---

### 8.6 ประเด็นจริยธรรม (ต้องคิดก่อน deploy)

| ประเด็น | ทางแก้ |
|---------|--------|
| **False negative** (พลาด ASD) | Framing เป็น "screening" ไม่ใช่ diagnosis → human-in-the-loop เสมอ |
| **False positive** (alarm พ่อแม่) | แสดง confidence + คำแนะนำพบแพทย์ยืนยัน |
| **Bias** (เพศ/เชื้อชาติ/เศรษฐฐานะ) | Audit AUC ในแต่ละ subgroup ก่อน deploy |
| **Privacy** | Audio/transcript = sensitive → encryption + consent + IRB |
| **Transparency** | แสดง model coefficients ให้หมอเห็นว่าตัดสินจากอะไร (**ทำแล้วใน dashboard**) |

---

### 8.7 Roadmap สมจริง 6–12 เดือน

| Milestone | สิ่งที่ต้องทำ | ทรัพยากร | สถานะ |
|-----------|--------------|----------|--------|
| **M1 (เดือน 1–2)** | Whisper → CHAT auto-annotator | 1 developer | ✅ เสร็จแล้ว (EN) |
| **M2 (เดือน 3–4)** | เก็บข้อมูลไทย 50+ เด็ก | รพ. + IRB | ⏳ รอ advisor |
| **M3 (เดือน 5–6)** | Retrain + external validation | ML engineer | ⏳ รอ M2 |
| **M4 (เดือน 7–8)** | Mobile app MVP | Mobile dev + UX | ⏳ |
| **M5 (เดือน 9–12)** | Pilot study + publication + medical approval | Clinical team + PI | ⏳ รอ M2-M4 |

✅ **Deploy-ready แล้ว:** `Dockerfile`, Streamlit Cloud config, HuggingFace Spaces guide อยู่ใน `DEPLOYMENT.md`

---

## 9. จุดเด่นที่ควรนำเสนออาจารย์

1. **ตอบโจทย์อาจารย์ครบ 2/3 แนวทาง** (Progress tracking + Screening)
2. **ผลลัพธ์ดีมาก:** **AUC 0.931** ที่ Binary screening พร้อม sensitivity/specificity/PPV/NPV, calibration และ decision curve
3. **ขยาย dataset เป็น 122 คน** (จาก 86) โดยรวม 5 corpora: Eigsti, Nadig, NYU-Emerson, Flusberg, QuigleyMcNally
4. **Clinical interpretability:** ใช้ features ที่นักบำบัดเข้าใจ (MLU, TTR) ไม่ใช่ black-box
5. **Progress tracking ทำงานจริง:** **9/12 เด็ก** แสดง IMPROVING pattern (จาก 4/5)
6. **มี interactive dashboard** — รวม Parent Public Demo, Audio assessment และ Progress tracker
7. **End-to-end audio pipeline ✅** — Whisper ASR + pitch-based diarization + CHAT formatter สำเร็จและทำงานได้
8. **Deploy-ready**: `Dockerfile` + `DEPLOYMENT.md` — เปิดแจก URL ให้อาจารย์ได้ทันที
9. **Pastel Dashboard + Model Trust** — ใช้อธิบายข้อมูล โมเดล ความน่าเชื่อถือ limitations และ research evidence ได้ครบ

## 10. ข้อจำกัด (ที่ต้องกล่าวในรายงาน)

1. **Dataset ยังเล็ก** (122 คน, 87 longitudinal sessions) — ดีขึ้นจากเดิม แต่ยังไม่เพียง generalize เต็มที่
2. **ไม่มี video** — ได้แต่ text + audio (audio pipeline สร้างจาก Whisper เอง)
3. **Transcripts เป็นภาษาอังกฤษ** — Whisper รองรับไทยแล้ว แต่ model classifier ต้อง retrain ด้วยข้อมูลไทย
4. **LSTM under-performs** — ข้อมูลน้อยเกินไปสำหรับ sequence model เมื่อเทียบกับ LogReg/TabularMLP
5. **ASR + diarization ยังไม่ benchmark** — `src/evaluate_asr.py` พร้อมแล้ว แต่ยังไม่มี TalkBank audio มาทดสอบ WER
6. **ยังไม่มี external validation** — ใช้ CV เท่านั้น

## 11. แนวทางต่อยอด

| Idea | Effort | Clinical value |
|------|--------|----------------|
| ✅ ~~ใช้ **Whisper** transcribe audio~~ | — | เสร็จแล้ว (EN) |
| Fine-tune Whisper/Thai + retrain classifier | ปานกลาง | สูงมาก — ใช้กับเด็กไทยได้ |
| WER benchmark กับ TalkBank audio | ต่ำ | พิสูจน์คุณภาพ ASR |
| Pyannote diarization (SOTA) | ต่ำ (HF token) | แยกผู้พูดดีขึ้น |
| เก็บ video dataset จาก รพ.ไทย | สูงมาก | สูงมาก |
| ลอง **pretrained language model** (BERT, wav2vec2) | ปานกลาง | ปานกลาง |
| เชื่อมต่อกับแบบประเมินไทย (REELS, DAIM) | สูง | สูงมาก |

---

## 12. คำถามที่คุยกับอาจารย์พรุ่งนี้

1. **Scope:** โปรเจกต์ควรเน้น Screening หรือ Progress tracking?
2. **Data:** อาจารย์มี connection กับ รพ. ที่มี video/audio data เด็ก ASD ไทยหรือไม่?
3. **Target scale:** ถ้าจะต่อยอด ควรใช้ assessment scale ไทยอะไร (REELS, TDMI, ADOS)?
4. **Deliverable:** Term paper ต้องเป็น report อย่างเดียว หรือต้องมี demo ใช้งานได้?
5. **Timeline:** ถ้าขยาย scope ต่อ จะมีเวลากี่สัปดาห์?

---

**วันที่ update ล่าสุด:** 17 พฤษภาคม 2026 — เพิ่ม Parent Public Demo, shared 13-feature schema, versioned model bundle, Model Trust metrics, Project Atlas dashboard และ LogReg AUC 0.931
