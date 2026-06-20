# Project Source of Truth

เอกสารนี้เป็นจุดอ้างอิงหลักสำหรับคนและ AI agents ทุกตัวที่ทำงานใน repository
นี้ ไม่ว่าจะมาจาก Codex, Antigravity, Claude หรือเครื่องมืออื่น

## สถานะปัจจุบัน

- รุ่นโครงการ: `v1.6.1`
- active user-facing surfaces และ API ใช้ version `v1.6.1`
- branch หลัก: `main`
- Therapist frontend หลัก: `apps/therapist-app-v2/`
- Therapist workflow API หลัก: `apps/api/`
- ML/audio/research libraries: `packages/` และ `src/`
- ระบบเป็น research/education prototype และ clinical review support เท่านั้น
- ระบบไม่วินิจฉัย ASD และยังไม่มี Thai clinical validation

## Canonical runtime surfaces

| Surface | Canonical path | สถานะ |
|---|---|---|
| Therapist web app | `apps/therapist-app-v2/` | Active |
| Therapist workflow API | `apps/api/` | Active |
| Public screening | `public-screening/` | Active educational demo |
| Advisor dashboard | `presentation-dashboard/` | Active presentation surface |
| Research ML/audio | `packages/`, `src/`, `scripts/` | Active research tooling |

`apps/api` เป็น backend ที่ frontend หลักเรียกใช้ผ่าน `/api/v1`.

`src/therapist_backend` เป็น legacy research/pilot API ที่ยังเก็บไว้เพราะชุด
research tests และ workflow เดิมบางส่วนยังใช้มัน ห้ามเพิ่ม endpoint ผลิตภัณฑ์
ใหม่ที่นี่ เว้นแต่งานนั้นระบุชัดว่าแก้ legacy compatibility.

`src/clinical_workflow` เป็น legacy/research domain implementation และไม่ใช่
persistence layer หลักของ Therapist App v2.

## Removed and generated paths

- `therapist-clinician-app/` รุ่น Vite/Capacitor ถูกถอดออกจาก Git แล้ว
- `.next/`, `dist/`, `.local/`, `node_modules/`, `*.tsbuildinfo` เป็น generated
  หรือ local runtime files และต้องไม่ commit
- ถ้าโฟลเดอร์ legacy ปรากฏในเครื่องจาก build เก่า ให้ลบได้โดยไม่กระทบ source

## Backend source-of-truth rules

1. Backend records เป็น source of truth เมื่อมี case/session/transcript/report ID
2. `sessionStorage` เป็น UI cache หรือ local fallback เท่านั้น
3. JSON repository เป็น default สำหรับ local prototype
4. Memory repository ใช้เฉพาะ tests และ intentional reset
5. SQL repository เป็น scaffold ที่ยังไม่ pilot-hardened
6. Browser ห้ามสร้าง ML result หรือ report-final state แทน backend

## ML status

โปรเจกต์มี ML สองชั้นที่ต้องไม่สับสน:

1. **Research benchmarks** — `src/classifier.py`, `src/deep_learning.py` และ
   artifacts เดิม ใช้รายงานผลการทดลองบน public English-language corpora
2. **Reference evidence review** — `packages/ml/`,
   `artifacts/reference_evidence/` และ provider ใน `apps/api`

Gate 1 artifact ล่าสุดมีสถานะ `promoted_candidate` ในเชิง engineering:

- sensitivity: `0.8862`
- sensitivity lower 95% CI: `0.8091`
- specificity: `0.6124`
- ECE: `0.0332`
- abstention: `0.3166`

คำว่า `promoted_candidate` ไม่ได้หมายถึง clinical validation หรืออนุญาตให้แสดง
diagnosis/probability. Runtime therapist workflow ยังคงแสดงเฉพาะ evidence/review
cues แบบ fail-closed และไม่ใส่ผลลงรายงานอัตโนมัติ

## Version policy

- รุ่นผลิตภัณฑ์รวมใช้สาย `v1.6.x`
- รุ่นย่อย `v0.7–v0.9` ใน API/ML docs คือ component milestones ไม่ใช่รุ่นรวม
- `README.md`, `PROJECT_STATUS.md` และหัวบนสุดของ `CHANGELOG.md` ต้องตรงกัน
- เอกสาร phase/spec/plan เก่าเป็น historical record ไม่ใช่คำสั่ง runtime

## Standard commands

```bash
# Active API
cd apps/api
PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# Active therapist frontend
cd apps/therapist-app-v2
npm ci
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run dev

# Full verification
cd /path/to/asd-project
bash scripts/check_project.sh
```

## Rules for every agent

1. อ่านไฟล์นี้และ `AGENTS.md` ก่อนแก้โค้ด
2. ตรวจ branch และ `git status` ก่อนเริ่ม
3. ห้ามสร้าง therapist frontend/backend ชุดใหม่โดยไม่เพิ่ม ADR
4. ห้ามเปลี่ยน canonical path โดยแก้เอกสารเพียงบางไฟล์
5. ห้าม commit generated/local files
6. ห้ามใช้ข้อมูลจริงหรือ identifier ใน fixtures/logs
7. หลังเปลี่ยนโครงสร้าง ต้องอัปเดตไฟล์นี้ README และ CHANGELOG พร้อมกัน
8. อย่าอ้างว่า clinical-ready จาก software tests หรือ Gate 1
