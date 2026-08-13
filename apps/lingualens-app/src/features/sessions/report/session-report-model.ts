import type { BackendReport, WorkflowState } from "@/lib/workflow";

export type SnapshotIntegrityState =
  | { status: "not_applicable" }
  | { status: "checking" }
  | { status: "valid" }
  | { status: "invalid"; reason: string };

export function clinicianLabel(userId: string) {
  if (userId === "therapist-demo") return "Demo Therapist";
  return userId
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function downloadTextFile(text: string, filename: string, contentType = "text/plain") {
  if (typeof document === "undefined" || typeof URL.createObjectURL !== "function") return;
  const url = URL.createObjectURL(new Blob([text], { type: `${contentType};charset=utf-8` }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function versionLabel(value?: number | string) {
  return value == null || value === "" ? "Unavailable" : `Version ${value}`;
}

export function signedSnapshotRecord(report: BackendReport | null | undefined): Record<string, unknown> | undefined {
  const snapshot = report?.signed_snapshot;
  return snapshot && typeof snapshot === "object" && !Array.isArray(snapshot) ? snapshot : undefined;
}

export function signedSnapshotString(report: BackendReport | null | undefined, key: string): string | undefined {
  const value = signedSnapshotRecord(report)?.[key];
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

export function signedSnapshotNumber(report: BackendReport | null | undefined, key: string): number | undefined {
  const value = signedSnapshotRecord(report)?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

export function signedSnapshotProviderString(report: BackendReport | null | undefined, key: string): string | undefined {
  const provider = signedSnapshotRecord(report)?.provider;
  if (!provider || typeof provider !== "object" || Array.isArray(provider)) return undefined;
  const value = (provider as Record<string, unknown>)[key];
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function signedSnapshotGeneratedVersion(report: BackendReport | null | undefined, key: string): string | number | undefined {
  const generatedFrom = signedSnapshotRecord(report)?.generated_from_versions;
  if (!generatedFrom || typeof generatedFrom !== "object" || Array.isArray(generatedFrom)) return undefined;
  const value = (generatedFrom as Record<string, unknown>)[key];
  return typeof value === "string" || typeof value === "number" ? value : undefined;
}

export function reportGeneratedVersion(
  report: BackendReport | null | undefined,
  state: WorkflowState,
  key: "transcript_version" | "schema_version",
) {
  if (report?.status === "Signed Off") return signedSnapshotGeneratedVersion(report, key);
  return report?.generated_from_versions?.[key] ?? state.reportGeneratedFromVersions?.[key];
}

export function finalizedSafetyMetadataString(
  report: BackendReport | null | undefined,
  key: "status" | "validator_version" | "rule_set_version",
) {
  if (report?.status !== "Signed Off") return undefined;
  const snapshotSafety = signedSnapshotRecord(report)?.finalized_safety_result;
  if (!snapshotSafety || typeof snapshotSafety !== "object" || Array.isArray(snapshotSafety)) return undefined;
  const value = (snapshotSafety as Record<string, unknown>)[key];
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

export function reportMetadataString(
  report: BackendReport | null | undefined,
  key: "requested_provider" | "actual_provider" | "provider_version",
) {
  if (report?.status === "Signed Off") return signedSnapshotProviderString(report, key);
  return report?.[key];
}

export function validateSignedSnapshotEnvelope(report: BackendReport | null | undefined): { valid: true } | { valid: false; reason: string } {
  const snapshot = signedSnapshotRecord(report);
  if (!snapshot) return { valid: false, reason: "The immutable snapshot is missing or malformed." };
  const markdown = signedSnapshotString(report, "markdown");
  const hash = signedSnapshotString(report, "report_hash");
  const version = signedSnapshotNumber(report, "report_version");
  const signer = signedSnapshotString(report, "signed_by");
  const signedAt = signedSnapshotString(report, "signed_at");
  if (!markdown || !hash || !version || !signer || !signedAt) {
    return { valid: false, reason: "Required immutable snapshot content or signing provenance is missing." };
  }
  if (!/^[a-f0-9]{64}$/i.test(hash) || report?.signed_snapshot_hash !== hash) {
    return { valid: false, reason: "The signed snapshot hash is invalid or does not match its persisted envelope." };
  }
  if (report?.signed_snapshot_version !== version || Number.isNaN(Date.parse(signedAt))) {
    return { valid: false, reason: "The signed snapshot version or timestamp is invalid." };
  }
  return { valid: true };
}

export async function verifySignedSnapshotHash(report: BackendReport): Promise<{ valid: true } | { valid: false; reason: string }> {
  const envelope = validateSignedSnapshotEnvelope(report);
  if (!envelope.valid) return envelope;
  const snapshot = signedSnapshotRecord(report);
  const expectedHash = signedSnapshotString(report, "report_hash");
  if (!snapshot || !expectedHash) return { valid: false, reason: "The immutable snapshot hash payload is missing." };

  try {
    const { report_hash: _excludedHash, ...payload } = snapshot;
    const canonicalJson = JSON.stringify(sortCanonicalJson(payload));
    const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonicalJson));
    const actualHash = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
    return actualHash === expectedHash.toLowerCase()
      ? { valid: true }
      : { valid: false, reason: "The signed snapshot payload does not match its persisted SHA-256 hash." };
  } catch {
    return { valid: false, reason: "The signed snapshot hash could not be verified in this browser." };
  }
}

function sortCanonicalJson(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortCanonicalJson);
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return Object.fromEntries(Object.keys(record).sort().map((key) => [key, sortCanonicalJson(record[key])]));
  }
  return value;
}

export function resetSignedReportForRevision(markdown: string) {
  const withoutSignedClaims = markdown
    .split("\n")
    .filter((line) => !/^\s*-\s*(?:Signed by|Sign-off status|Export timestamp):/i.test(line))
    .join("\n");
  const withPendingSignoff = replaceMarkdownSection(withoutSignedClaims, "## Therapist Sign-off", ["Pending therapist edit and sign-off."]);
  return replaceMarkdownSection(withPendingSignoff, "## Export Timestamp", ["- Pending until therapist sign-off."]);
}

function replaceMarkdownSection(markdown: string, heading: string, replacement: string[]) {
  const lines = markdown.split("\n");
  const start = lines.indexOf(heading);
  if (start < 0) return [...lines, "", heading, ...replacement].join("\n");
  const end = lines.findIndex((line, index) => index > start && line.startsWith("## "));
  return [...lines.slice(0, start), heading, ...replacement, ...(end < 0 ? [] : ["", ...lines.slice(end)])].join("\n");
}

export function replaceRevisionUrl(sessionId?: string, reportId?: string, caseId?: string, transcriptId?: string) {
  if (typeof window === "undefined" || !sessionId || !reportId) return;
  const current = new URL(window.location.href);
  const params = new URLSearchParams({ view: "report" });
  const preservedCaseId = current.searchParams.get("case_id") ?? caseId;
  const preservedTranscriptId = current.searchParams.get("transcript_id") ?? transcriptId;
  if (preservedCaseId) params.set("case_id", preservedCaseId);
  if (preservedTranscriptId) params.set("transcript_id", preservedTranscriptId);
  params.set("report_id", reportId);
  window.history.replaceState(window.history.state, "", `/sessions/${encodeURIComponent(sessionId)}?${params.toString()}`);
}

export function finalizedSafetyLabel(report: BackendReport | null | undefined) {
  let status: unknown = finalizedSafetyMetadataString(report, "status");
  if (report?.status !== "Signed Off") status ??= report?.finalized_safety_result?.status;
  if (typeof status !== "string" || status.length === 0) return "Unavailable";
  return `${status.charAt(0).toUpperCase()}${status.slice(1).replaceAll("_", " ")}`;
}

export function reportSourceLabel(report: BackendReport | null | undefined) {
  const requested = reportMetadataString(report, "requested_provider");
  const actual = reportMetadataString(report, "actual_provider");
  if (actual && requested && actual !== requested) return `${actual} (requested ${requested})`;
  return actual ?? requested;
}

export function reportWorkflowLabel(state: WorkflowState, report: BackendReport | null | undefined) {
  if (report?.status === "Failed") return "Safety validation failed";
  if (report?.status?.toLowerCase() === "processing") return "Processing";
  if (state.reportStatus === "not_started") return "Never generated";
  return `${state.reportStatus.charAt(0).toUpperCase()}${state.reportStatus.slice(1).replaceAll("_", " ")}`;
}

export function reportSaveStateLabel(status: WorkflowState["reportSaveStatus"], isFinalized: boolean, isStale: boolean) {
  if (isFinalized) return "Locked snapshot";
  if (isStale) return "Blocked — regenerate";
  if (status === "unsaved") return "Unsaved changes";
  if (status === "saving") return "Saving";
  if (status === "saved") return "Saved";
  if (status === "failed") return "Save failed";
  return "Not saved";
}

export function createDraftText(state: WorkflowState) {
  return [
    "# Draft Report Preview", "", `Child/session: ${state.childName}`, `Report period: ${state.reportPeriod}`,
    `Transcript readiness: ${state.transcriptCompleteness || 0}%`, `Reviewed transcript status: ${state.transcriptReviewStatus}`,
    `Review-needed count: ${state.reviewNeededCount}`, "", "## Strengths",
    ...(state.featureSummary.length ? state.featureSummary.map((item) => `- ${item.label}: ${item.value}`) : ["- Feature summary pending therapist review"]),
    "", "## Therapist Notes", state.therapistNotes || "- No therapist notes recorded.", "", "## Therapy Goals",
    ...(state.therapyGoals.length ? state.therapyGoals.map((goal) => `- ${goal}`) : ["- No therapy goals recorded."]),
    "", "## Needs Support", "- Review transcript wording before caregiver sharing", "", "## Next Steps",
    "- Therapist edits and finalizes this report", "", "Decision-support only.", "Not diagnostic.", "Therapist review required.",
  ].join("\n");
}

export function parseGoals(value: string) {
  return value.split("\n").map((goal) => goal.trim()).filter(Boolean);
}

export function mergeReportInputs(markdown: string, therapistNotes: string, therapyGoals: string[]) {
  const withoutInputs = markdown
    .replace(/\n*## Therapist Notes[\s\S]*?(?=\n## |\s*$)/, "")
    .replace(/\n*## Therapy Goals[\s\S]*?(?=\n## |\s*$)/, "")
    .trimEnd();
  return [withoutInputs, "", "## Therapist Notes", therapistNotes || "- No therapist notes recorded.", "", "## Therapy Goals",
    ...(therapyGoals.length ? therapyGoals.map((goal) => `- ${goal}`) : ["- No therapy goals recorded."])].join("\n");
}
