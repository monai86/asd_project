# CLAN Batch Runbook

This runbook covers CLAN Batch Pipeline v1 for curated English child CHAT
transcripts. The pipeline creates an audit manifest and QC summary for planned
or executed CLAN commands. It does not parse CLAN metrics into the Reference
Cohort CSVs.

## Inputs

- `data/manifests/english_child_transcript_manifest.csv`
- Only rows where `analysis_ready=True` are included.
- CLAN receives `curated_path` files, not the raw TalkBank mirror.

## Commands

The v1 command plan is:

- `check`: one run per transcript file
- `mlu`: one run per corpus batch
- `freq`: one run per corpus batch
- `vocd`: one run per corpus batch
- `kideval`: one run per corpus batch

The script checks for these commands on `PATH` before execution. If a command
is unavailable, it records `clan_unavailable` and continues.

## Dry Run

Dry-run is the default and does not call subprocesses or create raw CLAN output
files.

```bash
python scripts/run_clan_batch.py
```

Expected tracked outputs:

- `data/manifests/english_child_clan_run_manifest.csv`
- `data/manifests/english_child_clan_qc_summary.csv`

`status=planned` means the command was available and the job was planned but
not executed.

## Execute

Install CLAN and make sure `check`, `mlu`, `freq`, `vocd`, and `kideval` are
available on `PATH`, then run:

```bash
python scripts/run_clan_batch.py --execute
```

Raw CLAN stdout, stderr, and corpus file lists are written under:

- `data/clan/raw_outputs/`

That directory is ignored by git because the files are regenerable command
outputs from protected corpus material.

## Status Values

- `planned`: dry-run job only; no CLAN subprocess was called.
- `completed`: CLAN subprocess exited with code `0`.
- `failed`: CLAN subprocess exited with a non-zero code; later jobs continue.
- `clan_unavailable`: the CLAN command was missing from `PATH`.
- `skipped`: the job could not run because required curated transcript files
  were missing.

## QC Interpretation

- `pass`: planned or completed.
- `warn`: CLAN unavailable; dependency is missing but the pipeline did not
  crash.
- `fail`: missing curated input or non-zero command exit.

CLAN-Derived Metrics are descriptive research outputs only. They are not
diagnostic norms, diagnoses, validated clinical benchmarks, or clinical
validation evidence.
