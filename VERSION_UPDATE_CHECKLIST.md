---
description: Checklist สำหรับอัปเดต version ก่อน commit ทุกครั้ง
---

# Version Update Checklist

เมื่อมีการเปลี่ยนแปลง code สำคัญใน project:

## Step 1: อัปเดต CHANGELOG.md

1. เปิดไฟล์ `CHANGELOG.md`
2. เพิ่ม version ใหม่ที่ด้านบนสุด (ต่อจาก version ล่าสุด)
3. ใช้รูปแบบ:
   ```markdown
   ## [v0.X.0] - 2026-04-XX
   
   ### Added
   - **Feature Name** — คำอธิบายสั้น ๆ ว่าทำอะไร
   ### Changed
   - **Module Name** — คำอธิบายสิ่งที่เปลี่ยน
   ### Fixed
   - **Bug Name** — คำอธิบาย bug ที่แก้
   ### Removed
   - **Feature Name** — คำอธิบายสิ่งที่ลบออก
   ```

## Step 2: ตัดสินใจ version bump

- **PATCH** (v0.9.0 → v0.9.1): Bug fixes, small improvements, documentation only
- **MINOR** (v0.9.0 → v0.10.0): เพิ่ม features ใหม่, backward compatible
- **MAJOR** (v0.9.0 → v1.0.0): Breaking changes, ลบ features สำคัญ, ขยาย scope ใหญ่

## Step 3: Commit พร้อม message ชัดเจน

ใช้ Conventional Commits format:
```
<type>: <subject>

<body>
```

**ตัวอย่าง:**
```
feat(audio): add echolalia ratio feature

- Add echolalia detection in data_loader.py
- Update FEATURE list in dashboard.py  
- Add echolalia to feature documentation
- Update CHANGELOG.md to v0.10.0
```

## Step 4: Push ไป GitHub

```bash
git add CHANGELOG.md <other_files>
git commit -m "feat: add echolalia ratio feature"
git push origin main
```

## Step 5: (ถ้าเป็น major milestone) สร้าง Git Tag

```bash
git tag -a v0.10.0 -m "Release v0.10.0: add echolalia ratio"
git push origin v0.10.0
```

---

# ตัวอย่างการใช้งานจริง

## Scenario 1: เพิ่ม feature ใหม่ (echolalia ratio)

1. เขียน code ใน `src/data_loader.py` → เพิ่ม echolalia detection
2. อัปเดต `app/dashboard.py` → เพิ่ม feature ใน FEATURE list
3. อัปเดต `CHANGELOG.md`:
   ```markdown
   ## [v0.10.0] - 2026-04-27
   ### Added
   - **Echolalia ratio** — ตรวจ repeated utterances (core ASD symptom)
   ```
4. Commit:
   ```bash
   git add src/data_loader.py app/dashboard.py CHANGELOG.md
   git commit -m "feat(audio): add echolalia ratio feature"
   git push origin main
   ```
5. (ถ้าเป็น release) สร้าง tag:
   ```bash
   git tag -a v0.10.0 -m "Release v0.10.0"
   git push origin v0.10.0
   ```

## Scenario 2: แก้ bug (dashboard crash)

1. แก้ code ใน `app/dashboard.py`
2. อัปเดต `CHANGELOG.md`:
   ```markdown
   ## [v0.9.1] - 2026-04-27
   ### Fixed
   - **Dashboard crash** — แก้ KeyError เมื่อ DataFrame ว่าง
   ```
3. Commit:
   ```bash
   git add app/dashboard.py CHANGELOG.md
   git commit -m "fix(dashboard): handle empty DataFrames gracefully"
   git push origin main
   ```

## Scenario 3: เปลี่ยน documentation เท่านั้น

1. อัปเดต `PROJECT_SUMMARY_TH.md` → เพิ่มผลลัพธ์ใหม่
2. อัปเดต `CHANGELOG.md`:
   ```markdown
   ## [v0.9.1] - 2026-04-27
   ### Changed
   - **PROJECT_SUMMARY_TH.md** — เพิ่มผลลัพธ์ echolalia
   ```
3. Commit:
   ```bash
   git add PROJECT_SUMMARY_TH.md CHANGELOG.md
   git commit -m "docs: update project summary with echolalia results"
   git push origin main
   ```
