# CLAN Batch Runbook

This runbook covers CLAN Batch Pipeline v1 for curated English child CHAT
transcripts. The pipeline creates an audit manifest and QC summary for planned
or executed CLAN commands. KIDEVAL output can be parsed into a separate
CLAN-Derived Metrics table, but it does not overwrite the Python-derived
Reference Cohort CSVs.

## Inputs

- `data/manifests/english_child_transcript_manifest.csv`
- Only rows where `analysis_ready=True` are included.
- CLAN receives `curated_path` files, not the raw TalkBank mirror.

## Commands

The v1 command plan is:

- `check`: one run per transcript file
- `kideval`: one run per transcript file
- `mlu`: one run per corpus batch
- `freq`: one run per corpus batch
- `vocd`: one run per corpus batch

The script checks for these commands on `PATH` before execution. If a command
is unavailable, it records `clan_unavailable` and continues. You can also pass
`--clan-bin-dir` to use an explicit UnixCLAN binary directory without changing
your global shell `PATH`.

KIDEVAL selects the child speaker with `+t*CHI` rather than relying on the
default `+t#Target_Child` role filter. Some TalkBank corpora use the role
`Child` in `@ID` while still providing the canonical `*CHI` child tier; using
the tier keeps CLAN-Derived Metrics consistent across analysis-ready
transcripts without rewriting curated CHAT files.

## Install Verification

Install CLAN manually from the official TalkBank installer, then confirm the
required command-line programs are visible:

```bash
command -v check
command -v kideval
command -v mlu
command -v freq
command -v vocd
```

If any command is missing, update your shell `PATH` before executing the batch.
On macOS, if CLAN.app is installed but command-line tools are not on `PATH`,
download TalkBank UnixCLAN and point the runner at its `unix/bin` directory:

```bash
python scripts/run_clan_batch.py --clan-bin-dir /path/to/unix-clan/unix/bin
```

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

For a small KIDEVAL smoke plan:

```bash
python scripts/run_clan_batch.py --commands check,kideval --corpus Eigsti --max-files 1
```

## Incremental Corpus Execution

When adding one new corpus such as `Gillam`, run the corpus-limited CLAN batch
with `--append` so the new rows are merged into the existing CLAN run manifest:

```bash
python scripts/run_clan_batch.py \
  --execute \
  --commands check,kideval \
  --corpus Gillam \
  --append
```

If CLAN binaries are not on the shell `PATH`, add `--clan-bin-dir` as in the
smoke examples below. Do not run a corpus-limited batch and then parse KIDEVAL
without `--append`; doing so replaces the run manifest with only that corpus
and makes the CLAN-Derived Metrics table incomplete.

## Execute

Install CLAN and make sure `check`, `mlu`, `freq`, `vocd`, and `kideval` are
available on `PATH`, or provide `--clan-bin-dir`, then run:

```bash
python scripts/run_clan_batch.py --execute
```

Raw CLAN stdout, stderr, KIDEVAL `.kideval.xls` artifacts, and corpus file
lists are written under:

- `data/clan/raw_outputs/`

That directory is ignored by git because the files are regenerable command
outputs from protected corpus material.

Run a small smoke execution before the full batch:

```bash
python scripts/run_clan_batch.py \
  --execute \
  --commands check,kideval \
  --corpus Eigsti \
  --max-files 1 \
  --clan-bin-dir /path/to/unix-clan/unix/bin
```

When the smoke output parses correctly, run the full batch:

```bash
python scripts/run_clan_batch.py --execute
```

## KIDEVAL Parser

Parse completed `kideval` jobs into a separate CLAN-Derived Metrics table:

```bash
python scripts/parse_clan_kideval.py
```

Tracked outputs:

- `data/reference/english_child_clan_features.csv`
- `data/reference/english_child_clan_features_qc.csv`

The parser reads `command=kideval,status=completed` rows from
`data/manifests/english_child_clan_run_manifest.csv` and prefers
`artifact_path` when present. If CLAN has not been run successfully yet, the
feature table is empty and the QC file records `no_completed_kideval_jobs`.

UnixCLAN currently runs `check` and `kideval` through stdin in this pipeline.
That avoids a filename-argument parsing issue observed with the macOS UnixCLAN
archive and makes KIDEVAL emit a per-file `pipeout.kideval.xls`, which the
runner renames to the job-specific `artifact_path`.

The KIDEVAL command recorded in the run manifest should look like:

```bash
kideval +t*CHI -leng < data/curated/english_child_transcripts/.../file.cha
```

This v1 parser is KIDEVAL-first. `MLU`, `FREQ`, and `VOCD` raw outputs remain
audit outputs until their formats are reviewed separately. Parsed KIDEVAL rows
can be used by the Reference Comparison API as a separate
`clan_metric_comparisons` section when matched cohort data is ready. The
therapist UI does not display this section yet.

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
