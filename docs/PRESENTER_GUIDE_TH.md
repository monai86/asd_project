# คู่มือพรีเซนต์โปรเจกต์แบบสั้น

เอกสารนี้ออกแบบมาให้ใช้พูดอธิบายโปรเจกต์ภายใน 3-5 นาที โดยเน้น
ให้คนฟังเข้าใจว่าโปรเจกต์ทำอะไร มีข้อมูลอะไร และเชื่อถือผลลัพธ์ได้
อย่างไร โดยไม่ต้องอ่านโค้ด

## 1. ประโยคเปิด

> โปรเจกต์นี้เป็น web app สำหรับช่วยคัดกรองและติดตามพัฒนาการเด็ก
> จากข้อมูลเสียงและ transcript ภาษา spoken language โดยเน้นการใช้งานจริง
> สำหรับผู้ปกครอง นักบำบัด และอาจารย์

ประเด็นที่ต้องย้ำ:

- ไม่ใช่เครื่องมือวินิจฉัย
- มีโหมดสำหรับผู้ปกครองที่ปลอดภัยและไม่เก็บข้อมูลถาวรโดยค่าเริ่มต้น
- ใช้ Pastel dashboard หน้าเดียวสำหรับทั้ง demo, clinician workflow, model trust และข้อจำกัดของโปรเจกต์

## 2. อธิบายโครงสร้างโปรเจกต์

ให้เล่าตามลำดับนี้:

1. **Public app** — หน้าใช้งานสำหรับผู้ปกครองและผู้ใช้งานทั่วไป
2. **Clinician workflow** — ส่วนสำหรับ `.cha`, audio QA, prediction, และ progress tracking
3. **Model trust / readiness** — ส่วนอธิบาย data, model, metrics, safety และ research evidence ใน Pastel dashboard

ถ้าต้องเล่าแบบสั้นมาก ใช้ประโยคนี้:

> โปรเจกต์ใช้ Pastel dashboard เป็นหน้าหลักหน้าเดียว: ใช้งานจริง, ตรวจสอบเชิงคลินิก, และอธิบายภาพรวมของระบบ

## 3. สิ่งที่ควรโชว์บนหน้าจอ

- หน้า public app เพื่อแสดง parent-friendly flow
- หน้า Model Trust เพื่อให้เห็นว่าโมเดลไม่ได้มีแค่ accuracy แต่มี calibration,
  threshold, uncertainty, และ subgroup robustness
- หน้า Pastel dashboard เพื่อแสดง data inventory, corpus map, feature dictionary,
  และ pipeline ตั้งแต่เสียงไปจนถึงรายงาน

## 4. สคริปต์พรีเซนต์ 5 นาที

### นาทีที่ 0-1: ปัญหา

- ASD screening และ progress tracking ต้องใช้เวลาและข้อมูลจากหลายแหล่ง
- ทีมทำโปรเจกต์นี้เพื่อทำ web app ที่เข้าถึงง่ายและอธิบายได้โปร่งใส

### นาทีที่ 1-2: วิธีทำงาน

- รับเสียงหรือ transcript
- ถอดเสียง / ตรวจ CHAT / สกัด features
- ประเมินความเสี่ยงและสร้าง report

### นาทีที่ 2-3: ความน่าเชื่อถือ

- ใช้ 13 features ที่นิยามชัดเจน
- มี calibration, Brier score, decision curve, uncertainty zone
- มี model card และ dataset-style documentation

### นาทีที่ 3-4: สิ่งที่ทำให้โปรเจกต์ต่างจาก demo ทั่วไป

- มี public parent app
- มี clinician/research dashboard
- มี Pastel dashboard ที่อธิบายทั้งระบบให้คนอื่นเข้าใจ

### นาทีที่ 4-5: ข้อจำกัดและ next step

- ผลลัพธ์ยังเป็น decision support ไม่ใช่ diagnosis
- ยังต้องมี human review โดยผู้เชี่ยวชาญ
- ขั้นต่อไปคือ validation เพิ่ม และเตรียมใช้งานกับข้อมูลภาษาไทยมากขึ้น

## 5. ตัวเลขสำคัญที่ควรจำ

- Binary LogReg ROC-AUC: **0.9312**
- Sensitivity: **0.8462**
- Specificity: **0.9123**
- PPV: **0.9167**
- NPV: **0.8387**
- Brier score: **0.0983**

ถ้าต้องพูดสั้น ให้เน้นว่า:

> โมเดลแยกกลุ่มได้ดี และยังมี calibration กับ uncertainty เพื่อช่วยให้ผลลัพธ์ดูสมจริงและใช้งานได้ปลอดภัยกว่าแค่ดู accuracy อย่างเดียว

## 6. ข้อความที่ควรใช้

- ช่วยคัดกรอง
- ใช้ประกอบการตัดสินใจ
- ต้องมีผู้เชี่ยวชาญตรวจทาน
- ไม่เก็บข้อมูลถาวรโดยค่าเริ่มต้น
- ใช้เพื่ออธิบายแนวโน้มและความเสี่ยง ไม่ใช่สรุปว่าเป็น ASD แน่นอน

## 7. ลิงก์สำหรับเปิดสาธิต

- Pastel public app: <https://paoo4511-asd-screening-tool.hf.space>

## 8. ถ้าคนถามต่อ

- ถามว่าใช้ข้อมูลอะไร -> ตอบว่าเสียงและ CHAT transcript จากหลาย corpus
- ถามว่าเชื่อถือได้แค่ไหน -> ตอบว่ามี calibration, threshold analysis, และ model card
- ถามว่าใช้แทนแพทย์ได้ไหม -> ตอบว่าไม่ได้ เป็น decision support เท่านั้น
- ถามว่าใช้งานกับพ่อแม่ได้ไหม -> ตอบว่าได้ มี public flow ภาษาไทยและ optional audio consent gate
