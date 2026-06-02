# Reference Cohort Coverage Report

รายงานนี้สรุปความพร้อมของ Reference Cohort โดยเทียบ coverage ของ Python-derived features, cohort summary และ CLAN-Derived Metrics แบบ side-by-side เพื่อใช้ตัดสินใจขั้นถัดไปของข้อมูลอ้างอิง.

รายงานนี้เป็น research readiness artifact สำหรับทีมพัฒนา ไม่ใช่ clinical output และไม่ควรใช้แทนการตีความโดยผู้เชี่ยวชาญ.

## Snapshot

| Metric | Value |
| --- | --- |
| Feature rows | 1961 |
| CLAN rows | 1961 |
| Coverage cells | 49 |
| Cohort-ready cells | 48 |
| Rows without age band | 1 |
| QC missing_age_months rows | 0 |
| QC known_unresolved_age_months rows | 1 |

## Coverage Status

| coverage_status | cell_count |
| --- | --- |
| low_n | 20 |
| not_cohort_ready | 1 |
| ok | 28 |

## Task and Group Coverage

| task_type | group | coverage_status | cell_count |
| --- | --- | --- | --- |
| narrative | SLI | low_n | 6 |
| narrative | SLI | ok | 1 |
| narrative | TD | low_n | 2 |
| narrative | TD | not_cohort_ready | 1 |
| narrative | TD | ok | 6 |
| picture_description | SLI | low_n | 1 |
| picture_description | TD | low_n | 1 |
| toyplay | ASD | low_n | 5 |
| toyplay | ASD | ok | 3 |
| toyplay | DD | low_n | 4 |
| toyplay | HL | ok | 3 |
| toyplay | LT | ok | 6 |
| toyplay | NH | ok | 3 |
| toyplay | TD | low_n | 1 |
| toyplay | TD | ok | 6 |

## Cells Needing Attention

| age_band_12mo | task_type | group | feature_rows | cohort_n | clan_rows | clan_coverage_status | coverage_status | triage_bucket | triage_action | phase2_recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 108-119 | narrative | SLI | 15 | 15 | 15 | matched | low_n | candidate_gillam | Use Gillam-style narrative additions only if the next data round targets narrative SLI/TD gaps. | Prioritize Gillam to strengthen narrative SLI and TD school-age cells. |
| 120-131 | narrative | SLI | 4 | 4 | 4 | matched | low_n | candidate_gillam | Use Gillam-style narrative additions only if the next data round targets narrative SLI/TD gaps. | Prioritize Gillam to strengthen narrative SLI and TD school-age cells. |
| 120-131 | narrative | TD | 17 | 17 | 17 | matched | low_n | candidate_gillam | Use Gillam-style narrative additions only if the next data round targets narrative SLI/TD gaps. | Add matched Phase 2 data or keep this cell low-confidence. |
| 132-143 | narrative | TD | 17 | 17 | 17 | matched | low_n | candidate_gillam | Use Gillam-style narrative additions only if the next data round targets narrative SLI/TD gaps. | Add matched Phase 2 data or keep this cell low-confidence. |
| 48-59 | narrative | SLI | 11 | 11 | 11 | matched | low_n | candidate_gillam | Use Gillam-style narrative additions only if the next data round targets narrative SLI/TD gaps. | Prioritize Gillam to strengthen narrative SLI and TD school-age cells. |
| 60-71 | narrative | SLI | 13 | 13 | 13 | matched | low_n | candidate_gillam | Use Gillam-style narrative additions only if the next data round targets narrative SLI/TD gaps. | Prioritize Gillam to strengthen narrative SLI and TD school-age cells. |
| 72-83 | narrative | SLI | 13 | 13 | 13 | matched | low_n | candidate_gillam | Use Gillam-style narrative additions only if the next data round targets narrative SLI/TD gaps. | Prioritize Gillam to strengthen narrative SLI and TD school-age cells. |
| 84-95 | narrative | SLI | 19 | 19 | 19 | matched | low_n | candidate_gillam | Use Gillam-style narrative additions only if the next data round targets narrative SLI/TD gaps. | Prioritize Gillam to strengthen narrative SLI and TD school-age cells. |
| 36-47 | picture_description | SLI | 17 | 17 | 17 | matched | low_n | defer_or_keep_low_confidence | Keep this cell low-confidence unless a clearly matched corpus is selected. | Add matched Phase 2 data or keep this cell low-confidence. |
| 36-47 | picture_description | TD | 17 | 17 | 17 | matched | low_n | defer_or_keep_low_confidence | Keep this cell low-confidence unless a clearly matched corpus is selected. | Add matched Phase 2 data or keep this cell low-confidence. |
| 108-119 | toyplay | ASD | 4 | 4 | 4 | matched | low_n | candidate_rollins_or_asd_addon | Consider an ASD toyplay add-on such as Rollins-like material, but keep low-confidence cells separated. | Prioritize Rollins only as a small ASD add-on; keep low-confidence cells separated. |
| 156-167 | toyplay | TD | 7 | 7 | 7 | matched | low_n | defer_or_keep_low_confidence | Keep this cell low-confidence unless a clearly matched corpus is selected. | Add matched Phase 2 data or keep this cell low-confidence. |
| 24-35 | toyplay | ASD | 10 | 10 | 10 | matched | low_n | candidate_rollins_or_asd_addon | Consider an ASD toyplay add-on such as Rollins-like material, but keep low-confidence cells separated. | Prioritize Rollins only as a small ASD add-on; keep low-confidence cells separated. |
| 36-47 | toyplay | DD | 3 | 3 | 3 | matched | low_n | no_direct_phase2_fill | No direct Phase 2 corpus fills this DD toyplay cell; retain low-confidence labeling. | No Phase 2 corpus directly fills DD toyplay; keep this cell low-confidence. |
| 48-59 | toyplay | DD | 7 | 7 | 7 | matched | low_n | no_direct_phase2_fill | No direct Phase 2 corpus fills this DD toyplay cell; retain low-confidence labeling. | No Phase 2 corpus directly fills DD toyplay; keep this cell low-confidence. |
| 60-71 | toyplay | DD | 5 | 5 | 5 | matched | low_n | no_direct_phase2_fill | No direct Phase 2 corpus fills this DD toyplay cell; retain low-confidence labeling. | No Phase 2 corpus directly fills DD toyplay; keep this cell low-confidence. |
| 72-83 | toyplay | ASD | 16 | 16 | 16 | matched | low_n | candidate_rollins_or_asd_addon | Consider an ASD toyplay add-on such as Rollins-like material, but keep low-confidence cells separated. | Prioritize Rollins only as a small ASD add-on; keep low-confidence cells separated. |
| 72-83 | toyplay | DD | 1 | 1 | 1 | matched | low_n | no_direct_phase2_fill | No direct Phase 2 corpus fills this DD toyplay cell; retain low-confidence labeling. | No Phase 2 corpus directly fills DD toyplay; keep this cell low-confidence. |
| 84-95 | toyplay | ASD | 14 | 14 | 14 | matched | low_n | candidate_rollins_or_asd_addon | Consider an ASD toyplay add-on such as Rollins-like material, but keep low-confidence cells separated. | Prioritize Rollins only as a small ASD add-on; keep low-confidence cells separated. |
| 96-107 | toyplay | ASD | 11 | 11 | 11 | matched | low_n | candidate_rollins_or_asd_addon | Consider an ASD toyplay add-on such as Rollins-like material, but keep low-confidence cells separated. | Prioritize Rollins only as a small ASD add-on; keep low-confidence cells separated. |
| UNASSIGNED | narrative | TD | 1 | 0 | 1 | matched | not_cohort_ready | known_exclusion | Keep this row out of age-band cohort summaries unless a new unambiguous official age source is added. | Keep the known unresolved age row excluded unless a new unambiguous official age source is added. |

## Triage Decision

| triage_bucket | cell_count | row_gap_to_20 | triage_action |
| --- | --- | --- | --- |
| no_direct_phase2_fill | 4 | 64 | No direct Phase 2 corpus fills this DD toyplay cell; retain low-confidence labeling. |
| candidate_gillam | 8 | 51 | Use Gillam-style narrative additions only if the next data round targets narrative SLI/TD gaps. |
| candidate_rollins_or_asd_addon | 5 | 45 | Consider an ASD toyplay add-on such as Rollins-like material, but keep low-confidence cells separated. |
| known_exclusion | 1 | 20 | Keep this row out of age-band cohort summaries unless a new unambiguous official age source is added. |
| defer_or_keep_low_confidence | 3 | 19 | Keep this cell low-confidence unless a clearly matched corpus is selected. |

## Phase 2 Download Guidance

| Recommendation | cell_count | row_gap_to_20 |
| --- | --- | --- |
| No Phase 2 corpus directly fills DD toyplay; keep this cell low-confidence. | 4 | 64 |
| Prioritize Gillam to strengthen narrative SLI and TD school-age cells. | 6 | 45 |
| Prioritize Rollins only as a small ASD add-on; keep low-confidence cells separated. | 5 | 45 |
| Add matched Phase 2 data or keep this cell low-confidence. | 5 | 25 |
| Keep the known unresolved age row excluded unless a new unambiguous official age source is added. | 1 | 20 |

## Notes

- `ok` หมายถึง cell มี cohort summary อย่างน้อย 20 rows และมี CLAN-Derived Metrics match กับ feature rows.
- `low_n` หมายถึง cell มี cohort summary แล้วแต่ยังต่ำกว่า threshold 20 rows ตามนโยบายเดิมของ Reference Cohort.
- `not_cohort_ready` หมายถึง row ยังไม่พร้อมเข้า cohort summary เช่นไม่มี age band, task type หรือ group.
- `known_exclusion` หมายถึง row ที่มีนโยบาย exclusion ชัดเจนแล้ว และไม่ควรถูกเติม metadata จาก source ที่ไม่ตรงกัน.
- `missing_clan`, `partial_clan` และ `clan_only` ใช้ตรวจความตรงกันของ CLAN-Derived Metrics กับ Python-derived features.
