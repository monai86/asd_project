# Reference Cohort Coverage Report

รายงานนี้สรุปความพร้อมของ Reference Cohort โดยเทียบ coverage ของ Python-derived features, cohort summary และ CLAN-Derived Metrics แบบ side-by-side เพื่อใช้ตัดสินใจขั้นถัดไปของข้อมูลอ้างอิง.

รายงานนี้เป็น research readiness artifact สำหรับทีมพัฒนา ไม่ใช่ clinical output และไม่ควรใช้แทนการตีความโดยผู้เชี่ยวชาญ.

## Snapshot

| Metric | Value |
| --- | --- |
| Feature rows | 1536 |
| CLAN rows | 1536 |
| Coverage cells | 43 |
| Cohort-ready cells | 42 |
| Rows without age band | 1 |
| QC missing_age_months rows | 1 |

## Coverage Status

| coverage_status | cell_count |
| --- | --- |
| low_n | 18 |
| not_cohort_ready | 1 |
| ok | 24 |

## Task and Group Coverage

| task_type | group | coverage_status | cell_count |
| --- | --- | --- | --- |
| narrative | SLI | low_n | 6 |
| narrative | SLI | ok | 1 |
| narrative | TD | low_n | 2 |
| narrative | TD | not_cohort_ready | 1 |
| narrative | TD | ok | 6 |
| toyplay | ASD | low_n | 5 |
| toyplay | ASD | ok | 3 |
| toyplay | DD | low_n | 4 |
| toyplay | HL | ok | 3 |
| toyplay | LT | ok | 4 |
| toyplay | NH | ok | 3 |
| toyplay | TD | low_n | 1 |
| toyplay | TD | ok | 4 |

## Cells Needing Attention

| age_band_12mo | task_type | group | feature_rows | cohort_n | clan_rows | clan_coverage_status | coverage_status | phase2_recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 108-119 | narrative | SLI | 15 | 15 | 15 | matched | low_n | Prioritize Gillam to strengthen narrative SLI and TD school-age cells. |
| 120-131 | narrative | SLI | 4 | 4 | 4 | matched | low_n | Prioritize Gillam to strengthen narrative SLI and TD school-age cells. |
| 120-131 | narrative | TD | 17 | 17 | 17 | matched | low_n | Add matched Phase 2 data or keep this cell low-confidence. |
| 132-143 | narrative | TD | 17 | 17 | 17 | matched | low_n | Add matched Phase 2 data or keep this cell low-confidence. |
| 48-59 | narrative | SLI | 11 | 11 | 11 | matched | low_n | Prioritize Gillam to strengthen narrative SLI and TD school-age cells. |
| 60-71 | narrative | SLI | 13 | 13 | 13 | matched | low_n | Prioritize Gillam to strengthen narrative SLI and TD school-age cells. |
| 72-83 | narrative | SLI | 13 | 13 | 13 | matched | low_n | Prioritize Gillam to strengthen narrative SLI and TD school-age cells. |
| 84-95 | narrative | SLI | 19 | 19 | 19 | matched | low_n | Prioritize Gillam to strengthen narrative SLI and TD school-age cells. |
| 108-119 | toyplay | ASD | 4 | 4 | 4 | matched | low_n | Prioritize Rollins only as a small ASD add-on; keep low-confidence cells separated. |
| 12-23 | toyplay | TD | 3 | 3 | 3 | matched | low_n | Add matched Phase 2 data or keep this cell low-confidence. |
| 24-35 | toyplay | ASD | 10 | 10 | 10 | matched | low_n | Prioritize Rollins only as a small ASD add-on; keep low-confidence cells separated. |
| 36-47 | toyplay | DD | 3 | 3 | 3 | matched | low_n | No Phase 2 corpus directly fills DD toyplay; keep this cell low-confidence. |
| 48-59 | toyplay | DD | 7 | 7 | 7 | matched | low_n | No Phase 2 corpus directly fills DD toyplay; keep this cell low-confidence. |
| 60-71 | toyplay | DD | 5 | 5 | 5 | matched | low_n | No Phase 2 corpus directly fills DD toyplay; keep this cell low-confidence. |
| 72-83 | toyplay | ASD | 16 | 16 | 16 | matched | low_n | Prioritize Rollins only as a small ASD add-on; keep low-confidence cells separated. |
| 72-83 | toyplay | DD | 1 | 1 | 1 | matched | low_n | No Phase 2 corpus directly fills DD toyplay; keep this cell low-confidence. |
| 84-95 | toyplay | ASD | 14 | 14 | 14 | matched | low_n | Prioritize Rollins only as a small ASD add-on; keep low-confidence cells separated. |
| 96-107 | toyplay | ASD | 11 | 11 | 11 | matched | low_n | Prioritize Rollins only as a small ASD add-on; keep low-confidence cells separated. |
| UNASSIGNED | narrative | TD | 1 | 0 | 1 | matched | not_cohort_ready | Resolve missing age metadata before using this row in Reference Cohort summaries. |

## Phase 2 Download Guidance

| Recommendation | cell_count | row_gap_to_20 |
| --- | --- | --- |
| No Phase 2 corpus directly fills DD toyplay; keep this cell low-confidence. | 4 | 64 |
| Prioritize Gillam to strengthen narrative SLI and TD school-age cells. | 6 | 45 |
| Prioritize Rollins only as a small ASD add-on; keep low-confidence cells separated. | 5 | 45 |
| Add matched Phase 2 data or keep this cell low-confidence. | 3 | 23 |
| Resolve missing age metadata before using this row in Reference Cohort summaries. | 1 | 20 |

## Notes

- `ok` หมายถึง cell มี cohort summary อย่างน้อย 20 rows และมี CLAN-Derived Metrics match กับ feature rows.
- `low_n` หมายถึง cell มี cohort summary แล้วแต่ยังต่ำกว่า threshold 20 rows ตามนโยบายเดิมของ Reference Cohort.
- `not_cohort_ready` หมายถึง row ยังไม่พร้อมเข้า cohort summary เช่นไม่มี age band, task type หรือ group.
- `missing_clan`, `partial_clan` และ `clan_only` ใช้ตรวจความตรงกันของ CLAN-Derived Metrics กับ Python-derived features.
