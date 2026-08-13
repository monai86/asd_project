import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const presentationalViews = [
  "src/features/sessions/intake/session-intake-view.tsx",
  "src/features/sessions/report/session-report-view.tsx",
];

const complexFeatureFiles = [
  "src/features/sessions/findings/session-findings-view.tsx",
  "src/features/settings/components/settings-workspace.tsx",
  "src/components/transcript-editor-panel.tsx",
];

describe("Session presentational boundaries", () => {
  it.each(presentationalViews)("keeps backend transport imports out of %s", (relativePath) => {
    const source = readFileSync(resolve(process.cwd(), relativePath), "utf8");

    expect(source).not.toMatch(/from ["']@\/lib\/api["']/);
    expect(source).not.toMatch(/(?<!\.)\b(?:apiRequest|apiGet|apiBlob|getBackend\w+|updateBackend\w+|generateBackend\w+|finalizeBackend\w+|exportBackend\w+|exportReviewed\w+)\s*\(/);
  });

  it.each(complexFeatureFiles)("keeps %s within the documented 500-line container budget", (relativePath) => {
    const source = readFileSync(resolve(process.cwd(), relativePath), "utf8");
    const lineCount = source.trimEnd().split("\n").length;

    expect(lineCount).toBeLessThanOrEqual(500);
  });
});
