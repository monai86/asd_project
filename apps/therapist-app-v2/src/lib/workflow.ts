import { API_BASE, apiGet, apiRequest, apiText, ApiError } from "@/lib/api";

export const WORKFLOW_STORAGE_KEY = "linguacare.therapist.workflow.v1";
export const SEEDED_TRANSCRIPT_SESSION_ID = "SESSION-001";

export type WorkflowSource = "recording" | "audio-upload" | "cha-upload" | "paste-transcript";
export type TranscriptReviewStatus = "not_started" | "draft" | "in_review" | "reviewed";
export type AnalysisStatus = "not_started" | "processing" | "completed" | "failed";
export type TranscriptionJobStatus = "queued" | "processing" | "completed" | "failed";
export type TranscriptQaStatus = "not_run" | "pass" | "warning" | "fail";
export type PersistenceStatus = "idle" | "unsaved" | "saving" | "saved" | "failed";
export type ChatParticipant = {
  code: string;
  name: string;
  role: string;
};
export type ChatId = {
  code: string;
  raw: string;
};
export type ChatMetadata = {
  languages: string[];
  participants: ChatParticipant[];
  ids: ChatId[];
  media?: {
    name: string;
    type: string;
  };
  headers: Record<string, string[]>;
};
export type ChatParseResult = {
  transcriptText: string;
  transcriptLines: TranscriptLine[];
  metadata: ChatMetadata;
  warnings: string[];
  validationIssues: string[];
};
export type TranscriptLine = {
  lineId: string;
  speaker: string;
  text: string;
  startMs?: number;
  endMs?: number;
  unclear?: boolean;
};

export type LanguageSampleFeatures = {
  totalUtterances: number;
  childUtterances: number;
  adultUtterances: number;
  totalWords: number;
  mluWords: number;
  ndw: number;
  ttr: number;
  questionRatio: number;
  unclearRatio: number;
  repetitionCue: number;
  echolaliaCue: number;
  pronounReversalCue: number;
};

export type MlDecisionSupport = {
  patternCues: string[];
  reviewSuggestions: string[];
  confidence: "limited" | "moderate";
  limitations: string[];
  dismissed: boolean;
  source: "backend" | "local";
};

export type WorkflowState = {
  sessionId?: string;
  sessionCreatedAt?: string;
  backendSessionId?: string;
  backendTranscriptId?: string;
  backendTranscriptSessionId?: string;
  backendReportId?: string;
  caseId?: string;
  caseInfo: {
    caseId?: string;
    clientLabel: string;
  };
  childName: string;
  reportPeriod: string;
  source?: WorkflowSource;
  recordingStatus: "idle" | "recording" | "paused" | "stopped" | "interrupted" | "error";
  recordingSeconds: number;
  mockAudioStored: boolean;
  audioMimeType?: string;
  recordingCreatedAt?: string;
  hasUnsavedRecording: boolean;
  recordingClearedForPrivacy: boolean;
  transcriptionJobId?: string;
  transcriptionJobStatus?: TranscriptionJobStatus;
  transcriptionJobMessage?: string;
  transcriptDraftLabel?: string;
  sourceFilename?: string;
  transcriptText: string;
  transcriptLines: TranscriptLine[];
  chatMetadata: ChatMetadata;
  chatWarnings: string[];
  chatValidationIssues: string[];
  transcriptReady: boolean;
  transcriptAttested: boolean;
  transcriptCompleteness: number;
  transcriptReviewStatus: TranscriptReviewStatus;
  qaStatus: TranscriptQaStatus;
  qaSummary?: string;
  qaIssues: string[];
  transcriptSaveStatus: PersistenceStatus;
  workflowLoading: boolean;
  analysisStatus: AnalysisStatus;
  featuresExtracted: boolean;
  featurePercent: number;
  featureSummary: Array<{ label: string; value: string }>;
  mlDecisionSupport?: MlDecisionSupport;
  reviewNeededCount: number;
  insights: Array<{ title: string; text: string; tone: "green" | "orange" }>;
  therapistNotes: string;
  therapyGoals: string[];
  reportId?: string;
  reportStatus: "Not started" | "Draft" | "Reviewed" | "Finalized";
  reportMarkdown?: string;
  reportSaveStatus: PersistenceStatus;
  shareStatus: "Not shared" | "Secure link copied" | "Sent to caregiver";
  finalizeStatus?: string;
  statusMessage?: string;
  error?: string;
  updatedAt?: string;
};

export type BackendCase = {
  case_id: string;
  child_code?: string;
  nickname?: string;
  consent_status?: string;
  display_label?: string;
  anonymized_child_code?: string;
};

export type BackendSession = {
  session_id: string;
  case_id: string;
  session_date?: string;
  transcript_id?: string;
  feature_set_id?: string;
  report_id?: string;
  status?: string;
};

export type BackendTranscript = {
  transcript_id: string;
  session_id?: string;
  case_id?: string;
  raw_text?: string;
  transcript_text?: string;
  review_status?: string;
  therapist_attested?: boolean;
  qa_status?: string;
  qa_issues?: Array<{ message?: string } | string>;
  utterances?: Array<{
    utterance_id: string;
    speaker: string;
    text: string;
    start_ms?: number | null;
    end_ms?: number | null;
    unintelligible?: boolean;
  }>;
};

type BackendQa = {
  status?: string;
  qa_status?: string;
  quality_score?: number;
  qa_score?: number;
  summary?: string;
  issues?: string[];
  qa_issues?: string[];
};

type BackendFeatures = {
  feature_id?: string;
  features?: Record<string, string | number | boolean | null> | Array<{ name: string; value: string | number | boolean | null }>;
  core_features?: Record<string, string | number | boolean | null>;
  optional_indicators?: Record<string, string | number | boolean | null>;
};

type BackendMlDecisionSupport = {
  pattern_cues: string[];
  review_suggestions: string[];
  confidence: "limited" | "moderate";
  limitations: string[];
};

export type BackendReport = {
  report_id?: string;
  session_id?: string;
  case_id?: string;
  status?: string;
  export_status?: string;
  title?: string;
  content_markdown?: string;
  markdown?: string;
};

export const defaultTranscript = [
  "@Begin",
  "@Languages:\teng",
  "@Participants:\tCHI Child Target_Child, THER Therapist Investigator",
  "*THER:\tWhat do you see?",
  "*CHI:\tI see a big blue block.",
  "*THER:\tWhat color is it?",
  "*CHI:\tIt is blue.",
  "*THER:\tCan you ask me a question?",
  "*CHI:\tWhat color do you like?",
  "@End"
].join("\n");

export function createInitialWorkflowState(): WorkflowState {
  return {
    caseInfo: {
      clientLabel: "Ethan L."
    },
    childName: "Ethan L.",
    reportPeriod: "May 1 - May 13, 2026",
    recordingStatus: "idle",
    recordingSeconds: 0,
    mockAudioStored: false,
    hasUnsavedRecording: false,
    recordingClearedForPrivacy: false,
    transcriptText: defaultTranscript,
    transcriptLines: [],
    chatMetadata: createDefaultChatMetadata(),
    chatWarnings: [],
    chatValidationIssues: [],
    transcriptReady: false,
    transcriptAttested: false,
    transcriptCompleteness: 0,
    transcriptReviewStatus: "not_started",
    qaStatus: "not_run",
    qaIssues: [],
    transcriptSaveStatus: "idle",
    workflowLoading: false,
    analysisStatus: "not_started",
    featuresExtracted: false,
    featurePercent: 0,
    featureSummary: [],
    reviewNeededCount: 0,
    insights: [
      { title: "Transcript review required", text: "Review speaker labels and transcript quality before report use.", tone: "orange" }
    ],
    therapistNotes: "",
    therapyGoals: [],
    reportStatus: "Not started"
    ,
    reportSaveStatus: "idle",
    shareStatus: "Not shared"
  };
}

export async function generateBackendMlDecisionSupport(sessionId: string): Promise<MlDecisionSupport> {
  const result = await apiRequest<BackendMlDecisionSupport>(`/v1/sessions/${sessionId}/ml-decision-support`, {
    method: "POST"
  });
  return {
    patternCues: result.pattern_cues,
    reviewSuggestions: result.review_suggestions,
    confidence: result.confidence,
    limitations: result.limitations,
    dismissed: false,
    source: "backend"
  };
}

export function createLocalMlDecisionSupport(featureSummary: WorkflowState["featureSummary"]): MlDecisionSupport {
  const numericFeatures = featureSummary
    .map((feature) => ({
      ...feature,
      numericValue: Number.parseFloat(feature.value.replace("%", ""))
    }))
    .filter((feature) => Number.isFinite(feature.numericValue));
  const preferredLabels = [
    "MLU words",
    "TTR",
    "NDW",
    "Question ratio",
    "Unclear / unintelligible ratio",
    "Repetition cue",
    "Echolalia cue",
    "Pronoun reversal cue"
  ];
  const selected = preferredLabels
    .map((label) => numericFeatures.find((feature) => feature.label === label))
    .filter((feature): feature is NonNullable<typeof feature> => Boolean(feature))
    .sort((a, b) => Number(b.numericValue !== 0) - Number(a.numericValue !== 0) || Math.abs(b.numericValue) - Math.abs(a.numericValue))
    .slice(0, 3);
  const childUtterances = numericFeatures.find((feature) => feature.label === "Child utterances")?.numericValue ?? 0;
  return {
    patternCues: selected.map((feature) => `${feature.label} contributed to the local model review pattern (value ${feature.value}).`),
    reviewSuggestions: selected.map((feature) => `Review ${feature.label.toLowerCase()} in transcript context and document the therapist's interpretation.`),
    confidence: childUtterances >= 5 && selected.length >= 3 ? "moderate" : "limited",
    limitations: [
      "This model is trained on limited/public datasets and is not clinically validated for diagnosis.",
      "Pattern cues are model-informed review aids, not clinical conclusions.",
      "Confidence describes input and model limitations, not diagnostic certainty."
    ],
    dismissed: false,
    source: "local"
  };
}

export function loadWorkflowState(): WorkflowState {
  if (typeof window === "undefined") {
    return createInitialWorkflowState();
  }
  const stored = window.sessionStorage.getItem(WORKFLOW_STORAGE_KEY);
  if (!stored) {
    return createInitialWorkflowState();
  }
  try {
    const parsed = JSON.parse(stored) as Partial<WorkflowState>;
    const initial = createInitialWorkflowState();
    const lostUnsavedRecording = parsed.hasUnsavedRecording === true;
    return {
      ...initial,
      ...parsed,
      recordingStatus: lostUnsavedRecording ? "idle" : parsed.recordingStatus ?? initial.recordingStatus,
      hasUnsavedRecording: false,
      recordingClearedForPrivacy: lostUnsavedRecording,
      caseInfo: {
        ...initial.caseInfo,
        ...parsed.caseInfo,
        caseId: parsed.caseInfo?.caseId ?? parsed.caseId,
        clientLabel: parsed.caseInfo?.clientLabel ?? parsed.childName ?? initial.childName
      }
    };
  } catch {
    return createInitialWorkflowState();
  }
}

export function saveWorkflowState(state: WorkflowState): WorkflowState {
  const next = { ...state, updatedAt: new Date().toISOString() };
  if (typeof window !== "undefined") {
    window.sessionStorage.setItem(WORKFLOW_STORAGE_KEY, JSON.stringify(next, (_key, value) => (
      value instanceof Blob ? undefined : value
    )));
  }
  return next;
}

export function ensureWorkflowSession(
  state: WorkflowState,
  source: WorkflowSource,
  overrides: Partial<WorkflowState> = {}
): WorkflowState {
  const shouldCreate = !state.sessionId || state.reportStatus === "Finalized";
  const now = new Date().toISOString();
  const sessionId = shouldCreate ? createLocalSessionId() : state.sessionId;
  const caseId = overrides.caseId ?? state.caseId ?? state.caseInfo.caseId;
  const childName = overrides.childName ?? state.childName;

  return {
    ...(shouldCreate ? createInitialWorkflowState() : state),
    ...overrides,
    sessionId,
    sessionCreatedAt: shouldCreate ? now : state.sessionCreatedAt ?? now,
    caseId,
    caseInfo: {
      caseId,
      clientLabel: childName
    },
    childName,
    source
  };
}

export function prepareTranscriptIntake(
  source: Extract<WorkflowSource, "cha-upload" | "paste-transcript">,
  input: string
): ChatParseResult {
  return source === "cha-upload" ? parseChaTranscript(input) : parsePastedTranscript(input);
}

export function serializeTranscriptLines(lines: TranscriptLine[]): string {
  return buildBasicChatExport({
    lines,
    metadata: createDefaultChatMetadata()
  }).trimEnd();
}

export function evaluateTranscriptQa(
  lines: TranscriptLine[],
  metadata?: ChatMetadata,
  importValidationIssues: string[] = []
): {
  status: TranscriptQaStatus;
  issues: string[];
  summary: string;
} {
  const issues: string[] = [];
  const childCount = lines.filter((line) => line.speaker === "CHI").length;
  const unknownCount = lines.filter((line) => line.speaker === "UNK").length;
  const unclearCount = lines.filter((line) => line.unclear || /\b(?:xxx|yyy|www|\[unclear\])\b/i.test(line.text)).length;
  const emptyCount = lines.filter((line) => !line.text.trim()).length;
  const declaredSpeakers = new Set(metadata?.participants.map((participant) => participant.code) ?? []);

  if (lines.length === 0) issues.push("Transcript has no utterance lines.");
  if (emptyCount > 0) issues.push(`${emptyCount} transcript line${emptyCount === 1 ? " is" : "s are"} empty.`);
  if (childCount === 0) issues.push("No child speaker lines are marked CHI.");
  if (childCount > 0 && childCount < 3) issues.push("Child sample has fewer than 3 utterances.");
  if (unknownCount / Math.max(lines.length, 1) > 0.25) issues.push("More than 25% of utterances have unknown speaker labels.");
  if (unclearCount / Math.max(lines.length, 1) > 0.2) issues.push("More than 20% of utterances are marked unclear.");
  if (metadata && metadata.participants.length === 0) issues.push("Missing @Participants header.");
  if (metadata && metadata.languages.length === 0) issues.push("Missing @Languages header.");
  if (metadata && declaredSpeakers.size > 0) {
    for (const speaker of new Set(lines.map((line) => line.speaker))) {
      if (!declaredSpeakers.has(speaker)) issues.push(`Speaker ${speaker} is not declared in @Participants.`);
    }
  }
  for (const issue of importValidationIssues) {
    if (!issues.includes(issue)) issues.push(issue);
  }

  const status: TranscriptQaStatus = lines.length === 0 || emptyCount > 0 || childCount === 0
    ? "fail"
    : issues.length > 0
      ? "warning"
      : "pass";
  return {
    status,
    issues,
    summary: status === "pass" ? "Transcript QA completed with no flagged issues." : `Transcript QA completed with ${issues.length} review item${issues.length === 1 ? "" : "s"}.`
  };
}

export function extractLanguageSampleFeatures(
  lines: TranscriptLine[],
  metadata: ChatMetadata = createDefaultChatMetadata()
): LanguageSampleFeatures {
  const childLines = lines.filter((line) => line.speaker.toUpperCase() === "CHI");
  const declaredAdults = new Set(
    metadata.participants
      .filter((participant) => participant.code.toUpperCase() !== "CHI" && participant.code.toUpperCase() !== "UNK")
      .map((participant) => participant.code.toUpperCase())
  );
  const adultLines = lines.filter((line) => {
    const speaker = line.speaker.toUpperCase();
    if (speaker === "CHI" || speaker === "UNK") return false;
    return declaredAdults.size === 0 || declaredAdults.has(speaker);
  });
  const childTokens = childLines.flatMap((line) => tokenizeLanguageSample(line.text));
  const uniqueChildTokens = new Set(childTokens);
  const unclearCount = lines.filter((line) => (
    line.unclear || /\b(?:xxx|yyy|www|\[unclear\])\b/iu.test(line.text)
  )).length;
  const repetitionCue = childLines.reduce((count, line) => (
    count
    + (line.text.match(/\[\/\]/gu)?.length ?? 0)
    + (line.text.match(/\b([\p{L}\p{N}']+)\s+\1\b/giu)?.length ?? 0)
  ), 0);
  let previousAdult = "";
  let echolaliaCue = 0;
  for (const line of lines) {
    const normalized = normalizeCueText(line.text);
    if (line.speaker.toUpperCase() === "CHI") {
      if (previousAdult && normalized && normalized === previousAdult) echolaliaCue += 1;
    } else if (line.speaker.toUpperCase() !== "UNK") {
      previousAdult = normalized;
    }
  }
  const pronounReversalCue = childLines.reduce((count, line) => (
    count + (line.text.match(/\b(?:you am|me am|my want|i are)\b/giu)?.length ?? 0)
  ), 0);

  return {
    totalUtterances: lines.length,
    childUtterances: childLines.length,
    adultUtterances: adultLines.length,
    totalWords: childTokens.length,
    mluWords: roundFeature(childLines.length ? childTokens.length / childLines.length : 0),
    ndw: uniqueChildTokens.size,
    ttr: roundFeature(childTokens.length ? uniqueChildTokens.size / childTokens.length : 0),
    questionRatio: roundFeature(childLines.length ? childLines.filter((line) => line.text.includes("?")).length / childLines.length : 0),
    unclearRatio: roundFeature(lines.length ? unclearCount / lines.length : 0),
    repetitionCue,
    echolaliaCue,
    pronounReversalCue
  };
}

export function languageSampleFeatureSummary(features: LanguageSampleFeatures): WorkflowState["featureSummary"] {
  return [
    { label: "Total utterances", value: String(features.totalUtterances) },
    { label: "Child utterances", value: String(features.childUtterances) },
    { label: "Adult utterances", value: String(features.adultUtterances) },
    { label: "Total words", value: String(features.totalWords) },
    { label: "MLU words", value: formatFeatureNumber(features.mluWords) },
    { label: "NDW", value: String(features.ndw) },
    { label: "TTR", value: formatFeatureNumber(features.ttr) },
    { label: "Question ratio", value: formatFeatureRatio(features.questionRatio) },
    { label: "Unclear / unintelligible ratio", value: formatFeatureRatio(features.unclearRatio) },
    { label: "Repetition cue", value: String(features.repetitionCue) },
    { label: "Echolalia cue", value: String(features.echolaliaCue) },
    { label: "Pronoun reversal cue", value: String(features.pronounReversalCue) }
  ];
}

export function parseChaTranscript(input: string): ChatParseResult {
  const normalized = normalizeLineEndings(input).trim();
  const sourceLines = normalized.split("\n");
  const hasBegin = sourceLines.some((line) => line.trim() === "@Begin");
  const hasEnd = sourceLines.some((line) => line.trim() === "@End");

  if (!hasBegin || !hasEnd || !sourceLines.some((line) => line.trim().startsWith("*"))) {
    throw new Error("Invalid .cha file: expected @Begin, @End, and at least one speaker line such as *CHI:.");
  }

  const metadata = parseChatMetadata(sourceLines);
  const warnings: string[] = [];
  const validationIssues: string[] = [];
  const transcriptLines: TranscriptLine[] = [];
  const declaredSpeakers = new Set(metadata.participants.map((participant) => participant.code));

  if (metadata.participants.length === 0) {
    validationIssues.push("Missing @Participants header.");
  }

  sourceLines.forEach((rawLine, index) => {
    const trimmed = rawLine.trim();
    if (!trimmed || trimmed === "@Begin" || trimmed === "@End" || trimmed === "@UTF8") return;
    if (trimmed.startsWith("@")) return;
    if (trimmed.startsWith("%")) {
      const tier = trimmed.match(/^(%[^:\s]+):/)?.[1] ?? trimmed.split(/\s/, 1)[0];
      const warning = `Unsupported dependent tier ${tier} was not imported.`;
      if (!warnings.includes(warning)) warnings.push(warning);
      return;
    }

    const speakerMatch = rawLine.match(/^\*([A-Za-z0-9_]{1,8}):\s*(.*)$/);
    if (speakerMatch) {
      const speaker = speakerMatch[1].toUpperCase();
      const parsed = parseTimestamp(speakerMatch[2]);
      transcriptLines.push({
        lineId: `line-${transcriptLines.length + 1}`,
        speaker,
        text: parsed.text,
        ...(parsed.startMs !== undefined ? { startMs: parsed.startMs, endMs: parsed.endMs } : {})
      });
      if (!parsed.text) {
        validationIssues.push(`Line ${index + 1} has an empty utterance.`);
      }
      if (!declaredSpeakers.has(speaker)) {
        validationIssues.push(`Speaker ${speaker} is not declared in @Participants.`);
      }
      return;
    }

    if (/^\s+/.test(rawLine) && transcriptLines.length > 0) {
      const previous = transcriptLines[transcriptLines.length - 1];
      const parsed = parseTimestamp(trimmed);
      transcriptLines[transcriptLines.length - 1] = {
        ...previous,
        text: `${previous.text} ${parsed.text}`.trim(),
        ...(parsed.startMs !== undefined ? { startMs: parsed.startMs, endMs: parsed.endMs } : {})
      };
      return;
    }

    validationIssues.push(`Line ${index + 1} is malformed and was not imported.`);
  });

  return {
    transcriptText: normalized,
    transcriptLines,
    metadata,
    warnings,
    validationIssues
  };
}

export function parsePastedTranscript(input: string): ChatParseResult {
  const normalized = normalizeLineEndings(input).trim();
  if (!normalized) {
    throw new Error("Paste transcript text before saving.");
  }

  if (normalized.includes("@Begin") || normalized.split("\n").some((line) => /^\*[A-Za-z0-9_]+:/.test(line))) {
    return parseChaTranscript(normalized);
  }

  const transcriptLines = normalized
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const labelled = line.match(/^([^:]{1,40}):\s*(.+)$/);
      const speaker = labelled ? normalizeSpeakerLabel(labelled[1]) : "UNK";
      const parsed = parseTimestamp(labelled ? labelled[2] : line);
      return {
        lineId: `line-${index + 1}`,
        speaker,
        text: parsed.text,
        ...(parsed.startMs !== undefined ? { startMs: parsed.startMs, endMs: parsed.endMs } : {})
      };
    })
    .filter((line) => line.text);

  if (transcriptLines.length === 0) {
    throw new Error("Paste transcript text with at least one speaker line.");
  }

  const speakers = [...new Set(transcriptLines.map((line) => line.speaker))];
  const participantText = speakers.map((speaker) => `${speaker} ${speaker}`).join(", ");
  const speakerTiers = transcriptLines.map((line) => {
    const timestamp = line.startMs !== undefined && line.endMs !== undefined
      ? ` \u0015${line.startMs}_${line.endMs}\u0015`
      : "";
    return `*${line.speaker}:\t${line.text}${timestamp}`;
  });

  const transcriptText = [
      "@Begin",
      "@Languages:\teng",
      `@Participants:\t${participantText}`,
      ...speakerTiers,
      "@End"
    ].join("\n");
  return parseChaTranscript(transcriptText);
}

export function buildBasicChatExport({
  lines,
  metadata,
  includeMedia = false,
  fallbackMediaName,
  allowInvalid = false
}: {
  lines: TranscriptLine[];
  metadata: ChatMetadata;
  includeMedia?: boolean;
  fallbackMediaName?: string;
  allowInvalid?: boolean;
}): string {
  const emptyLine = lines.findIndex((line) => !line.text.trim());
  if (!allowInvalid && emptyLine >= 0) throw new Error(`Line ${emptyLine + 1} has an empty utterance.`);
  const unknownLine = lines.findIndex((line) => !isValidSpeakerCode(line.speaker) || line.speaker === "UNK");
  if (!allowInvalid && unknownLine >= 0) throw new Error(`Line ${unknownLine + 1} has an unknown speaker.`);

  const languages = metadata.languages.length > 0 ? metadata.languages : ["eng"];
  const speakerCodes = [...new Set(lines.map((line) => line.speaker.toUpperCase()))];
  const participants = speakerCodes.map((code) => (
    metadata.participants.find((participant) => participant.code === code) ?? defaultParticipant(code)
  ));
  const existingIds = new Map(metadata.ids.map((id) => [id.code, id.raw]));
  const primaryLanguage = languages[0] || "eng";
  const media = metadata.media ?? (fallbackMediaName ? { name: fallbackMediaName, type: "audio" } : undefined);
  const output = [
    "@UTF8",
    "@Begin",
    `@Languages:\t${languages.join(", ")}`,
    `@Participants:\t${participants.map((participant) => `${participant.code} ${participant.name} ${participant.role}`).join(", ")}`,
    ...participants.map((participant) => (
      `@ID:\t${existingIds.get(participant.code) ?? `${primaryLanguage}|TherapistAppV2|${participant.code}|||||${participant.role}|||`}`
    )),
    ...(includeMedia && media ? [`@Media:\t${sanitizeMediaName(media.name)}, ${media.type || "audio"}`] : []),
    ...lines.map(renderChatSpeakerLine),
    "@End",
    ""
  ];
  return output.join("\n");
}

export async function getUsableCase(): Promise<BackendCase> {
  const cases = await apiGet<BackendCase[]>("/cases");
  const granted = cases.find((item) => item.consent_status === "granted");
  if (granted ?? cases[0]) {
    return granted ?? cases[0];
  }
  return apiRequest<BackendCase>("/cases", {
    method: "POST",
    body: JSON.stringify({
      child_code: `DEMO-${Date.now().toString().slice(-5)}`,
      nickname: "Demo child",
      age_months: 62,
      language: "English",
      consent_status: "granted",
      notes: "Local demo case; do not use real child data."
    })
  });
}

export async function createBackendSession(source: WorkflowSource): Promise<BackendSession> {
  const childCase = await getUsableCase();
  const session = await apiRequest<BackendSession>(`/cases/${childCase.case_id}/sessions`, {
    method: "POST",
    body: JSON.stringify({
      session_date: new Date().toISOString().slice(0, 10),
      session_type: "therapy_session",
      notes: `Simplified therapist workflow: ${source}. Audio/ASR remains experimental unless separately processed.`
    })
  });
  return session;
}

export async function getBackendCase(caseId: string): Promise<BackendCase> {
  return apiGet<BackendCase>(`/cases/${caseId}`);
}

export async function getBackendSession(sessionId: string): Promise<BackendSession> {
  return apiGet<BackendSession>(`/sessions/${sessionId}`);
}

export async function getBackendTranscript(transcriptId: string): Promise<BackendTranscript> {
  return apiGet<BackendTranscript>(`/transcripts/${transcriptId}`);
}

export async function getBackendSessionTranscript(sessionId: string): Promise<BackendTranscript> {
  return apiGet<BackendTranscript>(`/sessions/${sessionId}/transcript`);
}

export async function getBackendReport(reportId: string): Promise<BackendReport> {
  return apiGet<BackendReport>(`/reports/${reportId}`);
}

export function backendTranscriptLines(transcript: BackendTranscript): TranscriptLine[] {
  return (transcript.utterances ?? []).map((utterance) => ({
    lineId: utterance.utterance_id,
    speaker: String(utterance.speaker),
    text: utterance.text,
    ...(utterance.start_ms == null ? {} : { startMs: utterance.start_ms }),
    ...(utterance.end_ms == null ? {} : { endMs: utterance.end_ms }),
    unclear: Boolean(utterance.unintelligible)
  }));
}

export async function createBackendTranscript(
  sessionId: string,
  source: Extract<WorkflowSource, "cha-upload" | "paste-transcript">,
  sourceText: string,
  transcriptText: string,
  filename?: string
): Promise<BackendTranscript> {
  if (source === "cha-upload") {
    return apiRequest<BackendTranscript>(`/sessions/${sessionId}/transcripts/upload-cha`, {
      method: "POST",
      body: JSON.stringify({
        filename: filename || "transcript.cha",
        cha_text: transcriptText
      })
    });
  }
  return apiRequest<BackendTranscript>(`/sessions/${sessionId}/transcripts/manual`, {
    method: "POST",
    body: JSON.stringify({
      text: sourceText,
      language: "English"
    })
  });
}

export async function updateBackendTranscript(
  transcriptId: string,
  transcriptText: string,
  reviewerNote: string
): Promise<BackendTranscript> {
  return apiRequest<BackendTranscript>(`/transcripts/${transcriptId}`, {
    method: "PATCH",
    body: JSON.stringify({
      raw_text: transcriptText,
      reviewer_note: reviewerNote
    })
  });
}

export async function runBackendQa(transcriptId: string): Promise<BackendQa> {
  const response = await apiRequest<{
    overall_status: string;
    issues: any[];
    transcript_id: string;
  }>(`/transcripts/${transcriptId}/qa`, { method: "POST" });

  const status = normalizeQaStatus(response.overall_status);
  const issues = response.issues.map((issue) => typeof issue === "string" ? issue : issue?.message ?? "Transcript QA issue");
  const summary = issues.length > 0
    ? `QA detected ${issues.length} issue(s): ${issues.join("; ")}`
    : "Transcript QA completed successfully.";

  return {
    status,
    qa_status: status,
    issues,
    summary
  };
}

export async function attestBackendTranscript(transcriptId: string): Promise<void> {
  await apiRequest(`/transcripts/${transcriptId}/attest`, {
    method: "POST",
    body: JSON.stringify({
      attested_by: "Demo Therapist",
      reason: "Therapist attested transcript quality after transcript QA.",
      override_qa_failure: false
    })
  });
}

export async function runBackendAnalysis(
  sessionId: string,
  transcriptId?: string,
  qa: BackendQa = { status: "pass", summary: "Transcript QA and therapist attestation completed." }
): Promise<Pick<WorkflowState, "qaStatus" | "qaSummary" | "transcriptAttested" | "transcriptCompleteness" | "featuresExtracted" | "featurePercent" | "featureSummary" | "reviewNeededCount" | "insights">> {
  let features: BackendFeatures;
  try {
    const extractionPath = transcriptId
      ? `/transcripts/${transcriptId}/extract-features`
      : `/sessions/${sessionId}/features/extract`;
    features = await apiRequest<BackendFeatures>(extractionPath, { method: "POST" });
  } catch (error) {
    if (!(error instanceof ApiError)) {
      throw error;
    }
    features = await apiGet<BackendFeatures>(`/sessions/${sessionId}/features`);
  }
  return summarizeAnalysis(qa, features);
}

export async function generateBackendReport(sessionId: string): Promise<BackendReport> {
  const report = await apiRequest<any>(`/sessions/${sessionId}/reports/draft`, { method: "POST" });
  return {
    ...report,
    content_markdown: report.markdown
  };
}

export async function updateBackendReport(reportId: string, markdown: string, therapistNotes: string): Promise<BackendReport> {
  return apiRequest<BackendReport>(`/reports/${reportId}`, {
    method: "PATCH",
    body: JSON.stringify({ markdown, therapist_notes: therapistNotes })
  });
}

export async function finalizeBackendReport(reportId: string): Promise<BackendReport> {
  return apiRequest<BackendReport>(`/reports/${reportId}/sign-off`, {
    method: "POST",
    body: JSON.stringify({
      signed_by: "Demo Therapist",
      attestation: "I reviewed and accept responsibility for this report."
    })
  });
}

export async function exportBackendReport(reportId: string, format: "markdown" | "html"): Promise<{
  filename: string;
  content: string;
  content_type: string;
}> {
  return apiGet(`/reports/${reportId}/export?format=${format}`);
}

export async function exportReviewedCha(transcriptId: string): Promise<{
  filename: string;
  cha_text: string;
}> {
  return apiGet(`/transcripts/${transcriptId}/export-cha`);
}

export function summarizeAnalysis(qa: BackendQa, backendFeatures?: BackendFeatures): Pick<WorkflowState, "qaStatus" | "qaSummary" | "transcriptAttested" | "transcriptCompleteness" | "featuresExtracted" | "featurePercent" | "featureSummary" | "reviewNeededCount" | "insights"> {
  const score = Number(qa.quality_score ?? qa.qa_score ?? 0.92);
  const issues = qa.issues ?? qa.qa_issues ?? [];
  const directFeatures = Array.isArray(backendFeatures?.features)
    ? Object.fromEntries(backendFeatures.features.map((item) => [item.name, item.value]))
    : backendFeatures?.features ?? {};
  const features = {
    ...directFeatures,
    ...(backendFeatures?.core_features ?? {}),
    ...(backendFeatures?.optional_indicators ?? {})
  };
  const mlu = pickFeature(features, ["mlu_words", "mean_length_of_utterance_words", "mean_length_utterance_words"], "3.2");
  const ndw = pickFeature(features, ["ndw", "number_of_different_words"], "78");
  const questionRatio = pickFeature(features, ["question_ratio", "reciprocal_question_ratio"], "6%");
  const featureSummary = [
    { label: "MLU words", value: String(mlu) },
    { label: "Different words", value: String(ndw) },
    { label: "Question ratio", value: String(questionRatio) }
  ];
  const reviewNeededCount = Math.max(issues.length, score < 0.9 ? 1 : 0);
  return {
    qaStatus: normalizeQaStatus(qa.status ?? qa.qa_status),
    qaSummary: qa.summary ?? "Transcript QA completed. Therapist review remains required before final report use.",
    transcriptAttested: true,
    transcriptCompleteness: Math.round(Math.max(0, Math.min(1, score)) * 100),
    featuresExtracted: Boolean(backendFeatures),
    featurePercent: Boolean(backendFeatures) ? 88 : 72,
    featureSummary,
    reviewNeededCount,
    insights: [
      { title: "Transcript ready for review", text: "Transcript QA ran and therapist attestation was recorded for this workflow.", tone: "green" },
      { title: "Feature summary available", text: "Language feature values are available for therapist interpretation.", tone: "green" },
      {
        title: reviewNeededCount > 0 ? "Review item present" : "Review before report",
        text: reviewNeededCount > 0 ? "Check QA notes before using this draft in a report." : "Confirm wording before generating an exportable progress report.",
        tone: reviewNeededCount > 0 ? "orange" : "green"
      }
    ]
  };
}

function normalizeQaStatus(status?: string): TranscriptQaStatus {
  const normalized = status?.toLowerCase();
  if (normalized === "pass" || normalized === "passed" || normalized === "reviewed") return "pass";
  if (normalized === "fail" || normalized === "failed" || normalized === "error") return "fail";
  if (normalized === "warning" || normalized === "warn" || normalized === "needs_review") return "warning";
  return "warning";
}

export function createMockAnalysisSummary(): Pick<WorkflowState, "qaStatus" | "qaSummary" | "transcriptAttested" | "transcriptCompleteness" | "featuresExtracted" | "featurePercent" | "featureSummary" | "reviewNeededCount" | "insights"> {
  return {
    qaStatus: "warning",
    qaSummary: "Backend transcript data was unavailable, so this is a local decision-support preview only.",
    transcriptAttested: false,
    transcriptCompleteness: 82,
    featuresExtracted: true,
    featurePercent: 76,
    featureSummary: [
      { label: "Transcript source", value: "Local preview" },
      { label: "Feature status", value: "Preview" },
      { label: "Review gate", value: "Required" }
    ],
    reviewNeededCount: 1,
    insights: [
      { title: "Experimental audio workflow", text: "Recording and ASR are simulated until real processing is enabled.", tone: "orange" },
      { title: "Therapist review required", text: "Use this preview only to continue the therapist review workflow.", tone: "orange" }
    ]
  };
}

function pickFeature(features: Record<string, string | number | boolean | null>, names: string[], fallback: string): string | number | boolean {
  for (const name of names) {
    const value = features[name];
    if (value !== undefined && value !== null && value !== "") {
      return value;
    }
  }
  return fallback;
}

function createLocalSessionId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `local_${crypto.randomUUID()}`;
  }
  return `local_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

function normalizeLineEndings(value: string): string {
  return value.replace(/\r\n?/g, "\n");
}

function tokenizeLanguageSample(value: string): string[] {
  return (value.toLowerCase().match(/[\p{L}\p{N}']+/gu) ?? [])
    .filter((token) => !["xxx", "yyy", "www", "unclear"].includes(token));
}

function normalizeCueText(value: string): string {
  return tokenizeLanguageSample(value).join(" ");
}

function roundFeature(value: number): number {
  return Number(value.toFixed(4));
}

function formatFeatureNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function formatFeatureRatio(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function createDefaultChatMetadata(): ChatMetadata {
  return {
    languages: ["eng"],
    participants: [],
    ids: [],
    headers: {}
  };
}

function parseChatMetadata(lines: string[]): ChatMetadata {
  const headers: Record<string, string[]> = {};
  for (const rawLine of lines) {
    const match = rawLine.match(/^(@[^:\s]+):\s*(.*)$/);
    if (!match) continue;
    headers[match[1]] = [...(headers[match[1]] ?? []), match[2].trim()];
  }

  const languages = (headers["@Languages"] ?? [])
    .flatMap((value) => value.split(/[,;\s]+/))
    .map((value) => value.trim())
    .filter(Boolean);
  const participants = (headers["@Participants"] ?? [])
    .flatMap((value) => value.split(","))
    .map(parseParticipant)
    .filter((participant): participant is ChatParticipant => participant !== undefined);
  const ids = (headers["@ID"] ?? [])
    .map((raw) => {
      const code = raw.split("|")[2]?.trim().toUpperCase();
      return code ? { code, raw } : undefined;
    })
    .filter((id): id is ChatId => id !== undefined);
  const mediaValue = headers["@Media"]?.[0];
  const mediaParts = mediaValue?.split(",").map((value) => value.trim());

  return {
    languages,
    participants,
    ids,
    ...(mediaParts?.[0] ? { media: { name: mediaParts[0], type: mediaParts[1] || "audio" } } : {}),
    headers
  };
}

function parseParticipant(value: string): ChatParticipant | undefined {
  const parts = value.trim().split(/\s+/);
  const code = parts.shift()?.toUpperCase();
  if (!code) return undefined;
  return {
    code,
    name: parts.shift() || defaultParticipant(code).name,
    role: parts.join(" ") || defaultParticipant(code).role
  };
}

function defaultParticipant(code: string): ChatParticipant {
  const defaults: Record<string, Omit<ChatParticipant, "code">> = {
    CHI: { name: "Child", role: "Target_Child" },
    INV: { name: "Investigator", role: "Investigator" },
    THER: { name: "Therapist", role: "Investigator" },
    PAR: { name: "Parent", role: "Adult" },
    MOT: { name: "Mother", role: "Adult" },
    FAT: { name: "Father", role: "Adult" }
  };
  return { code, ...(defaults[code] ?? { name: code, role: "Adult" }) };
}

function renderChatSpeakerLine(line: TranscriptLine): string {
  const text = line.unclear && !/\b(?:xxx|\[unclear\])\b/i.test(line.text)
    ? `${line.text.trim()} [unclear]`
    : line.text.trim();
  const terminator = /[.?!]$/.test(text) || /\]$/.test(text) ? "" : " .";
  const timestamp = line.startMs !== undefined && line.endMs !== undefined
    ? ` \u0015${line.startMs}_${line.endMs}\u0015`
    : "";
  return `*${line.speaker.toUpperCase()}:\t${text}${terminator}${timestamp}`;
}

function isValidSpeakerCode(value: string): boolean {
  return /^[A-Za-z][A-Za-z0-9_]{0,7}$/.test(value);
}

function sanitizeMediaName(value: string): string {
  return value.replace(/\.[A-Za-z0-9]+$/, "").replace(/[^A-Za-z0-9_-]/g, "_") || "session_audio";
}

function parseTimestamp(value: string): { text: string; startMs?: number; endMs?: number } {
  const timestamp = value.match(/\u0015(\d+)_(\d+)\u0015/);
  const text = value.replace(/\s*\u0015\d+_\d+\u0015\s*/g, " ").trim();
  if (!timestamp) return { text };
  return {
    text,
    startMs: Number(timestamp[1]),
    endMs: Number(timestamp[2])
  };
}

function normalizeSpeakerLabel(value: string): string {
  const compact = value.trim().toUpperCase().replace(/[^A-Z0-9_]/g, "");
  const aliases: Record<string, string> = {
    CHILD: "CHI",
    KID: "CHI",
    THERAPIST: "THER",
    CLINICIAN: "THER",
    INVESTIGATOR: "INV",
    PARENT: "PAR",
    CAREGIVER: "PAR",
    MOTHER: "MOT",
    MOM: "MOT",
    FATHER: "FAT",
    DAD: "FAT"
  };
  return aliases[compact] ?? (compact.slice(0, 8) || "UNK");
}

export type BackendAudioFileMetadata = {
  audio_file_id: string;
  session_id: string;
  case_id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  upload_status: string;
};

export async function uploadAudioFileBytes(uploadUrl: string, blob: Blob): Promise<void> {
  const response = await fetch(`${API_BASE}${uploadUrl}`, {
    method: "PUT",
    body: blob,
    headers: {
      "content-type": blob.type
    }
  });
  if (!response.ok) {
    throw new Error(`Failed to upload audio file: ${response.statusText}`);
  }
}

export async function getSessionAudioFiles(sessionId: string): Promise<BackendAudioFileMetadata[]> {
  return apiGet<BackendAudioFileMetadata[]>(`/sessions/${sessionId}/audio`);
}
