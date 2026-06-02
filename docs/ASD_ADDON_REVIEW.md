# ASD Add-on Review

This research intake report combines the ASD Add-on Candidate Matrix, Reference Cohort coverage, and source-exhaustion audit results before any raw ASDBank download.

It is not a clinical output, access approval, or reason to relax Reference Cohort policy.

## Review Status

| review_status | candidate_count |
| --- | --- |
| blocked_known_limitation | 4 |
| keep_low_confidence | 1 |
| needs_access_and_task_review | 1 |
| no_official_refresh_available | 1 |

## Candidate Actions

| candidate_corpus | matrix_decision | review_status | expected_gap_cells | source_audit_summary | official_refresh_status | recommended_next_action |
| --- | --- | --- | --- | --- | --- | --- |
| AAC | review_access_and_task_fit | needs_access_and_task_review | ASD_toyplay_low_n_24_to_119_months |  |  | Confirm project-owner access eligibility and decide whether AAC intervention samples belong in a separate Reference Cohort task before any download. |
| Eigsti | already_ingested_or_known_limitation | blocked_known_limitation | ASD_toyplay_low_n_72_to_83_months |  |  | Do not redownload for current ASD toyplay gaps unless official metadata or the candidate matrix changes. |
| Flusberg | already_ingested_or_known_limitation | blocked_known_limitation | ASD_toyplay_low_n_72_to_119_months |  |  | Do not redownload for current ASD toyplay gaps unless official metadata or the candidate matrix changes. |
| NYU-Emerson | review_source_refresh | no_official_refresh_available | ASD_toyplay_36_to_71_months |  | no_official_refresh_available | Official NYU-Emerson transcript count matches local transcript count; do not download new NYU-Emerson data in this round. |
| Nadig | already_ingested_or_known_limitation | blocked_known_limitation | ASD_toyplay_low_n_72_to_83_months |  |  | Do not redownload for current ASD toyplay gaps unless official metadata or the candidate matrix changes. |
| QuigleyMcNally | known_task_mismatch | blocked_known_limitation | no_current_child_speech_reference_gap |  |  | Do not redownload for current ASD toyplay gaps unless official metadata or the candidate matrix changes. |
| Rollins | source_audit_then_keep_low_confidence | keep_low_confidence | ASD_toyplay_low_n_24_to_35_months | no_local_target_source_keep_low_confidence:4;policy_exhausted_keep_low_confidence:1 |  | Keep Rollins ASD toyplay cells low-confidence because source-exhaustion audit found no additional analysis-ready local rows under current policy. |

## Notes

- `download_candidate` is the only status that can trigger a manual TalkBank download.
- `needs_access_and_task_review` requires project-owner eligibility review before any AAC intake.
- `needs_official_refresh_check` requires checking whether the official package has newer shareable transcripts.
- `no_official_refresh_available` means the current official transcript count already matches local intake.
- Raw TalkBank content must remain separate from user uploads and public app content.
