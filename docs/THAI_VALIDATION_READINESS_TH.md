# Thai Validation Readiness

> สถานะ v1.3.0: Advisor-demo readiness + Thai ASR Drift Simulation  
> เอกสารนี้ใช้กำหนดขอบเขตที่ปลอดภัยของ prototype และสิ่งที่ต้องทำก่อนนำไปใช้กับเด็กไทยจริง

## A. Current Status

โมเดลปัจจุบันถูก train/evaluate จาก public corpora ภาษาอังกฤษในรูปแบบ CHAT/TalkBank/ASDBank เป็นหลัก และใช้เพื่อสาธิต workflow ของ AI-assisted screening support, risk estimate, decision support และ progress tracking

ข้อจำกัดสำคัญ:

- ยังไม่ได้ validated กับข้อมูลเด็กไทย
- ยังไม่มี Thai child clinical dataset ในโปรเจกต์นี้
- ยังไม่ควรใช้เป็นเครื่องมือวินิจฉัย ASD
- ยังไม่พร้อมสำหรับ clinical deployment
- ผลลัพธ์ทุกแบบต้องอ่านร่วมกับผู้เชี่ยวชาญแบบ human-in-the-loop

## B. What Is Already Ready

สิ่งที่ prototype เตรียมไว้แล้ว:

- audio/CHAT pipeline สำหรับแปลง audio เป็น `.cha` และสกัด features
- 14-feature schema ที่ใช้ร่วมกันระหว่าง model, dashboard และ artifacts
- Model Trust dashboard สำหรับ threshold, calibration, fairness audit, decision curve, subgroup และ leave-one-corpus-out review
- uncertainty band เพื่อไม่บังคับผลลัพธ์ binary เมื่อโมเดลไม่มั่นใจ
- XAI/explainability เพื่อดู feature contribution ของแต่ละ screening risk estimate
- progress tracking จาก longitudinal sessions
- parent-safe wording และ no-data-retention framing ใน public demo
- AI Transcript Reviewer สำหรับตรวจ `.cha`, Thai language tag readiness และ ASR confidence ก่อน feature extraction
- Therapist Progress Report สำหรับสรุป trend หลาย session เป็น Markdown/PDF โดยไม่สรุปผลทางการแพทย์แทนผู้เชี่ยวชาญ
- Printable Progress Report view ใน Therapist app สำหรับสาธิตรายงานติดตามพัฒนาการแบบ human-in-the-loop พร้อม audit trail ใน mock mode
- AI Speech Therapist Assistant สำหรับสรุป transcript quality, speech-language patterns, screening risk estimates และ progress trends ให้ therapist review
- Clinician Workflow Simulator สำหรับสาธิต transcript QA, screening pattern interpretation และ progress case brief ใน workflow เดียว
- fairness/calibration CSV exports สำหรับ ECE, Brier score, group TPR/FPR difference และ demographic parity difference บนข้อมูลเดิม
- Thai ASR Drift Simulation จากข้อมูล synthetic mock profiles 40 ราย เพื่อสาธิตว่า WER อาจทำให้ MLU/TTR/echolalia ratio เพี้ยนได้อย่างไร ก่อนมีข้อมูลเด็กไทยจริง

## B.1 Thai ASR Drift Simulation Boundary

`Thai ASR Drift Simulation` เป็นเครื่องมือวางแผนและสื่อสารความเสี่ยงของ ASR เท่านั้น:

- ใช้ข้อมูล synthetic/mock ไม่ใช่ข้อมูลเด็กไทยจริง
- ใช้จำลอง WER 10%, 25%, 40% เพื่อดู feature drift ของ MLU, TTR และ echolalia ratio
- ใช้เป็น pre-validation readiness artifact สำหรับคุยเรื่อง gold transcript, ASR WER และ feature drift protocol
- ไม่ใช่ Thai validation dataset
- ไม่ใช่ clinical validation result
- ห้ามใช้ตัวเลข simulation เพื่อ claim ความแม่นยำกับเด็กไทย

## C. What Is Still Required For Real Thai Deployment

ก่อนใช้งานจริงกับเด็กไทย ต้องมีอย่างน้อย:

- Thai child speech/audio dataset
- expert-confirmed labels จากนักบำบัดหรือแพทย์ผู้เชี่ยวชาญ
- metadata ด้าน age, sex, language background และบริบทการบันทึก
- gold transcript หรือ human-reviewed transcript
- ASR quality evaluation สำหรับเสียงเด็กไทย
- feature drift analysis ระหว่าง gold transcript และ ASR transcript
- external validation แยกจากข้อมูลที่ใช้พัฒนา
- calibration สำหรับ population ไทย
- subgroup performance แยกตามอายุ เพศ ภาษา และกลุ่มพัฒนาการ
- fairness and calibration monitoring หลัง recalibration กับข้อมูลไทย
- IRB/consent/privacy workflow ที่ชัดเจน
- clinician workflow testing ก่อนตัดสินใจ deploy

## D. Minimal Future Pilot Design

pilot ระยะ feasibility ควรเริ่มขนาดเล็กและเน้นตรวจ workflow มากกว่าการ claim clinical accuracy:

- 30-50 cases เป็น feasibility pilot
- ถ้าเป็นไปได้ควรมีกลุ่ม ASD / TD / developmental delay
- audio 5-10 นาทีต่อเด็กหนึ่งคน
- transcript ต้องผ่าน human review
- เก็บ metadata อายุ เพศ ภาษาในบ้าน และบริบท session
- เปรียบเทียบ gold transcript features vs ASR transcript features
- เปรียบเทียบ original English-trained model vs recalibrated model
- เปรียบเทียบ screening output กับ expert assessment
- รายงานผลเป็น feasibility, data quality, feature drift และ calibration readiness ไม่ใช่ Thai diagnostic validation

## E. Safe Claim Wording

ใช้คำเหล่านี้:

- screening support
- risk estimate
- progress tracking
- decision support
- requires expert assessment
- human-in-the-loop
- external validation required

หลีกเลี่ยง wording ที่สื่อว่า:

- ระบบสรุปผลทางการแพทย์ได้เอง
- ระบบยืนยัน ASD ได้
- ระบบผ่าน validation กับเด็กไทยแล้ว
- ระบบแทน clinician ได้
- ระบบพร้อมใช้งานจริงทางคลินิกแล้ว

ถ้ากล่าวถึง parent screening tools ภายนอก ให้ระบุว่าเป็นเครื่องมือ established ภายนอก และต้องตรวจ permission/licensing ก่อนทำ electronic หรือ commercial use ห้าม copy คำถาม M-CHAT-R/F เข้าโปรเจกต์นี้

## AI Speech Therapist Assistant

Assistant layer นี้ทำหน้าที่ช่วยนักบำบัดด้านภาษาและการสื่อสารอ่านผลจากระบบเดิมอย่างปลอดภัย:

- สรุป Transcript QA ว่า transcript ใช้ต่อได้หรือควรให้คนตรวจเพิ่ม
- อธิบาย speech-language pattern จาก 14-feature schema โดยใช้ wording แบบ descriptive
- สรุป screening risk estimate เมื่อมี probability จากโมเดล
- สรุป progress trend จากหลาย session และสร้าง therapist-facing case brief

Assistant นี้เป็น decision support เท่านั้น ต้องมี human-in-the-loop และยังต้องใช้ร่วมกับ expert assessment เสมอ ในบริบทไทยยังต้องมี Thai validation dataset, external validation, calibration และ subgroup audit ก่อนใช้งานจริง

## v0.19.0 Readiness Enhancements

v0.19.0 เพิ่มชั้นตรวจสอบที่ทำได้โดยไม่ต้องใช้ Thai child data:

- ตรวจ Thai characters ใน utterance และเตือนเมื่อ `@Languages` ยังไม่มี `tha`
- อ่านค่า ASR/diarization confidence จาก transcript metadata หากมี และเตือนเมื่อ average confidence ต่ำกว่า 0.6
- สร้าง fairness/calibration audit จาก `binary_oof_predictions.csv` เพื่อดู ECE, Brier score, TPR/FPR difference และ demographic parity difference
- เพิ่ม PDF export สำหรับ therapist progress report
- เพิ่ม Clinician Workflow Simulator เพื่อทดลอง workflow แบบ human-in-the-loop

ข้อควรระวัง: fairness/calibration audit ในรอบนี้ใช้ English-speaking public corpora เป็นหลัก จึงเป็น governance readiness signal ไม่ใช่ Thai clinical validation result

## F. No Thai Validation Data Yet: What This Demo Proves

ถึงแม้ยังไม่มี Thai clinical validation data, demo นี้แสดง readiness ได้ว่า:

- technical workflow เป็นไปได้ ตั้งแต่ audio/CHAT ไปจนถึง features, risk estimate และ report
- model governance structure ถูกเตรียมไว้ เช่น model card, uncertainty band, calibration view, fairness audit และ subgroup audit framework
- reporting and safety layer มีแล้ว เช่น parent-safe wording, AI Transcript Reviewer, ASR confidence warning และ Thai-safe therapist report
- therapist-facing explanation layer มีแล้วผ่าน AI Speech Therapist Assistant
- Thai ASR Drift Simulation ช่วยอธิบายความเสี่ยงของ ASR-to-feature drift ก่อนทำ pilot จริง
- ระบบสามารถรับ Thai validation data ในอนาคตผ่าน schema และ workflow เดิม

แต่ demo นี้ยังไม่พิสูจน์ Thai clinical accuracy และไม่ควรใช้เพื่อบอกว่าโมเดลแม่นยำสำหรับเด็กไทย จนกว่าจะมี external validation, calibration และ expert-reviewed Thai dataset ที่เหมาะสม
