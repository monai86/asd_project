# Project Source of Truth

เอกสารนี้เป็นจุดอ้างอิงหลักสำหรับคนและ AI agents ทุกตัวที่ทำงานใน repository
นี้ ไม่ว่าจะมาจาก Codex, Antigravity, Claude หรือเครื่องมืออื่น

## สถานะปัจจุบัน

- รุ่นโครงการ: `v1.6.3`
- active user-facing surfaces และ API ใช้ version `v1.6.3`
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
| Research ML/audio | `packages/`, `src/`, `scripts/` | Active research tooling |

`apps/api` เป็น backend ที่ frontend หลักเรียกใช้ผ่าน `/api/v1`.

`src/therapist_backend` เป็น legacy research/pilot API ที่ยังเก็บไว้เพราะชุด
research tests และ workflow เดิมบางส่วนยังใช้มัน ห้ามเพิ่ม endpoint ผลิตภัณฑ์
ใหม่ที่นี่ เว้นแต่งานนั้นระบุชัดว่าแก้ legacy compatibility.

`src/clinical_workflow` เป็น legacy/research domain implementation และไม่ใช่
persistence layer หลักของ Therapist App v2.

## Removed and generated paths

- `therapist-clinician-app/` รุ่น Vite/Capacitor ถูกถอดออกจาก Git แล้ว
- `public-screening/` และ `presentation-dashboard/` ถูกถอดออกจาก working tree
  เพื่อให้ repository เหลือเฉพาะ maintained surfaces
- legacy benchmark pipeline (`src/classifier.py`, `src/deep_learning.py`,
  `src/fairness_metrics.py`, `scripts/compute_fairness_metrics.py`) ถูกถอดออก
  จาก working tree แล้ว
- `.next/`, `dist/`, `.local/`, `node_modules/`, `*.tsbuildinfo` เป็น generated
  หรือ local runtime files และต้องไม่ commit
- ถ้าโฟลเดอร์ legacy ปรากฏในเครื่องจาก build เก่า ให้ลบได้โดยไม่กระทบ source
- เอกสาร implementation plans/specs เก่าถูกเก็บใน Git history ไม่อยู่ใน
  working tree ปัจจุบัน

## Backend source-of-truth rules

1. Backend records เป็น source of truth เมื่อมี case/session/transcript/report ID
2. `sessionStorage` เป็น UI cache หรือ local fallback เท่านั้น
3. JSON repository เป็น default สำหรับ local prototype
4. Memory repository ใช้เฉพาะ tests และ intentional reset
5. SQL repository เป็น scaffold ที่ยังไม่ pilot-hardened
6. Browser ห้ามสร้าง ML result หรือ report-final state แทน backend
7. Signed-off reports ต้องมี backend-generated signed snapshot, SHA-256 report
   hash, signer, version และ export timestamp เพื่อ audit/export ย้อนหลังได้;
   การแก้ report หลัง sign-off ต้องสร้าง draft revision ใหม่ที่อ้างถึง report
   เดิม ไม่แก้ signed snapshot เดิมแบบเงียบ
8. AI report drafting ต้อง default off และเปิดด้วย explicit environment หรือ
   organization opt-in เท่านั้น; ทุก AI draft request ต้องเก็บ provider/model/
   input-hash provenance และยังต้อง editable/rejectable ก่อน sign-off
9. API rate limiting ต้องเปิดได้ด้วย server-side configuration และ 429 response
   ต้องเป็นข้อความทั่วไป ไม่มี child identifier, transcript, audio key หรือ
   clinical content
10. CI ต้องรัน repository consistency และ secret scan ก่อน test/deploy; dependency
    audit เป็น production gate ที่ต้องไม่มี unresolved critical/high findings
    ก่อน public production launch
11. Structured request logs ต้องใช้ route template หรือ sanitized path เท่านั้น
    และต้องไม่บันทึก child identifier, transcript text, audio content, storage key,
    raw file name หรือ raw URL ที่มี clinical identifiers
12. CORS origins ต้องมาจาก server-side configuration เท่านั้น; production ห้าม
    ใช้ wildcard/empty origins และ unsafe HTTP methods ต้องมี Origin guard ที่
    reject untrusted origins ด้วย generic 403
13. Production runtime (`THERAPIST_APP_V2_MOCK_MODE=false`) ต้อง fail-closed ถ้า
    ยังใช้ repository/storage/job queue แบบ local/demo หรือใช้ database/Redis URL
    default; secrets ต้องมาจาก managed secret store และหมุน credentials ได้
14. Production database ต้องมี backup/PITR และ restore drill ตาม
    `docs/BACKUP_RESTORE_RUNBOOK.md`; CI/local verification ต้องมี API migration
    smoke check ที่สร้างฐานใหม่และ migrate ถึง Alembic head
15. Incident response ต้องหยุด rollout ทันทีเมื่อพบ cross-tenant exposure,
    consent bypass, audit loss หรือ fabricated ASR output และต้องทำตาม
    `docs/INCIDENT_RESPONSE_RUNBOOK.md` โดยไม่คัดลอก clinical content ลง
    operational tools
16. In-app notifications และ email ต้องเป็น generic operational messages เท่านั้น
    และต้องไม่ใส่ child identifiers, transcript text, audio content, storage keys,
    raw filenames, report excerpts หรือ clinical content
17. Audit events ต้องมี actor, action, target, outcome, timestamp และ correlation
    ID และต้องไม่บันทึก child identifiers, transcript text, audio content, storage
    keys, raw filenames, report excerpts หรือ clinical content
18. Production observability ต้องเปิดใช้งานด้วย approved provider เช่น Sentry,
    CloudWatch หรือ OTLP และต้องมี critical alert route; telemetry tags/details
    ต้องเป็น operational metadata เท่านั้น และห้ามมี child identifiers, transcript
    text, audio content, storage keys, raw filenames, report excerpts หรือ
    clinical content
19. Privacy operations ต้องบันทึก retention policy, legal hold, deletion-review
    state และ evidence-retention summary; deletion review ห้าม complete ระหว่าง
    legal hold และห้ามลบ audit/sign-off evidence อัตโนมัติ
20. Production secrets ต้องมาจาก managed secret store เท่านั้น และต้องกำหนด
    credential rotation runbook; ห้ามใช้ local env/demo defaults เป็น production
    secret source
21. Production architecture freeze artifacts are active controls:
    `docs/adr/0015-supabase-fastapi-production-boundary.md`,
    `docs/adr/0016-responsive-web-pwa-only.md`, `docs/THREAT_MODEL.md`,
    `docs/DATA_FLOW_DIAGRAM.md`, and
    `docs/DATA_CLASSIFICATION_INVENTORY.md`.
22. Browser/PWA clients may use Supabase Auth and FastAPI-issued short-lived
    signed storage URLs only; all clinical reads/writes and workflow transitions
    must pass through `apps/api`.
23. Therapist App v2 is responsive web/PWA only. Do not recreate the removed
    Vite/Capacitor app or add a native shell without a new accepted ADR.

## ML status

Current ML runtime surface คือ **Reference evidence review** ใน `packages/ml/`,
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
- component/schema/provider version tags ต้องสอดคล้องกับ maintained runtime ปัจจุบัน
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
