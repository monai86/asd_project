---
description: Checklist สำหรับอัปเดต version และ release metadata ของ maintained runtime
---

# Version Update Checklist

ใช้ checklist นี้เมื่อมีการเปลี่ยนแปลงที่กระทบ maintained runtime ปัจจุบัน
(`apps/lingualens-app`, `apps/api`, `packages/ml`, และเอกสารหลักที่กำกับการใช้งาน)

## 1. ตัดสินใจก่อนว่าต้อง bump version หรือไม่

ไม่ต้อง bump version:
- docs-only edits
- file cleanup / repo organization
- comment, formatting, rename ที่ไม่เปลี่ยน behavior

ต้อง bump version:
- user-facing behavior เปลี่ยน
- API contract เปลี่ยน
- ML/runtime output semantics เปลี่ยน
- dependency/runtime requirement เปลี่ยน
- bug fix ที่มีผลต่อการทำงานจริง

## 2. อัปเดตไฟล์ version หลักให้ตรงกัน

เมื่อมีการ bump version ให้ตรวจอย่างน้อย:
- `README.md`
- `PROJECT_STATUS.md`
- `docs/PROJECT_SOURCE_OF_TRUTH.md`
- `CHANGELOG.md`
- frontend/backend package metadata ที่เกี่ยวข้อง

รูปแบบใน `CHANGELOG.md`:

```markdown
## [v1.6.4] - 2026-06-21

### Changed
- Short high-signal summary

### Fixed
- Short high-signal summary
```

## 3. ตรวจว่ามี hardcoded version เก่าค้างอยู่หรือไม่

ค้นหาใน repo:

```bash
rg -n "v0\\.|v1\\.[0-5]\\.|v1\\.6\\.[0-2]" README.md PROJECT_STATUS.md docs scripts apps src tests
```

ถ้าค่านั้นเป็นเพียง historical record ที่ตั้งใจเก็บไว้ ให้ย้ายออกจาก maintained
docs หรือ rewrite ให้เป็น current wording

## 4. รัน verification ก่อน commit

```bash
python3 scripts/check_repo_consistency.py
PYTHONPATH=apps/api:src pytest -m "not audio" -q
bash scripts/check_project.sh
```

## 5. Commit และ push

```bash
git add <changed_files>
git commit -m "type(scope): short summary"
git push origin main
```

AI-authored commits ต้องมี `Co-Authored-By` footer ตาม `AGENTS.md`
