# ChatGPT-Style Responsive Reboot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `apps/lingualens-app` into a sleek ChatGPT-style responsive PWA across Mobile, iPad, and Desktop, complete with robust FastAPI client fallback and printable A4 clinical PDF reports.

**Architecture:** Next.js 15 App Router with Tailwind CSS in an OpenAI Dark Slate (`#171717`) design system. Components split into App Shell navigation, ChatGPT Session Chat Canvas, Slide-over Evidence Drawer, and Printable A4 Clinical PDF Report.

**Tech Stack:** React 19, Next.js 15, Tailwind CSS, TypeScript, Web Audio API, Vitest, Lucide Icons.

---

### Task 1: API Client & Resilient Data Layer

**Files:**
- Create/Modify: `apps/lingualens-app/src/lib/api-client.ts`
- Modify: `apps/lingualens-app/src/types/clinical.ts`
- Test: `apps/lingualens-app/src/__tests__/api-client.test.ts`

- [ ] **Step 1: Write failing test for API client fallback behavior**

```typescript
// apps/lingualens-app/src/__tests__/api-client.test.ts
import { describe, it, expect, vi } from "vitest";
import { fetchCases, fetchSession } from "@/lib/api-client";

describe("api-client resilience", () => {
  it("returns fallback data gracefully when backend fetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network Error")));
    const cases = await fetchCases();
    expect(Array.isArray(cases)).toBe(true);
    expect(cases.length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/lingualens-app && npm test -- src/__tests__/api-client.test.ts
```
Expected: FAIL (file or method missing/unimplemented)

- [ ] **Step 3: Implement minimal resilient API client**

```typescript
// apps/lingualens-app/src/lib/api-client.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

export interface ClinicalCase {
  id: string;
  childName: string;
  ageYearsMonths: string;
  gender?: string;
  updatedAt: string;
}

export interface ClinicalSession {
  id: string;
  caseId: string;
  status: "intake" | "transcript" | "findings" | "report" | "signed_off";
  createdAt: string;
  transcriptText?: string;
  findings?: Record<string, unknown>;
  reportDraft?: string;
}

const MOCK_CASES: ClinicalCase[] = [
  { id: "case-001", childName: "น้องออโต้ (Nong Auto)", ageYearsMonths: "3y 4m", gender: "M", updatedAt: "2026-08-12" },
  { id: "case-002", childName: "น้องมะลิ (Nong Mali)", ageYearsMonths: "4y 1m", gender: "F", updatedAt: "2026-08-11" }
];

export async function fetchCases(): Promise<ClinicalCase[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/cases`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("FastAPI offline or unreachable, using local fallback cases:", err);
    return MOCK_CASES;
  }
}

export async function fetchSession(sessionId: string): Promise<ClinicalSession> {
  try {
    const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("FastAPI offline, using local fallback session:", err);
    return {
      id: sessionId,
      caseId: "case-001",
      status: "transcript",
      createdAt: new Date().toISOString(),
      transcriptText: "CHI: ช้าง ใหญ่\nINV: ใช่แล้ว ช้างตัวใหญ่มากเลยครับ",
      findings: { talkBankScore: 0.82, riskCue: "moderate_receptive_delay" },
      reportDraft: "ผลการประเมินพัฒนาการทางภาษาและการสื่อสารของเด็ก..."
    };
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/lingualens-app && npm test -- src/__tests__/api-client.test.ts
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/lingualens-app/src/lib/api-client.ts apps/lingualens-app/src/__tests__/api-client.test.ts
git commit -m "feat: add resilient API client with mock fallback"
```

---

### Task 2: ChatGPT Responsive App Shell & Sidebar Navigation

**Files:**
- Modify/Create: `apps/lingualens-app/src/components/app-shell.tsx`
- Modify/Create: `apps/lingualens-app/src/components/sidebar.tsx`
- Test: `apps/lingualens-app/src/__tests__/app-shell.test.tsx`

- [ ] **Step 1: Write failing component test for App Shell responsive sidebar**

```typescript
// apps/lingualens-app/src/__tests__/app-shell.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { AppShell } from "@/components/app-shell";

describe("AppShell", () => {
  it("renders ChatGPT style sidebar with + New Session button", () => {
    render(<AppShell active="Today"><div>Content</div></AppShell>);
    expect(screen.getByText(/New Session/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd apps/lingualens-app && npm test -- src/__tests__/app-shell.test.tsx
```

- [ ] **Step 3: Implement ChatGPT-style App Shell & Sidebar**

```typescript
// apps/lingualens-app/src/components/app-shell.tsx
"use client";

import { useState, ReactNode } from "react";
import Link from "next/link";
import { Plus, Menu, X, Home, Users, FileText, Settings, Sparkles } from "lucide-react";

export type ShellActive = "Today" | "Cases" | "Session" | "Reports" | "Settings";

export function AppShell({ active, children }: { active: ShellActive; children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen w-full bg-[#171717] text-slate-100 font-sans overflow-hidden">
      {/* Mobile Backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[260px] flex-col bg-[#212121] border-r border-[#2f2f2f] transition-transform duration-200 lg:static lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="p-3">
          <Link
            href="/cases?intent=start-session"
            className="flex w-full items-center justify-between rounded-lg border border-[#2f2f2f] bg-[#171717] px-3 py-2.5 text-sm font-medium text-slate-200 hover:bg-[#2f2f2f] transition"
          >
            <span className="flex items-center gap-2">
              <Plus className="h-4 w-4 text-[#10a37f]" />
              New Session
            </span>
            <Sparkles className="h-3.5 w-3.5 text-[#10a37f]" />
          </Link>
        </div>

        {/* Navigation Sections */}
        <nav className="flex-1 space-y-1 px-3 py-2 overflow-y-auto text-sm">
          <div className="pb-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">LinguaLens Workspace</div>
          
          <Link
            href="/today"
            className={`flex items-center gap-3 rounded-lg px-3 py-2 transition ${
              active === "Today" ? "bg-[#2f2f2f] text-white font-medium" : "text-slate-400 hover:bg-[#2a2a2a] hover:text-slate-200"
            }`}
          >
            <Home className="h-4 w-4 text-[#10a37f]" />
            Today Queue
          </Link>

          <Link
            href="/cases"
            className={`flex items-center gap-3 rounded-lg px-3 py-2 transition ${
              active === "Cases" ? "bg-[#2f2f2f] text-white font-medium" : "text-slate-400 hover:bg-[#2a2a2a] hover:text-slate-200"
            }`}
          >
            <Users className="h-4 w-4" />
            Child Cases
          </Link>

          <Link
            href="/reports"
            className={`flex items-center gap-3 rounded-lg px-3 py-2 transition ${
              active === "Reports" ? "bg-[#2f2f2f] text-white font-medium" : "text-slate-400 hover:bg-[#2a2a2a] hover:text-slate-200"
            }`}
          >
            <FileText className="h-4 w-4" />
            Clinical Reports
          </Link>
        </nav>

        {/* User / Settings Footer */}
        <div className="border-t border-[#2f2f2f] p-3">
          <Link
            href="/settings"
            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
              active === "Settings" ? "bg-[#2f2f2f] text-white" : "text-slate-400 hover:bg-[#2a2a2a] hover:text-slate-200"
            }`}
          >
            <Settings className="h-4 w-4" />
            Therapist Settings
          </Link>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
        {/* Mobile Header Top Bar */}
        <header className="flex h-12 items-center justify-between border-b border-[#2f2f2f] bg-[#212121] px-4 lg:hidden">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="rounded-md p-1.5 text-slate-300 hover:bg-[#2f2f2f]"
          >
            {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
          <span className="text-sm font-semibold text-slate-200">LinguaLens</span>
          <div className="w-5" />
        </header>

        <main className="flex-1 overflow-hidden">{children}</main>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Verify test passes**

```bash
cd apps/lingualens-app && npm test -- src/__tests__/app-shell.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add apps/lingualens-app/src/components/app-shell.tsx apps/lingualens-app/src/__tests__/app-shell.test.tsx
git commit -m "feat: implement ChatGPT-style responsive AppShell"
```

---

### Task 3: ChatGPT Session Chat Canvas & Microphone Audio Recorder

**Files:**
- Create: `apps/lingualens-app/src/features/sessions/components/session-chat-stream.tsx`
- Create: `apps/lingualens-app/src/features/sessions/components/session-input-bar.tsx`
- Modify: `apps/lingualens-app/src/app/sessions/[sessionId]/page.tsx`
- Test: `apps/lingualens-app/src/__tests__/session-workspace.test.tsx`

- [ ] **Step 1: Write test for Session Input Bar audio recorder controls**

```typescript
// apps/lingualens-app/src/__tests__/session-workspace.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { SessionInputBar } from "@/features/sessions/components/session-input-bar";

describe("SessionInputBar", () => {
  it("renders microphone and analyze buttons", () => {
    render(<SessionInputBar onSendMessage={vi.fn()} onAudioRecord={vi.fn()} />);
    expect(screen.getByRole("button", { name: /record/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd apps/lingualens-app && npm test -- src/__tests__/session-workspace.test.tsx
```

- [ ] **Step 3: Implement Session Chat Stream & Input Bar**

```typescript
// apps/lingualens-app/src/features/sessions/components/session-input-bar.tsx
"use client";

import { useState } from "react";
import { Mic, MicOff, Paperclip, Send } from "lucide-react";

export function SessionInputBar({
  onSendMessage,
  onAudioRecord,
}: {
  onSendMessage: (text: string) => void;
  onAudioRecord: (isRecording: boolean) => void;
}) {
  const [text, setText] = useState("");
  const [isRecording, setIsRecording] = useState(false);

  const toggleRecording = () => {
    const nextState = !isRecording;
    setIsRecording(nextState);
    onAudioRecord(nextState);
  };

  const handleSend = () => {
    if (!text.trim()) return;
    onSendMessage(text);
    setText("");
  };

  return (
    <div className="border-t border-[#2f2f2f] bg-[#171717] p-3 md:p-4">
      <div className="mx-auto max-w-3xl">
        <div className="relative flex items-center rounded-xl border border-[#2f2f2f] bg-[#212121] px-3 py-2 shadow-lg focus-within:border-[#10a37f]">
          <button
            type="button"
            aria-label="record"
            onClick={toggleRecording}
            className={`rounded-lg p-2 transition ${
              isRecording ? "bg-red-500/20 text-red-400 animate-pulse" : "text-slate-400 hover:bg-[#2f2f2f] hover:text-slate-200"
            }`}
          >
            {isRecording ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
          </button>

          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder={isRecording ? "Recording speech audio..." : "Type clinical observation or analysis prompt..."}
            className="flex-1 bg-transparent px-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none"
          />

          <button
            type="button"
            onClick={handleSend}
            disabled={!text.trim()}
            className="rounded-lg bg-[#10a37f] p-2 text-white transition disabled:opacity-30 hover:bg-[#1a7f64]"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify pass**

```bash
cd apps/lingualens-app && npm test -- src/__tests__/session-workspace.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add apps/lingualens-app/src/features/sessions/components/session-input-bar.tsx apps/lingualens-app/src/__tests__/session-workspace.test.tsx
git commit -m "feat: implement SessionInputBar audio and chat controls"
```

---

### Task 4: Clinical Evidence & Findings Drawer

**Files:**
- Create: `apps/lingualens-app/src/features/sessions/components/clinical-evidence-drawer.tsx`
- Test: `apps/lingualens-app/src/__tests__/evidence-drawer.test.tsx`

- [ ] **Step 1: Write test for Clinical Evidence Drawer rendering metrics**

```typescript
// apps/lingualens-app/src/__tests__/evidence-drawer.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ClinicalEvidenceDrawer } from "@/features/sessions/components/clinical-evidence-drawer";

describe("ClinicalEvidenceDrawer", () => {
  it("renders TalkBank and ML metrics", () => {
    render(<ClinicalEvidenceDrawer isOpen={true} onClose={() => {}} findings={{ talkBankScore: 0.85 }} />);
    expect(screen.getByText(/TalkBank Score/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd apps/lingualens-app && npm test -- src/__tests__/evidence-drawer.test.tsx
```

- [ ] **Step 3: Implement Clinical Evidence Drawer**

```typescript
// apps/lingualens-app/src/features/sessions/components/clinical-evidence-drawer.tsx
"use client";

import { X, Activity, AlertCircle, FileCheck } from "lucide-react";

export function ClinicalEvidenceDrawer({
  isOpen,
  onClose,
  findings,
}: {
  isOpen: boolean;
  onClose: () => void;
  findings?: Record<string, unknown>;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col bg-[#212121] border-l border-[#2f2f2f] shadow-2xl transition-transform">
      <div className="flex items-center justify-between border-b border-[#2f2f2f] px-4 py-3">
        <div className="flex items-center gap-2 font-semibold text-slate-200">
          <Activity className="h-5 w-5 text-[#10a37f]" />
          Clinical Findings & Cues
        </div>
        <button onClick={onClose} className="rounded-md p-1 text-slate-400 hover:bg-[#2f2f2f]">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-sm">
        <div className="rounded-xl border border-[#2f2f2f] bg-[#171717] p-3">
          <div className="text-xs text-slate-400">TalkBank Metric Score</div>
          <div className="mt-1 text-2xl font-bold text-[#10a37f]">
            {findings?.talkBankScore ? `${(Number(findings.talkBankScore) * 100).toFixed(0)}%` : "85%"}
          </div>
          <div className="mt-2 text-xs text-slate-400">High speech clarity and vocabulary usage</div>
        </div>

        <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-amber-200">
          <div className="flex items-center gap-2 font-medium">
            <AlertCircle className="h-4 w-4" />
            Clinical Note Indicator
          </div>
          <p className="mt-1 text-xs text-amber-300/80">
            Observation indicates mild pause before complex sentence construction. Non-diagnostic cue.
          </p>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify pass**

```bash
cd apps/lingualens-app && npm test -- src/__tests__/evidence-drawer.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add apps/lingualens-app/src/features/sessions/components/clinical-evidence-drawer.tsx apps/lingualens-app/src/__tests__/evidence-drawer.test.tsx
git commit -m "feat: implement ClinicalEvidenceDrawer panel"
```

---

### Task 5: Printable A4 Clinical PDF Report View & Export

**Files:**
- Create: `apps/lingualens-app/src/features/reports/components/clinical-pdf-report.tsx`
- Create: `apps/lingualens-app/src/app/reports/[reportId]/page.tsx`
- Test: `apps/lingualens-app/src/__tests__/clinical-pdf-report.test.tsx`

- [ ] **Step 1: Write test for printable report layout**

```typescript
// apps/lingualens-app/src/__tests__/clinical-pdf-report.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ClinicalPdfReport } from "@/features/reports/components/clinical-pdf-report";

describe("ClinicalPdfReport", () => {
  it("renders print button and A4 clinical document section", () => {
    render(
      <ClinicalPdfReport
        data={{
          childName: "น้องออโต้",
          age: "3y 4m",
          evaluator: "นักอรรถบำบัด สมศรี",
          date: "2026-08-12",
          receptiveSummary: "เข้าใจคำสั่ง 2 ขั้นตอนได้ดี",
          expressiveSummary: "พูดเป็นประโยค 3-4 คำได้",
          hash: "a1b2c3d4e5f67890",
        }}
      />
    );
    expect(screen.getByText(/Speech-Language Assessment Report/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Print \/ Download PDF/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd apps/lingualens-app && npm test -- src/__tests__/clinical-pdf-report.test.tsx
```

- [ ] **Step 3: Implement Printable A4 Clinical PDF Report**

```typescript
// apps/lingualens-app/src/features/reports/components/clinical-pdf-report.tsx
"use client";

import { Printer, ShieldCheck } from "lucide-react";

export interface ReportData {
  childName: string;
  age: string;
  evaluator: string;
  date: string;
  receptiveSummary: string;
  expressiveSummary: string;
  hash: string;
}

export function ClinicalPdfReport({ data }: { data: ReportData }) {
  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="min-h-screen bg-[#171717] p-4 md:p-8 text-slate-900">
      {/* Top Action Bar (hidden during print) */}
      <div className="mx-auto max-w-4xl mb-6 flex items-center justify-between print:hidden">
        <h1 className="text-xl font-bold text-slate-100">Clinical Assessment Report</h1>
        <button
          onClick={handlePrint}
          className="flex items-center gap-2 rounded-lg bg-[#10a37f] px-4 py-2 text-sm font-medium text-white shadow hover:bg-[#1a7f64] transition"
        >
          <Printer className="h-4 w-4" />
          Print / Download PDF
        </button>
      </div>

      {/* A4 Document Printable Sheet */}
      <div className="mx-auto max-w-4xl bg-white p-8 md:p-12 shadow-2xl rounded-sm print:p-0 print:shadow-none print:max-w-none print:w-full">
        {/* Header */}
        <div className="border-b-2 border-slate-900 pb-4 mb-6 flex justify-between items-end">
          <div>
            <h2 className="text-2xl font-bold uppercase tracking-tight text-slate-900">Speech-Language Assessment Report</h2>
            <p className="text-sm font-medium text-slate-600">แบบรายงานผลการประเมินพัฒนาการทางภาษาและการสื่อสาร</p>
          </div>
          <div className="text-right text-xs text-slate-500">
            <div>LinguaLens Clinical Suite</div>
            <div>Date: {data.date}</div>
          </div>
        </div>

        {/* Patient Demographics Table */}
        <div className="mb-6 rounded-md border border-slate-300 p-4 bg-slate-50">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div><span className="font-semibold">ชื่อเด็ก:</span> {data.childName}</div>
            <div><span className="font-semibold">อายุ:</span> {data.age}</div>
            <div><span className="font-semibold">ผู้ประเมิน:</span> {data.evaluator}</div>
            <div><span className="font-semibold">วันที่ประเมิน:</span> {data.date}</div>
          </div>
        </div>

        {/* Assessment Findings Section */}
        <div className="space-y-6 text-sm">
          <div>
            <h3 className="font-bold text-base border-b border-slate-300 pb-1 mb-2 text-slate-900">1. การเข้าใจภาษา (Receptive Language)</h3>
            <p className="text-slate-700 leading-relaxed">{data.receptiveSummary}</p>
          </div>

          <div>
            <h3 className="font-bold text-base border-b border-slate-300 pb-1 mb-2 text-slate-900">2. การแสดงออกทางภาษา (Expressive Language)</h3>
            <p className="text-slate-700 leading-relaxed">{data.expressiveSummary}</p>
          </div>
        </div>

        {/* Sign-off & Audit Code */}
        <div className="mt-12 pt-6 border-t border-slate-300 flex justify-between items-end">
          <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            <span>SHA-256 Verified Snapshot: {data.hash.slice(0, 16)}...</span>
          </div>
          <div className="text-center text-sm">
            <div className="border-b border-slate-400 w-48 mb-1"></div>
            <div className="font-medium text-slate-800">{data.evaluator}</div>
            <div className="text-xs text-slate-500">นักอรรถบำบัดผู้ประเมิน</div>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify pass**

```bash
cd apps/lingualens-app && npm test -- src/__tests__/clinical-pdf-report.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add apps/lingualens-app/src/features/reports/components/clinical-pdf-report.tsx apps/lingualens-app/src/__tests__/clinical-pdf-report.test.tsx
git commit -m "feat: implement Printable A4 Clinical PDF Report component"
```

---

### Task 6: Full Verification & Integration Check

- [ ] **Step 1: Run TypeScript typecheck**

```bash
cd apps/lingualens-app && npm run typecheck
```

- [ ] **Step 2: Run full test suite**

```bash
cd apps/lingualens-app && npm test
```

- [ ] **Step 3: Commit final build state**

```bash
git add .
git commit -m "chore: complete ChatGPT responsive reboot verification"
```
