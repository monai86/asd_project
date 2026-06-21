# Thai Validation Readiness

เอกสารนี้กำหนดขอบเขตการใช้งานที่ปลอดภัยของ prototype ปัจจุบัน และสิ่งที่ยังต้องมี
ก่อนนำ workflow นี้ไปใช้กับข้อมูลเด็กไทยจริง

## Current status

ระบบปัจจุบัน:
- เป็น research/education prototype
- ใช้ workflow therapist review เป็นหลัก
- ไม่วินิจฉัย ASD
- ยังไม่มี Thai clinical validation
- ยังไม่มี Thai child dataset ที่ใช้ยืนยัน performance ใน repo นี้

## What is already in place

สิ่งที่พร้อมแล้วใน maintained runtime:
- therapist workflow ที่มี case, session, transcript QA, transcript attestation,
  feature extraction, ML review, และ report workflow
- audio-to-CHAT research pipeline สำหรับเตรียม transcript ก่อน human review
- 14-feature schema ที่ใช้ร่วมกันใน workflow ปัจจุบัน
- reference-evidence ML path ที่ fail-closed และไม่ใส่ผลลงรายงานอัตโนมัติ
- Gate 1 engineering metrics, calibration review, และ subgroup audit framework
- safety wording, consent boundaries, audit trail, และ reviewed-only workflow

## What is not yet established

สิ่งที่ยังไม่มี:
- Thai external validation
- Thai calibration
- Thai subgroup performance evidence
- production-ready clinical deployment evidence
- permission ให้แสดง diagnosis, predicted class, หรือ autonomous conclusion

## Required before Thai real-world use

ก่อนใช้กับเด็กไทยจริง ต้องมีอย่างน้อย:
- Thai child dataset ที่จัดการ consent และ privacy ถูกต้อง
- expert-reviewed transcript หรือ gold transcript
- label provenance ที่ตรวจสอบย้อนกลับได้
- ASR quality evaluation บนเสียงเด็กไทย
- feature drift analysis ระหว่าง gold transcript และ ASR transcript
- external validation แยกจากข้อมูลที่ใช้พัฒนา
- recalibration หรือ local validation ตาม population ที่จะใช้จริง
- subgroup audit ตามอายุ เพศ ภาษา และ developmental profile
- pilot workflow verification กับผู้เชี่ยวชาญในสภาพแวดล้อมจริง

## Safe claim wording

ใช้คำเหล่านี้:
- screening support
- therapist review support
- evidence review
- progress tracking
- decision support
- human-in-the-loop
- external validation required

หลีกเลี่ยงคำที่สื่อว่า:
- ระบบยืนยัน ASD ได้
- ระบบวินิจฉัยได้เอง
- ระบบผ่าน Thai clinical validation แล้ว
- ระบบพร้อมใช้งานจริงทางคลินิกแล้ว

## Current proof boundary

สิ่งที่ demo ปัจจุบันพิสูจน์ได้:
- workflow เชิงเทคนิคทำงานครบตั้งแต่ transcript review ถึง report workflow
- governance และ safety boundary ถูกวางไว้แล้ว
- ML evidence ถูกจำกัดให้อยู่ใน therapist-review flow แบบ fail-closed

สิ่งที่ demo ปัจจุบันยังพิสูจน์ไม่ได้:
- Thai clinical accuracy
- Thai deployment readiness
- diagnostic validity
- fairness/performance บนประชากรไทยจริง
