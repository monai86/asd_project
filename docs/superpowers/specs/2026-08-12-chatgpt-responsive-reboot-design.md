# Design Spec: ChatGPT-Style Responsive Reboot for LinguaLens

**Date:** 2026-08-12  
**Status:** Approved by User  
**Target Surface:** `apps/lingualens-app/` (Next.js 15 PWA) & `apps/api/` (FastAPI `/api/v1`)

---

## 1. Overview & Business Goals

LinguaLens is a therapist clinical assessment web application for Thai child speech-language evaluation.
This redesign re-architects the web experience into a **ChatGPT / OpenAI-inspired Responsive PWA**, fixing broken runtime issues, clarifying user navigation, and providing a clean, accessible interface across Mobile (smartphones), iPad (tablets), and Desktop (Mac/PC).

### Key Objectives
- **Full UI/UX Modernization**: Implement a sleek OpenAI Dark Slate (`#171717`) aesthetic with responsive sidebar navigation, fluid chat session canvas, and slide-over clinical evidence drawer.
- **Cross-Device Responsiveness**: Seamless support for Mobile (1-col + slide drawer + bottom sheets), iPad (2-col fluid grid), and Desktop (3-col full workspace shell).
- **Clinical Printable PDF Report**: High-quality A4 clinical assessment report view with Print / Download PDF export capability, complete with child demographics, structured language metrics tables, clinical recommendations, clinician sign-off block, and SHA-256 cryptographic verification.
- **Robust API & Fallback Integration**: Upgrade frontend `api-client.ts` to seamlessly communicate with `apps/api` (`/api/v1`), with Toast notifications, Error Boundaries, and fail-closed local fallback so the web app never white-screens or breaks.

---

## 2. Architecture & Design System

### 2.1 Color Palette & Typography
- **Backgrounds**: Main Canvas `#171717`, Sidebar & Cards `#212121`, Hover/Active `#2f2f2f`.
- **Text**: Primary `#f3f4f6` (slate-100), Muted `#9ca3af` (slate-400), Accent Green `#10a37f` / `#16a34a`.
- **Borders & Dividers**: Subtly bordered at `#2f2f2f` / `#374151`.
- **Typography**: Inter / System Sans, high-contrast readable font sizes (14px base, 16px input, 18px-24px headers).

### 2.2 Responsive Layout Shell
- **Desktop (>= 1024px)**:
  - Left Sidebar (260px): `+ New Session`, `+ New Case`, Recent Sessions grouped by Today / 7 Days, Page Navigation (Today, Cases, Reports, Settings).
  - Center Canvas (Flex-1): Chat stream with message timeline, audio controls, and AI clinical assistant responses.
  - Right Drawer (360px): Slide-over drawer for Clinical Findings & Report Preview.
- **Tablet / iPad (768px - 1023px)**:
  - Collapsible Sidebar (icon bar or 2-col layout).
  - Touch-friendly tap targets (minimum 44x44px).
  - Right Drawer opens as overlay slide-sheet.
- **Mobile (< 768px)**:
  - Single column canvas.
  - Hamburger menu opens full-screen Slide Drawer.
  - Floating bottom action bar for microphone audio recording and message typing.
  - Clinical Findings & PDF Report open as Bottom Sheet.

---

## 3. Core Pages & Component Specification

### 3.1 App Shell & Navigation (`apps/lingualens-app/src/components/app-shell.tsx`)
- Unified shell wrapper handling theme, responsive sidebar state, mobile drawer toggles, and route navigation.
- Fail-closed redirects for canonical routes (`/today`, `/cases`, `/sessions/{sessionId}`, `/reports`, `/settings`).

### 3.2 Session Workspace (`apps/lingualens-app/src/app/sessions/[sessionId]/page.tsx`)
- **Header**: Child Case Metadata ("Nong Auto, 3y 4m"), Session Status Badge, quick view toggles (`Intake`, `Transcript`, `Findings`, `Report`).
- **Chat Stream**: Timeline of therapist notes, uploaded audio recordings, transcribed speech turns (CHI vs INV), ML cues, and AI draft suggestions.
- **Bottom Bar**: Real-time browser microphone audio recorder, drag-and-drop file uploader, observation prompt input, and `Analyze Session` trigger button.

### 3.3 Clinical Printable PDF Report View (`apps/lingualens-app/src/features/reports/components/clinical-pdf-report.tsx`)
- Structured A4 printable layout (`@media print` CSS rules):
  1. **Header**: Clinic/Institution Header + "Speech-Language Assessment Report".
  2. **Demographics**: Child Name, DOB, Evaluation Date, Evaluator Name, Case ID.
  3. **Assessment Summary Table**: Receptive Language, Expressive Language, Pragmatics, Behavioral Observations.
  4. **Clinical Findings**: TalkBank feature metrics, ML evidence cues, communication indicators.
  5. **Recommendations**: Tailored guidance for parents and educators.
  6. **Sign-off Block**: Clinician Signature image/stamp, Sign-off timestamp, SHA-256 report hash & verification QR code.
- **Export Control**: `Download PDF / Print` button calling browser `window.print()` with `@page { size: A4 portrait; margin: 15mm; }`.

---

## 4. API & Data Flow Specifications

- **Endpoint Integration**:
  - `GET /api/v1/cases` & `POST /api/v1/cases`
  - `GET /api/v1/sessions` & `POST /api/v1/sessions`
  - `POST /api/v1/sessions/{sessionId}/audio`
  - `GET /api/v1/sessions/{sessionId}/transcript`
  - `GET /api/v1/sessions/{sessionId}/findings`
  - `POST /api/v1/sessions/{sessionId}/report` & `POST /api/v1/sessions/{sessionId}/report/sign-off`
- **Error & Fallback Handling**:
  - API Client automatically detects network failure or server 5xx and falls back to local JSON workspace store without throwing unhandled exceptions.
  - User-facing Toast notifications display clean status updates (e.g. "Connecting to FastAPI backend...", "Operating in offline demo mode").

---

## 5. Verification Plan

### Automated Testing
- Frontend unit & component tests: `cd apps/lingualens-app && npm test`
- Bundle & type verification: `cd apps/lingualens-app && npm run typecheck`
- Backend check: `cd apps/api && pytest`

### Manual Verification
- Verify ChatGPT responsive shell across Desktop, iPad viewports, and Mobile screen widths.
- Test Audio recording and file upload UI.
- Test PDF report preview and print layout via browser Print preview.
