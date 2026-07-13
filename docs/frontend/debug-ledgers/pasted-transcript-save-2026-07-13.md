# Pasted transcript save debug ledger — 2026-07-13

Scope: diagnose the existing `/record?mode=paste` smoke failure without recording request bodies, transcript text, child identifiers, workflow identifiers, raw URLs, query strings, or storage keys.

| Run | Change or boundary | Result | Evidence and implication |
|---|---|---|---|
| 1 | Unchanged `npm run e2e:smoke` in the restricted sandbox | Test application did not run | FastAPI completed application startup, then binding `127.0.0.1:8000` failed with `EPERM`. This is an environment precondition failure and does not establish an application root cause. |
| 2 | Unchanged smoke command with elevated execution requested | No test result | The authorization/tool call was interrupted before Playwright emitted output. No application hypothesis was tested. |
| 3 | Static path trace | Save path identified | `SessionWorkspaceClient.handleTranscriptSubmit` calls case selection/creation, session creation, manual transcript creation, persists the confirmed transcript ID, then calls `router.push`. Its catch branch deliberately does not navigate. Candidate failure boundaries are therefore backend mutation rejection, client-side response handling, or integration-only state/timing. |
| 4 | FastAPI in-process client using the smoke identity and synthetic fixture data | `GET /cases`, `POST /cases`, `POST /cases/{case_id}/sessions`, and `POST /sessions/{session_id}/transcripts/manual` all returned `200` | Disproves a general backend rejection of the authorized pasted-transcript request. It does not yet disprove a browser-only header, origin, or state difference. |
| 5 | Existing focused component characterization for the pasted transcript flow | Passed | With successful case/session/transcript responses, the component persisted the backend IDs and called `router.push`. Disproves a general missing-navigation defect; the existing test mocks the transport and cannot expose an integration-only failure. |
| 6 | Real services ready on `127.0.0.1:8000` and `127.0.0.1:3100`; unchanged Playwright smoke requested | No test result | The browser-launch authorization/tool call was interrupted before Playwright emitted output. No mutation response status was captured. |
| 7 | Real Playwright smoke against the ready in-memory API and Next development server | Pasted transcript save passed in all three flows; one flow passed overall and two failed later on Results | Disproves the historical pasted-transcript save hypothesis in the current worktree. Both remaining failures reached `/results?`; their snapshots showed the indefinite “Analyzing linguistic observations...” branch. |
| 8 | Results call-path trace | Root cause proved | Hydration fetches optional ML evidence once and tolerates a missing result. `SessionResultsView` then treated `featuresExtracted && !mlDecisionSupport` as an active loading job, but no code in that branch starts or polls a job. The false loading branch hid completed features and the report action indefinitely. |
| 9 | Focused regression changed to require completed Results and report drafting when optional ML evidence is absent | Failed before the production change, passed after it | The minimal fix removes only the false loading branch. Existing transcript review, feature extraction, and report readiness gates remain authoritative. |
| 10 | Authoritative Playwright smoke rerun against the real in-memory API and Next server after the fix | `PASS 3`, `FAIL 0` in `18.746s` | Confirms pasted save/navigation, transcript QA and attestation, feature extraction, completed Results, optional evidence handling, report drafting, and diagnostic-language safety all cross the real frontend–backend boundary. |
| 11 | Smoke rerun after replacing raw diagnostic URLs with allowlisted route templates | `PASS 3`, `FAIL 0` in `12.621s` | Confirms the privacy-safe breadcrumb and boolean duplicate-prefix tracker preserve all real workflow coverage without retaining identifiers. |

## Conclusion

The historical save failure no longer reproduces. The current integration failure was downstream and shared by the happy and report-safety flows: completed feature extraction was replaced by a non-operational ML loading screen whenever optional evidence had not yet been generated.

No save-path `ApiError` behavior was changed because persistence succeeded and navigation was reached in every real browser flow. Changing that path would not address the proven failure.

The downstream Results/report regression is fixed and the smoke contract is restored without altering transcript persistence semantics.

The retained timeout breadcrumb records only mutation method, response status, and an allowlisted transcript-persistence route template. Read responses, unrelated mutations, and unrecognized nested routes are ignored; raw workflow identifiers and query strings are never added to the attachment payload.
