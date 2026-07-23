import type { FeatureSignal } from "@/lib/workflow";

type FindingGroupDefinition = {
  id: "language-sample" | "lexical-use" | "interaction" | "speech-intelligibility" | "data-quality";
  label: string;
  description: string;
  caution: string;
};

const findingGroupDefinitions: FindingGroupDefinition[] = [
  {
    id: "language-sample",
    label: "Language sample",
    description: "Utterance length and sample-level descriptive cues.",
    caution: "Interpret alongside sample length and elicitation context.",
  },
  {
    id: "lexical-use",
    label: "Lexical use",
    description: "Word use and vocabulary-diversity cues.",
    caution: "Vocabulary cues depend on the reviewed transcript sample.",
  },
  {
    id: "interaction",
    label: "Interaction",
    description: "Turn-taking, response, and question-use cues.",
    caution: "Review with speaker roles and interaction context.",
  },
  {
    id: "speech-intelligibility",
    label: "Speech / intelligibility",
    description: "Clarity and speech-pattern cues recorded in the sample.",
    caution: "Transcript cues are not a substitute for direct speech assessment.",
  },
  {
    id: "data-quality",
    label: "Data quality",
    description: "Completeness, timing, and input-quality cues.",
    caution: "Resolve material data-quality concerns before report use.",
  },
];

export function FindingsFeatureGroups({ signals }: { signals: FeatureSignal[] }) {
  const groups = findingGroupDefinitions.map((definition) => ({
    ...definition,
    signals: signals.filter((signal) => findingGroupId(signal.featureName) === definition.id),
  }));

  return (
    <section aria-labelledby="clinical-review-summary-title" className="rounded-[var(--radius-shell)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-4 sm:p-5">
      <div>
        <h2 id="clinical-review-summary-title" className="text-xl font-semibold text-[color:var(--color-text-strong)]">Clinical review summary</h2>
        <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">
          Descriptive cues from the current reviewed sample. Open a group only when more detail is needed.
        </p>
      </div>

      <div className="mt-4 divide-y divide-[color:var(--color-border)] overflow-hidden rounded-[var(--radius-panel)] border border-[color:var(--color-border)]">
        {groups.map((group) => (
          <details key={group.id} className="responsive-details bg-[color:var(--color-surface-strong)]" data-testid={`findings-group-${group.id}`}>
            <summary className="grid min-h-16 cursor-pointer grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-4 py-3 marker:content-none">
              <span className="min-w-0">
                <span className="block font-semibold text-[color:var(--color-text-strong)]">{group.label}</span>
                <span className="mt-0.5 block text-sm text-[color:var(--color-text-muted)]">{group.description}</span>
              </span>
              <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${group.signals.length ? "bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]" : "bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-muted)]"}`}>
                {group.signals.length ? `${group.signals.length} available` : "Not available"}
              </span>
            </summary>

            <div className="border-t border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-4">
              <p className="rounded-[var(--radius-card)] bg-[color:var(--color-warning-bg)] px-3 py-2 text-sm text-[color:var(--color-warning-text)]">
                {group.caution}
              </p>
              {group.signals.length ? (
                <div className="mt-3 grid gap-3 lg:grid-cols-2">
                  {group.signals.map((signal) => (
                    <article key={signal.featureName} className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <h3 className="font-semibold text-[color:var(--color-text-strong)]">{signal.displayName}</h3>
                          <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">{signal.description}</p>
                        </div>
                        <span className="shrink-0 rounded-full bg-[color:var(--color-accent-soft)] px-3 py-1 text-sm font-semibold text-[color:var(--color-accent-strong)]">
                          {signal.value}
                        </span>
                      </div>

                      <details className="responsive-details mt-3 rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)]">
                        <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 px-3 text-sm font-semibold text-[color:var(--color-text-strong)]">
                          <span>Evidence and limitations</span>
                          <span aria-hidden="true">›</span>
                        </summary>
                        <div className="space-y-3 border-t border-[color:var(--color-border)] p-3 text-sm text-[color:var(--color-text-muted)]">
                          <div>
                            <h4 className="font-semibold text-[color:var(--color-text-strong)]">Method</h4>
                            <p className="mt-1">{signal.calculationMethod}</p>
                          </div>
                          <div>
                            <h4 className="font-semibold text-[color:var(--color-text-strong)]">Reference evidence</h4>
                            <p className="mt-1">{signal.referenceText}</p>
                          </div>
                          {signal.limitations.length ? (
                            <div>
                              <h4 className="font-semibold text-[color:var(--color-text-strong)]">Limitations</h4>
                              <ul className="mt-1 list-disc space-y-1 pl-5">
                                {signal.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
                              </ul>
                            </div>
                          ) : null}
                          <div>
                            <h4 className="font-semibold text-[color:var(--color-text-strong)]">Clinical interpretation caution</h4>
                            <p className="mt-1">{signal.clinicalInterpretationCaution}</p>
                          </div>
                        </div>
                      </details>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="mt-3 text-sm text-[color:var(--color-text-muted)]">No backend feature is available for this group in the current result.</p>
              )}
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}

function findingGroupId(featureName: string): FindingGroupDefinition["id"] {
  const name = featureName.toLowerCase();
  if (/(unclear|confidence|missing|timing|timestamp|quality|completeness|coverage)/.test(name)) return "data-quality";
  if (/(echolalia|repetition|pronoun|intellig|speech|phon|articul)/.test(name)) return "speech-intelligibility";
  if (/(question|turn|response|speaker|interaction|adult_utterance|child_utterance)/.test(name)) return "interaction";
  if (/(ttr|type_token|lexic|vocab|distinct|different_word|ndw|total_word)/.test(name)) return "lexical-use";
  return "language-sample";
}
