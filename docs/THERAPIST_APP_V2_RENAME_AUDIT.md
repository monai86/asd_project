# THERAPIST_APP_V2 Rename Audit

เอกสารนี้สรุปว่า string/prefix `THERAPIST_APP_V2` ที่ยังเหลืออยู่ใน repository
ควรถูกมองเป็น 3 กลุ่มต่างกัน เพื่อไม่ให้ rename แบบกว้างเกินไปจนทำให้ runtime,
tests, deployment instructions, หรือ historical evidence เสียความสอดคล้อง

## Source of truth

- Canonical therapist frontend ปัจจุบันคือ `apps/lingualens-app/`
- Canonical therapist API ปัจจุบันคือ `apps/api/`
- ดู [docs/PROJECT_SOURCE_OF_TRUTH.md](./PROJECT_SOURCE_OF_TRUTH.md)

## 1. Keep for now: runtime contract

กลุ่มนี้ยังไม่ควร rename แบบตรงๆ เพราะเป็นส่วนหนึ่งของ environment contract,
deployment contract, หรือค่า default ที่ผูกกับ tests และ runbooks ปัจจุบัน

- Backend env contract ใน [apps/api/app/core/config.py](/Users/porschecaa/lingualens/apps/api/app/core/config.py:128)
  ยังอ่านค่า `THERAPIST_APP_V2_*` โดยตรงหลายตัว
- Production/runtime rules ใน [docs/PROJECT_SOURCE_OF_TRUTH.md](/Users/porschecaa/lingualens/docs/PROJECT_SOURCE_OF_TRUTH.md:78)
  และ [docs/PROJECT_SOURCE_OF_TRUTH.md](/Users/porschecaa/lingualens/docs/PROJECT_SOURCE_OF_TRUTH.md:120)
  ยังอ้าง `THERAPIST_APP_V2_*` เป็น operational rules
- Auth/deploy contracts เช่น
  [docs/SUPABASE_AUTH_CONTRACT.md](/Users/porschecaa/lingualens/docs/SUPABASE_AUTH_CONTRACT.md:23),
  [docs/PRODUCTION_DEPLOYMENT.md](/Users/porschecaa/lingualens/docs/PRODUCTION_DEPLOYMENT.md:80),
  [docs/DEPLOYMENT.md](/Users/porschecaa/lingualens/docs/DEPLOYMENT.md:57),
  [docs/ONE_DAY_PILOT_RUNBOOK.md](/Users/porschecaa/lingualens/docs/ONE_DAY_PILOT_RUNBOOK.md:52)
- Tooling/scripts ที่ generate runtime snippets หรือใช้ env names เดิม เช่น
  [scripts/create_supabase_runtime_env_snippets.sh](/Users/porschecaa/lingualens/scripts/create_supabase_runtime_env_snippets.sh:49),
  [scripts/check_api_migrations.py](/Users/porschecaa/lingualens/scripts/check_api_migrations.py:54)
- Frontend E2E config ที่ inject env เดิม เช่น
  [apps/lingualens-app/playwright.config.ts](/Users/porschecaa/lingualens/apps/lingualens-app/playwright.config.ts:28)

ข้อสรุป:
- ถ้าจะ rename กลุ่มนี้ ควรทำเป็น migration แยก
- ควรรองรับทั้ง `LINGUALENS_*` และ `THERAPIST_APP_V2_*` ชั่วคราว
- ต้องอัปเดต docs, scripts, tests, deployment env, และ release artifacts พร้อมกัน

## 2. Rename safely now: product wording and labels

กลุ่มนี้ rename ได้ค่อนข้างปลอดภัย เพราะเป็น wording/metadata ไม่ใช่ runtime key

- คำอธิบายใน [DEVELOPER_SETUP.md](/Users/porschecaa/lingualens/DEVELOPER_SETUP.md:57)
  และ [DEVELOPER_SETUP.md](/Users/porschecaa/lingualens/DEVELOPER_SETUP.md:72)
  ยังเรียก maintained frontend ว่า "Therapist App v2"
- สถานะโครงการใน [PROJECT_STATUS.md](/Users/porschecaa/lingualens/PROJECT_STATUS.md:52)
  และ [PROJECT_STATUS.md](/Users/porschecaa/lingualens/PROJECT_STATUS.md:71)
  ยังใช้ชื่อเดิมใน prose
- คำอธิบาย Docker comments เช่น
  [Dockerfile](/Users/porschecaa/lingualens/Dockerfile:26) และ
  [Dockerfile](/Users/porschecaa/lingualens/Dockerfile:36)
- ข้อความใน [AGENTS.md](/Users/porschecaa/lingualens/AGENTS.md:24)
  ที่เรียก `apps/api/` ว่า backend for the Therapist App v2 local workflow
- ชื่อ package metadata ใน
  [apps/lingualens-app/package-lock.json](/Users/porschecaa/lingualens/apps/lingualens-app/package-lock.json:2)
  และ [apps/lingualens-app/package-lock.json](/Users/porschecaa/lingualens/apps/lingualens-app/package-lock.json:8)
  ยังเป็น `therapist-app-v2`
- Logger namespace ใน
  [apps/api/app/core/logging.py](/Users/porschecaa/lingualens/apps/api/app/core/logging.py:93)
  ยังเป็น `therapist_app_v2.request`

ข้อสรุป:
- prose/comments/metadata rename ได้ก่อน
- logger namespace rename ได้ แต่ควรทำพร้อมอัปเดต tests/log dashboards
- package name rename ได้ แต่ควรทำคู่กับ `package-lock.json` regeneration เพื่อไม่ให้ metadata ค้าง

## 3. Keep unchanged: historical records

กลุ่มนี้ควรเก็บชื่อเดิมไว้ เพราะเป็นหลักฐานเชิงประวัติศาสตร์หรือ artifact ที่อ้างถึง
สถานะของระบบในช่วงเวลานั้น

- ADR เช่น
  [docs/adr/0013-add-parallel-nextjs-therapist-app-v2.md](/Users/porschecaa/lingualens/docs/adr/0013-add-parallel-nextjs-therapist-app-v2.md:1)
- Historical audit/spec docs เช่น
  `docs/THERAPIST_APP_V2_*`
- Release artifacts ใต้ `docs/release_artifacts/`
- Generated env evidence files ที่บันทึกค่าจริง ณ วันปล่อยระบบ

ข้อสรุป:
- ไม่ควร rewrite ชื่อใน historical artifacts
- ถ้าต้องการลดความสับสน ให้เพิ่ม note อธิบายว่าเป็น legacy naming

## Recommended migration order

1. Rename prose/comments/labels ที่ไม่กระทบ runtime
2. Rename package/logger metadata พร้อมอัปเดต tests
3. ออก compatibility layer ใน API config ให้รองรับ `LINGUALENS_*`
   ควบคู่กับ `THERAPIST_APP_V2_*`
4. ย้าย docs/runbooks หลักไปใช้ `LINGUALENS_*`
5. หลัง rollout ครบ ค่อยเลิก support `THERAPIST_APP_V2_*`

## Minimum safe first pass

รอบแรกที่เสี่ยงต่ำสุดควรจำกัดแค่:

- `DEVELOPER_SETUP.md`
- `PROJECT_STATUS.md`
- `AGENTS.md`
- `Dockerfile` comments
- logger namespace + tests ที่เกี่ยวข้อง
- package metadata ของ `apps/lingualens-app`

ไม่ควรเริ่มจาก:

- `apps/api/app/core/config.py`
- deploy/auth runbooks ที่เป็น operational contract
- `docs/PROJECT_SOURCE_OF_TRUTH.md`
- release artifacts และ ADR เก่า
