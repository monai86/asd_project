import { expect, expectTypeOf, test } from "vitest";

import { confirmed, failedWithPrevious, stale } from "@/services/adapters/remote-state";
import type { AvailableDataMode, RemoteState } from "@/services/adapters/remote-state";

test("preserves only confirmed data when a refresh fails", () => {
  expect(failedWithPrevious(new Error("offline"), [{ id: "case-1" }])).toMatchObject({
    status: "error",
    mode: "backend",
    previous: [{ id: "case-1" }],
  });
});

test("records the cause of downstream staleness", () => {
  expect(stale({ reportId: "report-1" }, "transcript-edited", "sample")).toMatchObject({
    status: "stale",
    mode: "sample",
    invalidatedBy: "transcript-edited",
  });
});

test("uses a fixed safe error message and preserves the available data mode", () => {
  expect(failedWithPrevious(
    { message: "raw child transcript and storage key" },
    { draftId: "draft-1" },
    "local-draft",
  )).toEqual({
    status: "error",
    mode: "local-draft",
    message: "Request failed",
    previous: { draftId: "draft-1" },
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

test("restricts data-bearing remote states to available modes", () => {
  expectTypeOf<Extract<RemoteState<unknown>, { status: "success" }>["mode"]>()
    .toEqualTypeOf<AvailableDataMode>();
  expectTypeOf<Extract<RemoteState<unknown>, { status: "loading" }>["mode"]>()
    .toEqualTypeOf<AvailableDataMode>();
  expectTypeOf<Extract<RemoteState<unknown>, { status: "stale" }>["mode"]>()
    .toEqualTypeOf<AvailableDataMode>();

  // @ts-expect-error unavailable mode cannot carry confirmed data
  confirmed({ id: "case-1" }, "unavailable");
});
