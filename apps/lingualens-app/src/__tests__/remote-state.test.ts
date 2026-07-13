import { expect, test } from "vitest";

import { confirmed, failedWithPrevious, stale } from "@/services/adapters/remote-state";

test("preserves only confirmed data when a refresh fails", () => {
  expect(failedWithPrevious(new Error("offline"), [{ id: "case-1" }])).toMatchObject({
    status: "error",
    mode: "backend",
    previous: [{ id: "case-1" }],
  });
});

test("records the cause of downstream staleness", () => {
  expect(stale({ reportId: "report-1" }, "transcript-edited")).toMatchObject({
    status: "stale",
    invalidatedBy: "transcript-edited",
  });
});

test("distinguishes an empty confirmed collection from successful data", () => {
  expect(confirmed([])).toEqual({ status: "empty", mode: "backend" });
  expect(confirmed([{ id: "case-1" }], "sample")).toEqual({
    status: "success",
    mode: "sample",
    data: [{ id: "case-1" }],
  });
});
