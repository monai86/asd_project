import { describe, expect, it } from "vitest";

import { safeMutationResponseBreadcrumb } from "../../e2e/support/mutation-response-breadcrumb";

describe("safeMutationResponseBreadcrumb", () => {
  it("keeps only method, status, and a normalized workflow route", () => {
    expect(safeMutationResponseBreadcrumb(
      "POST",
      "http://127.0.0.1:8000/api/v1/sessions/session-secret/transcripts/manual?case_id=case-secret",
      201,
    )).toEqual({
      method: "POST",
      route: "/api/v1/sessions/:session_id/transcripts/manual",
      status: 201,
    });
  });

  it("ignores reads and unrelated mutations", () => {
    expect(safeMutationResponseBreadcrumb(
      "GET",
      "http://127.0.0.1:8000/api/v1/transcripts/transcript-secret",
      200,
    )).toBeNull();
    expect(safeMutationResponseBreadcrumb(
      "POST",
      "http://127.0.0.1:8000/api/v1/reports/report-secret",
      200,
    )).toBeNull();
    expect(safeMutationResponseBreadcrumb(
      "POST",
      "http://127.0.0.1:8000/api/v1/sessions/session-secret/reports/report-secret",
      200,
    )).toBeNull();
  });

  it("normalizes case, session, and transcript identifiers", () => {
    expect(safeMutationResponseBreadcrumb(
      "POST",
      "http://127.0.0.1:8000/api/v1/cases/case-secret/sessions",
      200,
    )?.route).toBe("/api/v1/cases/:case_id/sessions");
    expect(safeMutationResponseBreadcrumb(
      "PATCH",
      "http://127.0.0.1:8000/api/v1/transcripts/transcript-secret",
      200,
    )?.route).toBe("/api/v1/transcripts/:transcript_id");
  });
});
