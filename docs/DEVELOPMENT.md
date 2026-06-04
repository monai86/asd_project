# Development Workflow

> **โปรเจกต์:** AI-Assisted Clinical Assessment of Autism (Term Paper)  
> **วันที่:** 26 เมษายน 2026

---

## 📋 Checklist ก่อน commit ทุกครั้ง

### 1. อัปเดต README.md (ทุกครั้งที่มีการเปลี่ยนแปลงใน project)

**สำคัญ:** README.md คือ entry point ของ project ต้องอัปเดตทุกครั้งที่มีการเปลี่ยนแปลง

**เมื่ออะไรต้องอัปเดต README.md:**
- ✅ เพิ่ม feature ใหม่
- ✅ เปลี่ยนโครงสร้างโฟลเดอร์
- ✅ เพิ่ม/ลบ dependencies สำคัญ
- ✅ เปลี่ยนวิธีรันหรือการใช้งาน
- ✅ เพิ่ม documentation ใหม่ที่สำคัญ

**สิ่งที่ไม่ต้องอัปเดต README.md:**
- ❌ การแก้ bug เล็ก ๆ
- ❌ การเปลี่ยน format code
- ❌ การเพิ่ม comments

---

### 2. อัปเดต CHANGELOG.md (เฉพาะเมื่อมีการเปลี่ยนแปลงระบบจริงๆ)

**สำคัญ:** เฉพาะการเปลี่ยนแปลง **ระบบจริงๆ** เท่านั้นที่ต้อง bump version

**สิ่งที่ไม่ต้อง bump version:**
- ❌ การจัดระเบียบไฟล์ (move files, rename folders)
- ❌ การเปลี่ยนแปลง documentation เท่านั้น (เช่น edit README.md)
- ❌ การเปลี่ยนแปลง format ของไฟล์ (เช่น indent code)
- ❌ การเพิ่ม comments หรือ docstrings

**สิ่งที่ต้อง bump version:**
- ✅ เพิ่ม feature ใหม่ใน code (เช่น add echolalia detection)
- ✅ แก้ bug ที่ส่งผลต่อการทำงาน
- ✅ เปลี่ยน behavior ของระบบ (เช่น เปลี่ยน default parameters)

เมื่อต้อง bump version:
- เพิ่ม version ใหม่ (เช่น `[v0.10.0] - 2026-04-XX`)
- บันทึกสิ่งที่เปลี่ยนแปลงในหมวด `Added`, `Changed`, `Fixed`, `Removed`
- ตัวอย่าง:
  ```markdown
  ## [v0.10.0] - 2026-04-XX
  ### Added
  - **Feature X** — คำอธิบายสั้น ๆ
  ### Changed
  - **Module Y** — แก้ไขอะไร
  ```

### 3. ทดสอบว่า code รันได้
- ถ้าเปลี่ยน code สำคัญ → รัน `python src/data_loader.py` หรือ `streamlit run app/dashboard.py` ตรวจสอบ
- ถ้าเปลี่ยนเฉพาะ documentation → ข้ามได้

### 4. Commit message ต้องชัดเจน

ใช้ **Conventional Commits** format ตามมาตรฐาน:
```
<type>[optional scope]: <subject>

<optional body>

<optional footer>
```

**Rules (จาก best practices):**
- ✅ Subject line: ไม่เกิน 50 ตัวอักษร
- ✅ Subject line: ใช้ imperative mood (เช่น "Add feature" ไม่ใช่ "Added feature")
- ✅ Subject line: ตัวแรกตัวพิมพ์ใหญ่ ไม่มีจุดท้าย
- ✅ Body: ไม่เกิน 72 ตัวอักษรต่อบรรทัด
- ✅ Body: อธิบาย **what** และ **why** (ไม่ใช่ how)
- ✅ Body: ใช้ bullet points ถ้ามีหลายข้อ
- ✅ แยก subject และ body ด้วย blank line
- ❌ หลีกเลี่ยง filler words (though, maybe, I think, kind of)
- ❌ หลีกเลี่ยงการพูดถึงตัวเอง (I, my)

**Types:**
- `feat:` — เพิ่ม feature ใหม่
- `fix:` — แก้ bug
- `docs:` — เปลี่ยน documentation เท่านั้น
- `refactor:` — refactor code (ไม่เปลี่ยน behavior)
- `style:` — แก้ format code (indent, spacing)
- `test:` — เพิ่ม/แก้ test
- `chore:` — อื่น ๆ (update dependencies, config)
- `perf:` — performance improvements
- `ci:` — continuous integration
- `build:` — เปลี่ยน build system

**ตัวอย่างดี:**
```
feat(audio): add echolalia ratio feature

Add echolalia detection to identify repeated utterances,
which is a core ASD symptom (75% prevalence).

- Add echolalia_ratio in data_loader.py
- Update FEATURE list in dashboard.py
- Update CHANGELOG.md to v0.10.0

Resolves: #123
```

**ตัวอย่างไม่ดี:**
```
fixed bug on landing page
Changed style
oops
I think I fixed it this time?
```

---

## 🌿 Branching Strategy (มาตรฐานสำหรับโปรเจกต์ขนาดเล็ก/กลาง)

### แนะนำ: ใช้ `main` branch + Git Tags (ไม่ใช้ branch แยกต่อ version)

**เพราะ:**
- Branch แยกต่อ version (เช่น `v0.1.0`, `v0.2.0`) เป็น **overkill** สำหรับ term paper
- Git tags ทำหน้าที่เดียวกัน (mark version) แต่เรียบง่ายกว่า
- ส่วนใหญ่ของ open-source projects ใช้ tags, ไม่ใช้ branch แยก version
- CHANGELOG.md เก็บ history อยู่แล้ว

### Workflow ที่แนะนำ

```
main branch (default)
  ↓
[commit changes with clear messages]
  ↓
[update CHANGELOG.md]
  ↓
git add .
git commit -m "feat: add echolalia ratio"
git push origin main
  ↓
[ทุกครั้งที่ release version ใหม่]
git tag v0.10.0
git push origin v0.10.0
```

### เมื่อไหร่ควรใช้ feature branch?

เฉพาะเมื่อมี **major feature** ที่ใช้เวลาหลายวัน/หลาย session:
- `feature/audio-pipeline` — สร้าง audio pipeline ใหม่
- `feature/deployment` — เพิ่ม deployment configuration
- `feature/thai-support` — เพิ่มภาษาไทย

**Workflow:**
```bash
git checkout -b feature/audio-pipeline
# ... develop ...
git checkout main
git merge feature/audio-pipeline
git branch -d feature/audio-purge
```

---

## 🏷️ Git Tags สำหรับ Versioning

เมื่อ release version ใหม่ (เช่น v0.9.0 → v0.10.0):

```bash
# สร้าง tag
git tag -a v0.10.0 -m "Release v0.10.0: add echolalia ratio"

# Push tag ไป GitHub
git push origin v0.10.0

# ดู tags ทั้งหมด
git tag

# ดู diff ระหว่าง tags
git diff v0.9.0..v0.10.0
```

---

## 📝 Checklist ก่อนคุยกับอาจารย์

1. **อัปเดต PROJECT_SUMMARY_TH.md** — สรุปสิ่งที่ทำไปใหม่
2. **อัปเดต DISCUSSION_TH.md** — เพิ่มประเด็นใหม่ถ้ามี
3. **อัปเดต REFERENCES.md** — เพิ่ม references ถ้ามีการใช้เทคนิคใหม่
4. **อัปเดต CHANGELOG.md** — บันทึก version ล่าสุด
5. **Push ไป GitHub** — ตรวจสอบว่าทุกอย่าง sync แล้ว
6. **Create git tag** — ถ้าเป็น major milestone

---

## 🔧 การจัดการ Dependencies

เมื่อเพิ่ม library ใหม่:
1. เพิ่มใน `requirements.txt`
2. ระบุ version แบบ compatible (เช่น `>=1.0.0` หรือ `~=1.2.0`)
3. Commit พร้อม message: `deps: add faster-whisper>=1.0.0 for ASR`

เมื่อเพิ่ม frontend library ใน `therapist-clinician-app/`:
1. อัปเดตทั้ง `package.json` และ `package-lock.json`
2. รัน `npm run test` และ `npm run build`
3. รัน `npm audit --omit=dev` ก่อน release
4. ถ้าเปลี่ยน PWA หรือ iOS shell ให้รัน `npm run cap:sync`
5. ตรวจว่า service worker ไม่ cache clinical records, audio, transcripts, reports, หรือ API responses

เมื่อเปลี่ยน Supabase pilot schema หรือ RLS:
1. อัปเดต `docs/sql/001_initial_clinical_schema.sql` และ/หรือ `docs/sql/002_indexes_rls.sql`
2. เพิ่ม test ที่ยืนยัน owner isolation และ admin boundary
3. ตรวจว่า `audit_logs` ไม่ถูก expose ผ่าน browser RLS
4. ตรวจว่า child case ใช้ anonymized child code เท่านั้น
5. ตรวจว่า media upload ยังผ่าน signed upload intent ไม่ใช่ permanent storage key

---

## 🚨 ข้อห้าม

- ❌ อย่า commit โดยไม่อัปเดต CHANGELOG.md (สำคัญมาก)
- ❌ อย่า commit ข้อความที่ไม่ชัดเจน (เช่น "update", "fix bug")
- ❌ อย่า push โค้ดที่รันไม่ได้
- ❌ อย่า commit sensitive data (API keys, tokens)
- ❌ อย่า commit binary files ขนาดใหญ่ (`.wav`, `.mp3`)

---

## 📚 References

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Tagging](https://git-scm.com/book/en/v2/Git-Basics-Tagging)
- [Semantic Versioning](https://semver.org/)
