"use client";

import { useEffect, useMemo, useState } from "react";
import { GitMerge, ShieldCheck } from "lucide-react";

import { PrimaryActionButton } from "@/components/workbench-ui";
import type { SpeakerMappingEntry, SpeakerMappingResponse } from "@/features/sessions/services/session-workflow-service";

export type { SpeakerMappingEntry, SpeakerMappingResponse } from "@/features/sessions/services/session-workflow-service";

export type SpeakerMappingPanelProps = {
  mapping: SpeakerMappingResponse;
  busy?: boolean;
  onSaveDraft: (entries: SpeakerMappingEntry[]) => void;
  onConfirm: () => void;
};

const ROLE_OPTIONS = [
  ["unknown", "Unknown"],
  ["target_child", "Target child"],
  ["therapist", "Therapist"],
  ["other_participant", "Other participant"],
  ["non_target", "Non-target"],
] as const;

const DISPOSITION_OPTIONS = [
  ["unknown", "Unknown"],
  ["target", "Target speaker"],
  ["non_target", "Non-target speaker"],
  ["merged", "Merged duplicate"],
] as const;

const CHAT_CODE_OPTIONS = ["", "CHI", "THE", "INV", "PAR", "UNK"] as const;

function hasReviewedEveryAffectedSegment(entry: SpeakerMappingEntry): boolean {
  const reviewedIds = new Set(entry.reviewed_utterance_ids);
  return entry.affected_utterance_ids.every((utteranceId) => reviewedIds.has(utteranceId));
}

function entryReadyForConfirm(entry: SpeakerMappingEntry, allEntries: SpeakerMappingEntry[]): boolean {
  if (!hasReviewedEveryAffectedSegment(entry)) return false;

  if (entry.disposition === "merged") {
    return Boolean(
      entry.merged_into_temporary_speaker_id
      && entry.merged_into_temporary_speaker_id !== entry.temporary_speaker_id
      && allEntries.some((candidate) => (
        candidate.temporary_speaker_id === entry.merged_into_temporary_speaker_id
        && candidate.disposition !== "merged"
      )),
    );
  }

  return Boolean(
    entry.confirmed_chat_code
    && entry.participant_role !== "unknown"
    && entry.disposition !== "unknown"
  );
}

function hasRole(entries: SpeakerMappingEntry[], role: string, code: string): boolean {
  return entries.some((entry) => (
    entry.disposition !== "merged"
    && entry.participant_role === role
    && entry.confirmed_chat_code === code
  ));
}

export function SpeakerMappingPanel({
  mapping,
  busy = false,
  onSaveDraft,
  onConfirm,
}: SpeakerMappingPanelProps) {
  const [entries, setEntries] = useState(mapping.entries);

  useEffect(() => {
    setEntries(mapping.entries);
  }, [mapping]);

  const blockingIssues = mapping.issues.filter((issue) => issue.blocking || issue.severity === "error");
  const canConfirm = useMemo(() => (
    mapping.status !== "stale"
    && mapping.mapping_version > 0
    && blockingIssues.length === 0
    && entries.length > 0
    && entries.every((entry) => entryReadyForConfirm(entry, entries))
    && hasRole(entries, "target_child", "CHI")
    && hasRole(entries, "therapist", "THE")
  ), [blockingIssues.length, entries, mapping.mapping_version, mapping.status]);

  function updateEntry(
    temporarySpeakerId: string,
    patch: Partial<SpeakerMappingEntry>,
  ) {
    setEntries((current) => current.map((entry) => {
      if (entry.temporary_speaker_id !== temporarySpeakerId) return entry;

      const nextEntry = { ...entry, ...patch };
      if (patch.disposition && patch.disposition !== "merged") {
        nextEntry.merged_into_temporary_speaker_id = null;
      }
      if (
        patch.disposition === "merged"
        && nextEntry.merged_into_temporary_speaker_id === temporarySpeakerId
      ) {
        nextEntry.merged_into_temporary_speaker_id = null;
      }
      return nextEntry;
    }));
  }

  function updateReviewedSegment(
    temporarySpeakerId: string,
    utteranceId: string,
    reviewed: boolean,
  ) {
    setEntries((current) => current.map((entry) => {
      if (entry.temporary_speaker_id !== temporarySpeakerId) return entry;

      const reviewedIds = new Set(entry.reviewed_utterance_ids);
      if (reviewed) reviewedIds.add(utteranceId);
      else reviewedIds.delete(utteranceId);

      return {
        ...entry,
        reviewed_utterance_ids: entry.affected_utterance_ids.filter((candidate) => reviewedIds.has(candidate)),
      };
    }));
  }

  return (
    <section className="rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] p-4" aria-labelledby="speaker-mapping-heading">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <GitMerge size={18} aria-hidden="true" />
            <h2 id="speaker-mapping-heading" className="text-base font-semibold text-ink">Speaker mapping</h2>
          </div>
          <p className="mt-1 text-sm text-muted">
            Confirm temporary ASR speakers before QA, attestation, export, and role-dependent features.
          </p>
        </div>
        <div className="text-sm text-muted">
          v{mapping.mapping_version} · transcript v{mapping.transcript_version} · {mapping.status}
        </div>
      </div>

      {blockingIssues.length > 0 ? (
        <div className="mt-4 rounded-[var(--radius-card)] border border-red-200 bg-red-50 p-3 text-sm text-red-950" role="alert">
          <p className="font-semibold">Mapping blockers</p>
          <ul className="mt-2 space-y-1">
            {blockingIssues.map((issue) => (
              <li key={`${issue.code}-${issue.message}`}>
                <span className="font-semibold">{issue.code}</span>: {issue.message}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-4 space-y-3">
        {entries.map((entry) => (
          <article
            key={entry.temporary_speaker_id}
            data-testid={`speaker-mapping-${entry.temporary_speaker_id}`}
            className="rounded-[var(--radius-card)] border border-line bg-white p-3"
          >
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <h3 className="font-semibold text-ink">{entry.temporary_speaker_id}</h3>
                <p className="mt-1 text-sm text-muted">
                  Raw label: <span className="font-medium text-ink">{entry.source_speaker_label ?? "unknown"}</span>
                  {" · "}
                  Provider: <span className="font-medium text-ink">{entry.source_provider ?? "unavailable"}</span>
                </p>
                <p className="mt-1 text-xs text-muted">
                  Segments: {entry.affected_utterance_ids.join(", ") || "none"}
                </p>
                {entry.affected_utterance_ids.length > 0 ? (
                  <fieldset className="mt-3 space-y-2">
                    <legend className="text-xs font-semibold uppercase tracking-wide text-muted">
                      Reviewed segments for {entry.temporary_speaker_id}
                    </legend>
                    {entry.affected_utterance_ids.map((utteranceId) => (
                      <label key={utteranceId} className="flex items-center gap-2 text-sm text-ink">
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-line"
                          checked={entry.reviewed_utterance_ids.includes(utteranceId)}
                          onChange={(event) => updateReviewedSegment(
                            entry.temporary_speaker_id,
                            utteranceId,
                            event.target.checked,
                          )}
                        />
                        Reviewed segment {utteranceId} for {entry.temporary_speaker_id}
                      </label>
                    ))}
                  </fieldset>
                ) : null}
              </div>
              <div className="grid gap-2 sm:grid-cols-3 md:min-w-[520px]">
                <label className="text-xs font-semibold uppercase tracking-wide text-muted">
                  CHAT code for {entry.temporary_speaker_id}
                  <select
                    className="mt-1 min-h-10 w-full rounded-[var(--radius-card)] border border-line bg-white px-2 text-sm font-medium text-ink"
                    value={entry.confirmed_chat_code ?? ""}
                    onChange={(event) => updateEntry(entry.temporary_speaker_id, { confirmed_chat_code: event.target.value || null })}
                  >
                    {CHAT_CODE_OPTIONS.map((option) => (
                      <option key={option || "empty"} value={option}>{option || "Select"}</option>
                    ))}
                  </select>
                </label>
                <label className="text-xs font-semibold uppercase tracking-wide text-muted">
                  Role for {entry.temporary_speaker_id}
                  <select
                    className="mt-1 min-h-10 w-full rounded-[var(--radius-card)] border border-line bg-white px-2 text-sm font-medium text-ink"
                    value={entry.participant_role}
                    onChange={(event) => updateEntry(entry.temporary_speaker_id, { participant_role: event.target.value })}
                  >
                    {ROLE_OPTIONS.map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </label>
                <label className="text-xs font-semibold uppercase tracking-wide text-muted">
                  Disposition for {entry.temporary_speaker_id}
                  <select
                    className="mt-1 min-h-10 w-full rounded-[var(--radius-card)] border border-line bg-white px-2 text-sm font-medium text-ink"
                    value={entry.disposition}
                    onChange={(event) => updateEntry(entry.temporary_speaker_id, {
                      disposition: event.target.value as SpeakerMappingEntry["disposition"],
                    })}
                  >
                    {DISPOSITION_OPTIONS.map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </label>
                {entry.disposition === "merged" ? (
                  <label className="text-xs font-semibold uppercase tracking-wide text-muted sm:col-span-3">
                    Merge {entry.temporary_speaker_id} into
                    <select
                      className="mt-1 min-h-10 w-full rounded-[var(--radius-card)] border border-line bg-white px-2 text-sm font-medium text-ink"
                      value={entry.merged_into_temporary_speaker_id ?? ""}
                      onChange={(event) => updateEntry(entry.temporary_speaker_id, {
                        merged_into_temporary_speaker_id: event.target.value || null,
                      })}
                    >
                      <option value="">Select merge target</option>
                      {entries
                        .filter((candidate) => candidate.temporary_speaker_id !== entry.temporary_speaker_id)
                        .map((candidate) => (
                          <option key={candidate.temporary_speaker_id} value={candidate.temporary_speaker_id}>
                            {candidate.temporary_speaker_id}
                          </option>
                        ))}
                    </select>
                  </label>
                ) : null}
              </div>
            </div>
          </article>
        ))}
      </div>

      <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:justify-end">
        <button
          type="button"
          className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-card)] border border-line bg-white px-4 py-2 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-60"
          disabled={busy || mapping.status === "stale"}
          onClick={() => onSaveDraft(entries)}
        >
          Save mapping draft
        </button>
        <PrimaryActionButton
          icon={ShieldCheck}
          disabled={busy || !canConfirm}
          onClick={onConfirm}
        >
          Confirm mapping
        </PrimaryActionButton>
      </div>
    </section>
  );
}
