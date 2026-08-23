"use client";

import type { SpeakerMapping, SpeakerMappingEntry, TranscriptLine } from "@/lib/workflow";

const CHAT_CODES = ["CHI", "THER", "OTH"] as const;
const PARTICIPANT_ROLES = ["target_child", "therapist", "other"] as const;

type ChatCode = typeof CHAT_CODES[number];
type ParticipantRole = typeof PARTICIPANT_ROLES[number];

export type SpeakerMappingPanelProps = {
  mapping: SpeakerMapping;
  lines: TranscriptLine[];
  dirty: boolean;
  busy: boolean;
  onChange: (mapping: SpeakerMapping) => void;
  onSave: () => void;
  onConfirm: () => void;
};

/**
 * Determines whether the client-side mapping is safe to submit. The service
 * repeats these checks before persisting or confirming a mapping.
 */
export function isSpeakerMappingComplete(mapping: SpeakerMapping): boolean {
  if (mapping.entries.length === 0 || mapping.entries.length > 3) return false;

  const codes = mapping.entries.map((entry) => entry.confirmed_chat_code);
  if (codes.some((code) => !isChatCode(code)) || new Set(codes).size !== codes.length) return false;

  const roles = mapping.entries.map((entry) => entry.participant_role);
  if (roles.some((role) => !isParticipantRole(role))) return false;

  if (mapping.entries.filter((entry) => (
    entry.confirmed_chat_code === "CHI" && entry.participant_role === "target_child"
  )).length !== 1) return false;

  return mapping.entries.every((entry) => hasExactReviewedUtteranceSet(entry));
}

export function SpeakerMappingPanel({
  mapping,
  lines,
  dirty,
  busy,
  onChange,
  onSave,
  onConfirm,
}: SpeakerMappingPanelProps) {
  const linesById = new Map(lines.map((line) => [line.lineId, line]));
  const complete = isSpeakerMappingComplete(mapping);
  const issueText = mapping.issue_message?.trim() || mapping.issue_code?.trim();
  const blockedByIssue = mapping.effective_status === "stale" || Boolean(issueText);
  const controlsDisabled = busy || blockedByIssue;
  const canSave = complete && dirty && !busy && !blockedByIssue;
  const canConfirm = complete
    && mapping.persisted
    && !dirty
    && mapping.effective_status === "draft"
    && !busy
    && !blockedByIssue;

  const updateEntry = (entryIndex: number, patch: Partial<Pick<SpeakerMappingEntry,
    "confirmed_chat_code" | "participant_role" | "reviewed_utterance_ids"
  >>) => {
    onChange({
      ...mapping,
      entries: mapping.entries.map((entry, index) => (
        index === entryIndex ? { ...entry, ...patch } : entry
      )),
    });
  };

  const updateReviewedUtterance = (entryIndex: number, utteranceId: string, checked: boolean) => {
    const entry = mapping.entries[entryIndex];
    if (!entry || !entry.affected_utterance_ids.includes(utteranceId)) return;

    const selected = new Set(entry.reviewed_utterance_ids);
    if (checked) selected.add(utteranceId);
    else selected.delete(utteranceId);

    const reviewedUtteranceIds = uniqueIds(entry.affected_utterance_ids)
      .filter((id) => selected.has(id));
    updateEntry(entryIndex, { reviewed_utterance_ids: reviewedUtteranceIds });
  };

  return (
    <section
      className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-4 text-[color:var(--color-text-strong)] sm:p-5"
      aria-labelledby="speaker-mapping-title"
    >
      <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        <div>
          <h2 id="speaker-mapping-title" className="text-base font-semibold">Confirm temporary speakers</h2>
          <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
            Select a CHAT code, participant role, and review every affected utterance for each temporary speaker.
          </p>
        </div>
        <p className="shrink-0 text-sm font-medium text-[color:var(--color-text-muted)]" role="status" aria-live="polite">
          {complete ? "Speaker mapping is complete." : "Select a CHAT code, participant role, and review every affected utterance."}
        </p>
      </div>

      {issueText ? (
        <div
          className="mt-4 rounded-[var(--radius-card)] border border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] px-3 py-2 text-sm font-medium text-[color:var(--color-danger-text)]"
          role="alert"
          aria-live="assertive"
        >
          {issueText}
        </div>
      ) : null}

      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        {mapping.entries.map((entry, entryIndex) => {
          const temporarySpeakerId = entry.temporary_speaker_id;
          const speakerLabel = entry.source_speaker_label?.trim() || temporarySpeakerId;
          const descriptionId = `speaker-mapping-description-${entryIndex}`;
          return (
            <fieldset
              key={temporarySpeakerId}
              disabled={controlsDisabled}
              className="min-w-0 rounded-[var(--radius-card)] border border-[color:var(--color-border)] p-3 sm:p-4"
            >
              <legend className="px-1 text-sm font-semibold text-[color:var(--color-text-strong)]">{speakerLabel}</legend>
              <p id={descriptionId} className="text-sm text-[color:var(--color-text-muted)]">
                Temporary speaker ID: {temporarySpeakerId}
              </p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <label className="grid gap-1.5 text-sm font-medium">
                  <span>CHAT code</span>
                  <select
                    aria-label={`CHAT code for ${temporarySpeakerId}`}
                    aria-describedby={descriptionId}
                    value={entry.confirmed_chat_code ?? ""}
                    onChange={(event) => updateEntry(entryIndex, {
                      confirmed_chat_code: isChatCode(event.target.value) ? event.target.value : null,
                    })}
                    className={fieldClassName}
                  >
                    <option value="">Choose a code</option>
                    <option value="CHI">CHI</option>
                    <option value="THER">THER</option>
                    <option value="OTH">OTH</option>
                  </select>
                </label>
                <label className="grid gap-1.5 text-sm font-medium">
                  <span>Participant role</span>
                  <select
                    aria-label={`Participant role for ${temporarySpeakerId}`}
                    aria-describedby={descriptionId}
                    value={entry.participant_role ?? ""}
                    onChange={(event) => updateEntry(entryIndex, {
                      participant_role: isParticipantRole(event.target.value) ? event.target.value : null,
                    })}
                    className={fieldClassName}
                  >
                    <option value="">Choose a role</option>
                    <option value="target_child">Target child</option>
                    <option value="therapist">Therapist</option>
                    <option value="other">Other</option>
                  </select>
                </label>
              </div>
              <div className="mt-4 space-y-3">
                <h3 className="text-sm font-semibold">Review affected utterances</h3>
                {uniqueIds(entry.affected_utterance_ids).map((utteranceId) => {
                  const line = linesById.get(utteranceId);
                  const reviewed = entry.reviewed_utterance_ids.includes(utteranceId);
                  return (
                    <label
                      key={utteranceId}
                      className="flex min-h-11 cursor-pointer items-start gap-3 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 text-sm disabled:cursor-not-allowed"
                    >
                      <input
                        type="checkbox"
                        aria-label={`Reviewed utterance ${utteranceId} for ${temporarySpeakerId}`}
                        checked={reviewed}
                        onChange={(event) => updateReviewedUtterance(entryIndex, utteranceId, event.target.checked)}
                        className="mt-0.5 h-5 w-5 shrink-0 rounded border-[color:var(--color-border-strong)] text-[color:var(--color-accent)] outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--color-focus-ring)] focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]"
                      />
                      <span className="min-w-0">
                        <span className="block font-medium">Utterance {utteranceId}</span>
                        {line ? <ReviewedUtterance line={line} /> : (
                          <span className="mt-1 block text-[color:var(--color-text-muted)]">
                            Utterance {utteranceId} is unavailable in the current transcript.
                          </span>
                        )}
                      </span>
                    </label>
                  );
                })}
              </div>
            </fieldset>
          );
        })}
      </div>

      <div className="mt-5 flex flex-col gap-3 border-t border-[color:var(--color-border)] pt-4 sm:flex-row sm:justify-end">
        <button type="button" className={secondaryButtonClassName} disabled={!canSave} onClick={onSave}>
          Save speaker mapping draft
        </button>
        <button type="button" className={primaryButtonClassName} disabled={!canConfirm} onClick={onConfirm}>
          Confirm speaker mapping
        </button>
      </div>
    </section>
  );
}

function ReviewedUtterance({ line }: { line: TranscriptLine }) {
  const timestamp = line.startMs !== undefined && line.endMs !== undefined
    ? `${formatTimestamp(line.startMs)} – ${formatTimestamp(line.endMs)}`
    : "Timestamp unavailable";
  return (
    <>
      <span className="mt-1 block break-words text-[color:var(--color-text-strong)]">{line.text}</span>
      <span className="mt-1 block text-xs text-[color:var(--color-text-muted)]">{timestamp}</span>
    </>
  );
}

function hasExactReviewedUtteranceSet(entry: SpeakerMappingEntry): boolean {
  const affected = uniqueIds(entry.affected_utterance_ids);
  const reviewed = uniqueIds(entry.reviewed_utterance_ids);
  return affected.length === entry.affected_utterance_ids.length
    && reviewed.length === entry.reviewed_utterance_ids.length
    && affected.length === reviewed.length
    && affected.every((id) => reviewed.includes(id));
}

function uniqueIds(ids: string[]) {
  return [...new Set(ids)];
}

function isChatCode(value: unknown): value is ChatCode {
  return typeof value === "string" && CHAT_CODES.includes(value as ChatCode);
}

function isParticipantRole(value: unknown): value is ParticipantRole {
  return typeof value === "string" && PARTICIPANT_ROLES.includes(value as ParticipantRole);
}

function formatTimestamp(milliseconds: number) {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  const remainder = Math.max(0, milliseconds % 1000);
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}.${String(remainder).padStart(3, "0")}`;
}

const fieldClassName = "min-h-11 w-full rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-3 text-sm text-[color:var(--color-text-strong)] outline-none transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--color-focus-ring)] focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)] disabled:cursor-not-allowed disabled:bg-[color:var(--color-surface-muted)] disabled:text-[color:var(--color-text-muted)]";
const secondaryButtonClassName = "inline-flex min-h-11 items-center justify-center rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-4 py-2 text-sm font-semibold text-[color:var(--color-text-strong)] transition hover:border-[color:var(--color-accent-strong)] hover:bg-[color:var(--color-accent-soft)] outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--color-focus-ring)] focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)] disabled:cursor-not-allowed disabled:bg-[color:var(--color-surface-muted)] disabled:text-[color:var(--color-text-muted)]";
const primaryButtonClassName = "inline-flex min-h-11 items-center justify-center rounded-[var(--radius-card)] bg-[color:var(--color-accent)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[color:var(--color-accent-strong)] outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--color-focus-ring)] focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)] disabled:cursor-not-allowed disabled:bg-[color:var(--color-border-strong)] disabled:text-[color:var(--color-text-muted)]";
