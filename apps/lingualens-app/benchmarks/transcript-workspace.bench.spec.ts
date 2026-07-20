import { expect, test } from "@playwright/test";
import { cpus, freemem, platform, release, totalmem } from "node:os";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

import { makeTranscriptText } from "./fixtures/transcript-lines";

const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT ?? "8000";
const backendBaseUrl = `http://127.0.0.1:${backendPort}/api/v1`;
const sampleSizes = [100, 500, 1_000] as const;
const repetitions = 5;
const resultPath = path.resolve(process.cwd(), "benchmarks/results/transcript-benchmark-latest.json");

type RunMetrics = {
  readyMs: number;
  keystrokeMs: number;
  selectionMs: number;
  filterMs: number;
  scrollFps: number;
  heapBytes: number | null;
};

type Summary = Record<Exclude<keyof RunMetrics, "heapBytes">, { median: number; p95: number }> & {
  heapBytes: { median: number; p95: number } | null;
};

test.describe.configure({ mode: "serial" });

test("transcript editor stays responsive at 100, 500, and 1,000 lines", async ({ page, request, browser }) => {
  test.setTimeout(10 * 60_000);
  await page.addInitScript(() => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "therapist",
      organizationId: "pilot_org_001",
      aal: "aal2",
    }));
  });

  const results: Array<{ lineCount: number; runs: RunMetrics[]; summary: Summary }> = [];
  const authHeaders = {
    "X-Mock-Role": "therapist",
    "X-Mock-User-Id": "therapist-demo",
    "X-Organization-Id": "pilot_org_001",
  };

  for (const lineCount of sampleSizes) {
    const caseResponse = await request.post(`${backendBaseUrl}/cases`, {
      headers: authHeaders,
      data: {
        child_code: `C-BENCH-${lineCount}`,
        age_months: 60,
        language: "English",
        consent_status: "granted",
      },
    });
    expect(caseResponse.ok(), await caseResponse.text()).toBe(true);
    const caseId = (await caseResponse.json()).case_id as string;
    const sessionResponse = await request.post(`${backendBaseUrl}/cases/${caseId}/sessions`, {
      headers: authHeaders,
      data: { session_date: "2026-07-17", session_type: "language_sample" },
    });
    expect(sessionResponse.ok(), await sessionResponse.text()).toBe(true);
    const sessionId = (await sessionResponse.json()).session_id as string;
    const transcriptResponse = await request.post(`${backendBaseUrl}/sessions/${sessionId}/transcripts/manual`, {
      headers: authHeaders,
      data: {
        text: makeTranscriptText(lineCount),
        language: "English",
      },
    });
    expect(transcriptResponse.ok(), await transcriptResponse.text()).toBe(true);
    if (page.url() !== "about:blank") {
      await page.evaluate(() => {
        window.localStorage.clear();
        window.sessionStorage.removeItem("lingualens.therapist.workflow.v1");
      });
    }

    const runs: RunMetrics[] = [];
    for (let repetition = 0; repetition < repetitions; repetition += 1) {
      const navigationStart = performance.now();
      await page.goto(`/sessions/${sessionId}?view=transcript`, { waitUntil: "domcontentloaded" });
      const listbox = page.getByRole("listbox", { name: "Transcript lines" });
      await expect(listbox).toBeVisible();
      const transcriptRows = listbox.locator("article[role='option']");
      await expect(transcriptRows).toHaveCount(lineCount);
      const readyMs = performance.now() - navigationStart;

      const firstInput = page.getByLabel("Utterance text 1", { exact: true });
      const keystrokeMs = await firstInput.evaluate(async (element) => {
        const input = element as HTMLTextAreaElement;
        const started = performance.now();
        const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set;
        setter?.call(input, `${input.value} x`);
        input.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: "x" }));
        await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
        return performance.now() - started;
      });

      const secondLine = transcriptRows.nth(1);
      const selectionMs = await secondLine.evaluate(async (element) => {
        const started = performance.now();
        (element as HTMLElement).click();
        await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
        return performance.now() - started;
      });
      await expect(secondLine).toHaveAttribute("aria-selected", "true");

      const missingSpeakerFilter = page.getByRole("button", { name: /Missing Speaker/ });
      const filterMs = await missingSpeakerFilter.evaluate(async (element) => {
        const started = performance.now();
        (element as HTMLElement).click();
        await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
        return performance.now() - started;
      });
      await expect(page.getByText("No lines match the current review filter.")).toBeVisible();
      await page.getByRole("button", { name: /^All/ }).click();
      await expect(transcriptRows).toHaveCount(lineCount);

      const scrollFps = await page.evaluate(async () => {
        window.scrollTo(0, 0);
        let frames = 0;
        const started = performance.now();
        await new Promise<void>((resolve) => {
          const sample = (now: number) => {
            frames += 1;
            window.scrollBy(0, 48);
            if (now - started >= 600) resolve();
            else requestAnimationFrame(sample);
          };
          requestAnimationFrame(sample);
        });
        return frames / ((performance.now() - started) / 1_000);
      });

      const heapBytes = await page.evaluate(() => {
        const memory = (performance as Performance & { memory?: { usedJSHeapSize: number } }).memory;
        return memory?.usedJSHeapSize ?? null;
      });

      runs.push({ readyMs, keystrokeMs, selectionMs, filterMs, scrollFps, heapBytes });
    }

    const summary = summarize(runs);
    results.push({ lineCount, runs, summary });

  }

  mkdirSync(path.dirname(resultPath), { recursive: true });
  writeFileSync(resultPath, `${JSON.stringify({
    capturedAt: new Date().toISOString(),
    conditions: {
      browser: browser.browserType().name(),
      browserVersion: browser.version(),
      headless: true,
      repetitions,
      navigation: "cold page navigation with warm local production server; interaction samples after ready",
      viewport: await page.viewportSize(),
      platform: `${platform()} ${release()}`,
      cpu: cpus()[0]?.model ?? "unknown",
      logicalCpuCount: cpus().length,
      totalMemoryBytes: totalmem(),
      freeMemoryBytesAtCapture: freemem(),
    },
    budgets: {
      line500: { keystrokeP95Ms: 50, minimumScrollFps: 50 },
      line1000: { keystrokeP95Ms: 100, minimumScrollFps: 45 },
    },
    results,
  }, null, 2)}\n`);

  const result500 = results.find((result) => result.lineCount === 500)!;
  const result1000 = results.find((result) => result.lineCount === 1_000)!;
  expect(result500.summary.keystrokeMs.p95, "500-line keystroke p95 must stay at or below 50 ms").toBeLessThanOrEqual(50);
  expect(Math.min(...result500.runs.map((run) => run.scrollFps)), "500-line scroll must stay at or above 50 fps").toBeGreaterThanOrEqual(50);
  expect(result1000.summary.keystrokeMs.p95, "1,000-line keystroke p95 must stay at or below 100 ms").toBeLessThanOrEqual(100);
  expect(Math.min(...result1000.runs.map((run) => run.scrollFps)), "1,000-line scroll must stay at or above 45 fps").toBeGreaterThanOrEqual(45);
});

function summarize(runs: RunMetrics[]): Summary {
  return {
    readyMs: distribution(runs.map((run) => run.readyMs)),
    keystrokeMs: distribution(runs.map((run) => run.keystrokeMs)),
    selectionMs: distribution(runs.map((run) => run.selectionMs)),
    filterMs: distribution(runs.map((run) => run.filterMs)),
    scrollFps: distribution(runs.map((run) => run.scrollFps)),
    heapBytes: runs.every((run) => run.heapBytes === null)
      ? null
      : distribution(runs.flatMap((run) => run.heapBytes === null ? [] : [run.heapBytes])),
  };
}

function distribution(values: number[]) {
  const sorted = [...values].sort((left, right) => left - right);
  return {
    median: round(percentile(sorted, 0.5)),
    p95: round(percentile(sorted, 0.95)),
  };
}

function percentile(sortedValues: number[], percentileValue: number) {
  const index = Math.min(sortedValues.length - 1, Math.max(0, Math.ceil(sortedValues.length * percentileValue) - 1));
  return sortedValues[index] ?? 0;
}

function round(value: number) {
  return Math.round(value * 100) / 100;
}
