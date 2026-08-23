import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createInitialWorkflowState,
  acknowledgeSessionCues,
  buildBasicChatExport,
  evaluateTranscriptQa,
  extractLanguageSampleFeatures,
  generateBackendMlDecisionSupport,
  getBackendMlDecisionSupport,
  getBackendMlReadiness,
  loadWorkflowState,
  parseChaTranscript,
  saveWorkflowState,
  serializeTranscriptLines,
  updateProfileEvidenceReview,
  createBackendCase,
  updateBackendCase,
  withdrawBackendCaseConsent
} from "@/lib/workflow";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

beforeEach(() => {
  window.sessionStorage.clear();
  window.localStorage.clear();
});

describe("simplified transcript intake", () => {
  it("migrates legacy title-cased report statuses to the lowercase persisted domain", () => {
    window.sessionStorage.setItem("lingualens.therapist.workflow.v1", JSON.stringify({
      ...createInitialWorkflowState(),
      analysisStatus: "completed",
      reportStatus: "Draft",
      reportMarkdown: "# Existing draft",
    }));

    expect(loadWorkflowState()).toEqual(expect.objectContaining({
      analysisStatus: "completed",
      reportStatus: "draft",
      reportMarkdown: "# Existing draft",
    }));
  });

  it("persists stale findings and report provenance across reload", () => {
    const staleState = saveWorkflowState({
      ...createInitialWorkflowState(),
      analysisStatus: "stale",
      reportStatus: "stale",
      backendTranscriptId: "transcript-v2",
      backendReportId: "report-v1",
      reportId: "report-v1",
      reportMarkdown: "# Stale draft retained for provenance",
    });

    expect(loadWorkflowState()).toEqual(expect.objectContaining({
      analysisStatus: "stale",
      reportStatus: "stale",
      backendTranscriptId: "transcript-v2",
      backendReportId: "report-v1",
      reportMarkdown: staleState.reportMarkdown,
    }));
  });

  it("persists recording metadata but clears unsaved audio state on refresh", () => {
    saveWorkflowState({
      ...createInitialWorkflowState(),
      recordingStatus: "stopped",
      recordingSeconds: 12,
      audioMimeType: "audio/webm",
      recordingCreatedAt: "2026-06-19T08:00:00.000Z",
      hasUnsavedRecording: true
    });

    const stored = window.sessionStorage.getItem("lingualens.therapist.workflow.v1") ?? "";
    expect(stored).toContain('"audioMimeType":"audio/webm"');
    expect(stored).not.toContain("blob:");
    expect(loadWorkflowState()).toEqual(expect.objectContaining({
      recordingStatus: "idle",
      recordingSeconds: 12,
      audioMimeType: "audio/webm",
      hasUnsavedRecording: false,
      recordingClearedForPrivacy: true
    }));
  });

  it("joins CHAT continuation text to the preceding speaker line", () => {
    const parsed = parseChaTranscript([
      "@Begin",
      "@Participants:\tCHI Child Target_Child",
      "*CHI:\tI want the",
      "\tblue car. \u0015100_900\u0015",
      "@End"
    ].join("\n"));

    expect(parsed.transcriptLines).toEqual([
      expect.objectContaining({
        speaker: "CHI",
        text: "I want the blue car.",
        startMs: 100,
        endMs: 900
      })
    ]);
  });

  it("parses CHAT metadata, preserves configured speaker codes and timestamps, and warns for unsupported tiers", () => {
    const parsed = parseChaTranscript([
      "@UTF8",
      "@Begin",
      "@Languages:\teng, tha",
      "@Participants:\tCHI Child Target_Child, INV Investigator Investigator, GRM Grandmother Adult",
      "@ID:\teng|Demo|CHI|4;00.00|female|||Target_Child|||",
      "@ID:\teng|Demo|INV|||||Investigator|||",
      "@ID:\teng|Demo|GRM|||||Grandmother|||",
      "@Media:\tsession_audio, audio",
      "*INV:\tTell me more. \u0015100_900\u0015",
      "%mor:\tpro:sub|I v|tell",
      "*GRM:\tShe likes the blue car. \u0015950_1600\u0015",
      "@End"
    ].join("\n"));

    expect(parsed.metadata).toEqual(expect.objectContaining({
      languages: ["eng", "tha"],
      media: { name: "session_audio", type: "audio" },
      participants: expect.arrayContaining([
        expect.objectContaining({ code: "GRM", name: "Grandmother", role: "Adult" })
      ]),
      ids: expect.arrayContaining([
        expect.objectContaining({ code: "CHI", raw: "eng|Demo|CHI|4;00.00|female|||Target_Child|||" })
      ])
    }));
    expect(parsed.transcriptLines).toEqual([
      expect.objectContaining({ speaker: "INV", startMs: 100, endMs: 900 }),
      expect.objectContaining({ speaker: "GRM", startMs: 950, endMs: 1600 })
    ]);
    expect(parsed.warnings).toContain("Unsupported dependent tier %mor was not imported.");
    expect(parsed.validationIssues).toEqual([]);
  });

  it("reports missing participants, empty utterances, unknown speakers, and malformed lines", () => {
    const parsed = parseChaTranscript([
      "@Begin",
      "@Languages:\teng",
      "*CHI:\t",
      "*GRM:\tHello.",
      "not a CHAT tier",
      "@End"
    ].join("\n"));

    expect(parsed.validationIssues).toEqual(expect.arrayContaining([
      "Missing @Participants header.",
      "Line 3 has an empty utterance.",
      "Speaker GRM is not declared in @Participants.",
      "Line 5 is malformed and was not imported."
    ]));
  });

  it("serializes edited lines while preserving timestamps and unclear review markers", () => {
    const transcript = serializeTranscriptLines([
      { lineId: "line-1", speaker: "THER", text: "What do you see?", startMs: 100, endMs: 900 },
      { lineId: "line-2", speaker: "CHI", text: "Blue car.", startMs: 950, endMs: 1600, unclear: true }
    ]);

    expect(transcript).toContain("*THER:\tWhat do you see? \u0015100_900\u0015");
    expect(transcript).toContain("*CHI:\tBlue car. [unclear] \u0015950_1600\u0015");
  });

  it("exports reviewed lines as basic CHAT with metadata, IDs, media, and preserved speaker codes", () => {
    const chat = buildBasicChatExport({
      lines: [
        { lineId: "line-1", speaker: "INV", text: "What do you see?", startMs: 100, endMs: 900 },
        { lineId: "line-2", speaker: "GRM", text: "A blue car.", startMs: 950, endMs: 1600 }
      ],
      metadata: {
        languages: ["eng"],
        participants: [
          { code: "INV", name: "Investigator", role: "Investigator" },
          { code: "GRM", name: "Grandmother", role: "Adult" }
        ],
        ids: [
          { code: "INV", raw: "eng|Demo|INV|||||Investigator|||" }
        ],
        media: { name: "session_audio", type: "audio" },
        headers: {}
      },
      includeMedia: true,
      fallbackMediaName: "local-session_audio"
    });

    expect(chat).toContain("@Begin");
    expect(chat).toContain("@Languages:\teng");
    expect(chat).toContain("@Participants:\tINV Investigator Investigator, GRM Grandmother Adult");
    expect(chat).toContain("@ID:\teng|Demo|INV|||||Investigator|||");
    expect(chat).toContain("@ID:\teng|TherapistAppV2|GRM|||||Adult|||");
    expect(chat).toContain("@Media:\tsession_audio, audio");
    expect(chat).toContain("*GRM:\tA blue car. \u0015950_1600\u0015");
    expect(chat).toMatch(/@End\n$/);
  });

  it("blocks failed QA and permits therapist review of warning-level QA", () => {
    expect(evaluateTranscriptQa([
      { lineId: "line-1", speaker: "THER", text: "Hello." }
    ])).toEqual(expect.objectContaining({
      status: "fail",
      issues: expect.arrayContaining(["No child speaker lines are marked CHI."])
    }));

    expect(evaluateTranscriptQa([
      { lineId: "line-1", speaker: "THER", text: "Hello." },
      { lineId: "line-2", speaker: "CHI", text: "Hi." }
    ])).toEqual(expect.objectContaining({
      status: "warning",
      issues: expect.arrayContaining(["Child sample has fewer than 3 utterances."])
    }));
  });

  it("extracts reviewed language-sample features from child and adult transcript lines", () => {
    const result = extractLanguageSampleFeatures([
      { lineId: "line-1", speaker: "THER", text: "Do you want juice?" },
      { lineId: "line-2", speaker: "CHI", text: "Do you want juice?" },
      { lineId: "line-3", speaker: "CHI", text: "I want juice juice." },
      { lineId: "line-4", speaker: "CHI", text: "You am ready?", unclear: true },
      { lineId: "line-5", speaker: "UNK", text: "xxx" }
    ], {
      languages: ["eng"],
      participants: [
        { code: "THER", name: "Therapist", role: "Investigator" },
        { code: "CHI", name: "Child", role: "Target_Child" }
      ],
      ids: [],
      headers: {}
    });

    expect(result).toEqual({
      totalUtterances: 5,
      childUtterances: 3,
      adultUtterances: 1,
      totalWords: 11,
      mluWords: 3.6667,
      ndw: 7,
      ttr: 0.6364,
      questionRatio: 0.6667,
      unclearRatio: 0.4,
      repetitionCue: 1,
      echolaliaCue: 1,
      pronounReversalCue: 1
    });
  });

  describe("CHAT parser edge cases", () => {
    it("handles missing @Participants header", () => {
      const parsed = parseChaTranscript([
        "@Begin",
        "@Languages:\teng",
        "*CHI:\tI see it.",
        "@End"
      ].join("\n"));
      expect(parsed.validationIssues).toContain("Missing @Participants header.");
    });

    it("handles unsupported dependent tiers", () => {
      const parsed = parseChaTranscript([
        "@Begin",
        "@Languages:\teng",
        "@Participants:\tCHI Child Target_Child",
        "*CHI:\tI see it.",
        "%gla:\tpro:sub|I v|see pro:obj|it",
        "@End"
      ].join("\n"));
      expect(parsed.warnings).toContain("Unsupported dependent tier %gla was not imported.");
    });

    it("handles malformed speaker lines", () => {
      const parsed = parseChaTranscript([
        "@Begin",
        "@Languages:\teng",
        "@Participants:\tCHI Child Target_Child",
        "*CHI hello.",
        "@End"
      ].join("\n"));
      expect(parsed.validationIssues).toContain("Line 4 is malformed and was not imported.");
    });

    it("handles multiline utterance continuation", () => {
      const parsed = parseChaTranscript([
        "@Begin",
        "@Languages:\teng",
        "@Participants:\tCHI Child Target_Child",
        "*CHI:\tI want the",
        "\tred car.",
        "@End"
      ].join("\n"));
      expect(parsed.transcriptLines[0].text).toBe("I want the red car.");
    });

    it("handles timestamped speaker lines", () => {
      const parsed = parseChaTranscript([
        "@Begin",
        "@Languages:\teng",
        "@Participants:\tCHI Child Target_Child",
        "*CHI:\tI want it. \u00151500_3000\u0015",
        "@End"
      ].join("\n"));
      expect(parsed.transcriptLines[0]).toEqual(expect.objectContaining({
        speaker: "CHI",
        text: "I want it.",
        startMs: 1500,
        endMs: 3000
      }));
    });

    it("handles unknown speaker not in @Participants", () => {
      const parsed = parseChaTranscript([
        "@Begin",
        "@Languages:\teng",
        "@Participants:\tCHI Child Target_Child",
        "*MOT:\tHello.",
        "@End"
      ].join("\n"));
      expect(parsed.validationIssues).toContain("Speaker MOT is not declared in @Participants.");
    });

    it("handles empty utterances", () => {
      const parsed = parseChaTranscript([
        "@Begin",
        "@Languages:\teng",
        "@Participants:\tCHI Child Target_Child",
        "*CHI:\t",
        "@End"
      ].join("\n"));
      expect(parsed.validationIssues).toContain("Line 4 has an empty utterance.");
    });
  });

  describe("backend ML API paths", () => {
    it("uses API paths without a duplicated /v1 prefix", async () => {
      const requestedUrls: string[] = [];
      const mlResponse = {
        result_id: "MLR-1",
        status: "completed",
        provider_name: "ReferenceEvidenceProvider",
        provider_version: "0.9.0",
        input_feature_schema_version: "features-basic-v0.7",
        generated_at: "2026-06-20T00:00:00Z",
        cues: [],
        pattern_evidence: {
          status: "not_available",
          availability: {
            state: "system_unavailable",
            reason_code: "gate1_research_only",
            message: "Additional pattern evidence remains research-only.",
            workflow_can_continue: true,
            next_step: "Continue transcript and feature review."
          },
          associated_features: [],
          review_state: { status: "unreviewed", therapist_note: "" }
        },
        profile_evidence: []
      };

      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        requestedUrls.push(url);

        if (url.includes("/ml-readiness")) {
          return Response.json({
            ready: true,
            provider_id: "reference_evidence_review",
            reason_codes: [],
            reasons: []
          });
        }

        return Response.json(mlResponse);
      }));

      await generateBackendMlDecisionSupport("TRANSCRIPT-ML");
      await getBackendMlDecisionSupport("SESSION-ML");
      await updateProfileEvidenceReview("MLR-1", "TD", "reviewed", "Checked");
      await getBackendMlReadiness("TRANSCRIPT-ML");

      const mlUrls = requestedUrls.filter((url) => url.includes("/ml-review") || url.includes("/ml-readiness") || url.includes("/review-state"));

      expect(mlUrls).toContain("http://localhost:8000/api/v1/transcripts/TRANSCRIPT-ML/ml-review");
      expect(mlUrls).toContain("http://localhost:8000/api/v1/sessions/SESSION-ML/ml-review");
      expect(mlUrls).toContain("http://localhost:8000/api/v1/ml-results/MLR-1/profiles/TD/review-state");
      expect(mlUrls).toContain("http://localhost:8000/api/v1/transcripts/TRANSCRIPT-ML/ml-readiness?provider_id=reference_evidence_review");
      expect(mlUrls.length).toBeGreaterThanOrEqual(4);
      expect(mlUrls.every((url) => !url.includes("/api/v1/v1/"))).toBe(true);
    });

    it("records the cues acknowledgement against the session endpoint", async () => {
      const requestedUrls: string[] = [];
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        requestedUrls.push(url);
        return Response.json({
          session_id: "SESSION-ACK",
          acknowledged: true,
          acknowledged_at: "2026-07-17T00:00:00Z",
          acknowledged_by: "therapist-demo",
        });
      }));

      const acknowledgement = await acknowledgeSessionCues("SESSION-ACK");

      expect(requestedUrls).toContain("http://localhost:8000/api/v1/sessions/SESSION-ACK/acknowledge-cues");
      expect(acknowledgement).toEqual({
        sessionId: "SESSION-ACK",
        acknowledged: true,
        acknowledgedAt: "2026-07-17T00:00:00Z",
        acknowledgedBy: "therapist-demo",
      });
    });

    it("falls back to the default API base when NEXT_PUBLIC_API_BASE_URL is blank", async () => {
      const originalEnv = process.env.NEXT_PUBLIC_API_BASE_URL;
      process.env.NEXT_PUBLIC_API_BASE_URL = "";

      vi.resetModules();
      const { generateBackendMlDecisionSupport: generateWithBlankBase } = await import("@/lib/workflow");

      const requestedUrls: string[] = [];
      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
        requestedUrls.push(String(input));
        return Response.json({
          result_id: "MLR-1",
          status: "completed",
          provider_name: "ReferenceEvidenceProvider",
          provider_version: "0.9.0",
          input_feature_schema_version: "features-basic-v0.7",
          generated_at: "2026-06-20T00:00:00Z",
          cues: [],
          profile_evidence: []
        });
      }));

      try {
        await generateWithBlankBase("TRANSCRIPT-ML");
        expect(requestedUrls[0]).toBe("http://localhost:8000/api/v1/transcripts/TRANSCRIPT-ML/ml-review");
      } finally {
        process.env.NEXT_PUBLIC_API_BASE_URL = originalEnv;
        vi.resetModules();
      }
    });
  });

  describe("backend case consent management paths", () => {
    it("calls POST /cases with JSON body when creating a case", async () => {
      let requestedUrl = "";
      let requestedMethod = "";
      let requestedBody = "";

      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        requestedUrl = String(input);
        requestedMethod = init?.method ?? "GET";
        requestedBody = String(init?.body ?? "");
        return Response.json({
          case_id: "CASE-001",
          nickname: "Ethan"
        });
      }));

      const payload = { nickname: "Ethan" };
      const result = await createBackendCase(payload);

      expect(requestedUrl).toBe("http://localhost:8000/api/v1/cases");
      expect(requestedMethod).toBe("POST");
      expect(JSON.parse(requestedBody)).toEqual(payload);
      expect(result).toEqual({ case_id: "CASE-001", nickname: "Ethan" });
    });

    it("calls PATCH /cases/{caseId} with JSON body when updating a case", async () => {
      let requestedUrl = "";
      let requestedMethod = "";
      let requestedBody = "";

      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        requestedUrl = String(input);
        requestedMethod = init?.method ?? "GET";
        requestedBody = String(init?.body ?? "");
        return Response.json({
          case_id: "CASE-001",
          nickname: "Ethan Updated"
        });
      }));

      const payload = { nickname: "Ethan Updated" };
      const result = await updateBackendCase("CASE-001", payload);

      expect(requestedUrl).toBe("http://localhost:8000/api/v1/cases/CASE-001");
      expect(requestedMethod).toBe("PATCH");
      expect(JSON.parse(requestedBody)).toEqual(payload);
      expect(result).toEqual({ case_id: "CASE-001", nickname: "Ethan Updated" });
    });

    it("calls POST /cases/{caseId}/withdraw-consent with JSON body when withdrawing consent", async () => {
      let requestedUrl = "";
      let requestedMethod = "";
      let requestedBody = "";

      vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        requestedUrl = String(input);
        requestedMethod = init?.method ?? "GET";
        requestedBody = String(init?.body ?? "");
        return Response.json({
          status: "success",
          message: "Consent withdrawn successfully."
        });
      }));

      const result = await withdrawBackendCaseConsent("CASE-001", "Request by parent", true);

      expect(requestedUrl).toBe("http://localhost:8000/api/v1/cases/CASE-001/withdraw-consent");
      expect(requestedMethod).toBe("POST");
      expect(JSON.parse(requestedBody)).toEqual({
        reason: "Request by parent",
        redact_notes: true
      });
      expect(result).toEqual({
        status: "success",
        message: "Consent withdrawn successfully."
      });
    });
  });
});
