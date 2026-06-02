# TalkBank Download Runbook

This runbook covers transcript and sidecar intake for the TalkBank Raw Mirror.
It does not cover raw audio/video media downloads.

## Scope

- Download transcripts and sidecar files for `EllisWeismer`, `ENNI`, and
  `Ambrose`.
- Phase 2 starts with `Gillam` to strengthen narrative SLI/TD reference cells.
- Phase 2 continues with `Nicholas` `HL` and `TD` to strengthen
  hearing-related toyplay reference cells.
- Phase 2 also includes `NewEngland`, `Rescorla`, and `EisenbergGuo` to
  broaden early toyplay, late-talker free-play, and picture-description
  reference cells.
- Do not re-download `Nadig` or `NYU-Emerson`; audit the existing project
  copies into the manifest instead.
- Keep raw downloads under `data/raw/talkbank/**`, which is ignored by git.
- Track only `data/manifests/*.csv`, docs, and scripts.

## Browser Workflow

1. Open Google Chrome to the relevant TalkBank corpus page.
2. If TalkBank asks for authentication, the project owner logs in manually.
   Do not paste credentials into chat or store them in the repository.
3. Download transcripts and available sidecar files only.
4. Skip audio/video media in this phase.
5. Place each corpus download in a dedicated local folder such as:

   ```text
   ~/Downloads/talkbank/EllisWeismer/
   ~/Downloads/talkbank/ENNI/
   ~/Downloads/talkbank/Ambrose/
   ~/Downloads/talkbank/Gillam/
   ~/Downloads/talkbank/Nicholas/
   ```

## Computer Use Assisted Phase 2 Downloads

Use Computer Use only to navigate the browser, click TalkBank download links,
and confirm downloaded files. If TalkBank asks for authentication, the project
owner must log in directly in the browser. Do not paste credentials into chat
or store them in this repository.

For `Gillam`, download transcripts and available sidecar documentation only.
Skip raw audio/video media. Place the downloaded package and sidecars under:

```text
~/Downloads/talkbank/Gillam/
```

For `Nicholas`, download both `HL` and `TD` transcript packages from the
official corpus pages. Media is listed as no longer available, so keep this
phase transcript-and-sidecar only. Place the extracted packages under:

```text
~/Downloads/talkbank/Nicholas/HL/
~/Downloads/talkbank/Nicholas/TD/
```

Before intake, confirm that the folder contains transcript material such as
`.cha` files or a transcript archive plus any corpus page snapshots,
spreadsheets, demographic tables, manuals, or other sidecar files linked from
the corpus page.

For the NewEngland / Rescorla / EisenbergGuo Phase 2 batch, use Computer Use
to open each official corpus page and click `Download transcripts`:

- `NewEngland`: `https://talkbank.org/childes/access/Eng-NA/NewEngland.html`
- `Rescorla`: `https://talkbank.org/childes/access/Clinical-Eng/Rescorla.html`
- `EisenbergGuo`: `https://talkbank.org/childes/access/Clinical-Eng/EisenbergGuo.html`

If the data endpoint returns a TalkBank login page, stop the automated
download and have the project owner authenticate directly in the browser.
After login, retry the same browser links. Keep media folders out of scope and
place the transcript packages under:

```text
~/Downloads/talkbank/NewEngland/
~/Downloads/talkbank/Rescorla/
~/Downloads/talkbank/EisenbergGuo/
```

## Intake Commands

Run one intake command per newly downloaded corpus:

```bash
python3 scripts/talkbank_download_manager.py \
  --bank CHILDES \
  --corpus EllisWeismer \
  --download-date 2026-05-31 \
  --source-dir ~/Downloads/talkbank/EllisWeismer \
  --audit-existing Nadig \
  --audit-existing NYU-Emerson
```

For `ENNI` and `Ambrose`, change `--corpus` and `--source-dir` accordingly.
Use `--dry-run` before copying if you want to preview manifest output without
writing files into the raw mirror. When running multiple corpus intake commands
in sequence, add `--append` on the second and later commands so the file
inventory is merged instead of replaced:

```bash
python3 scripts/talkbank_download_manager.py \
  --bank CHILDES \
  --corpus ENNI \
  --download-date 2026-05-31 \
  --source-dir ~/Downloads/talkbank/ENNI \
  --audit-existing Nadig \
  --audit-existing NYU-Emerson \
  --append
```

For Phase 2 `Gillam`, keep the existing manifest rows and append the new
corpus:

```bash
python3 scripts/talkbank_download_manager.py \
  --bank CHILDES \
  --corpus Gillam \
  --download-date 2026-06-01 \
  --source-dir ~/Downloads/talkbank/Gillam \
  --append
```

Then rebuild derived reference artifacts:

```bash
python3 scripts/curate_english_child_transcripts.py
python3 scripts/build_reference_cohorts.py
python3 scripts/run_clan_batch.py --execute --commands check,kideval --corpus Gillam --append
python3 scripts/parse_clan_kideval.py
python3 scripts/build_reference_coverage_report.py
```

For Phase 2 `Nicholas`, keep both `HL` and `TD` under one source directory and
append the corpus:

```bash
python3 scripts/talkbank_download_manager.py \
  --bank CHILDES \
  --corpus Nicholas \
  --download-date 2026-06-01 \
  --source-dir ~/Downloads/talkbank/Nicholas \
  --append
```

Then rebuild derived reference artifacts and run CLAN for the new corpus:

```bash
python3 scripts/curate_english_child_transcripts.py
python3 scripts/build_reference_cohorts.py
python3 scripts/run_clan_batch.py \
  --execute \
  --commands check,kideval \
  --corpus Nicholas \
  --append \
  --clan-bin-dir ~/Downloads/talkbank/tools/unix-clan/unix-clan/unix/bin
python3 scripts/parse_clan_kideval.py
python3 scripts/build_reference_coverage_report.py
```

The CLAN batch command must use `--append` for corpus-limited execution.
Without it, `english_child_clan_run_manifest.csv` is replaced with only the
selected corpus rows, and the parsed CLAN-Derived Metrics table will no longer
represent the full reference set.

For the NewEngland / Rescorla / EisenbergGuo Phase 2 batch, run one dry-run and
one append intake per corpus. If zip archives are already present in
`~/Downloads`, validate them with `file` and `unzip -l`, extract them to a
temporary source directory, and use that directory as `--source-dir`:

```text
/private/tmp/asd-talkbank-phase2/NewEngland/
/private/tmp/asd-talkbank-phase2/Rescorla/
/private/tmp/asd-talkbank-phase2/EisenbergGuo/
```

```bash
python3 scripts/talkbank_download_manager.py \
  --bank CHILDES \
  --corpus NewEngland \
  --download-date 2026-06-01 \
  --source-dir ~/Downloads/talkbank/NewEngland \
  --append \
  --dry-run

python3 scripts/talkbank_download_manager.py \
  --bank CHILDES \
  --corpus NewEngland \
  --download-date 2026-06-01 \
  --source-dir ~/Downloads/talkbank/NewEngland \
  --append
```

Repeat with `Rescorla` and `EisenbergGuo`, then rebuild and run CLAN
incrementally for each corpus:

```bash
python3 scripts/curate_english_child_transcripts.py
python3 scripts/build_reference_cohorts.py

python3 scripts/run_clan_batch.py \
  --execute \
  --commands check,kideval \
  --corpus NewEngland \
  --append \
  --clan-bin-dir ~/Downloads/talkbank/tools/unix-clan/unix-clan/unix/bin

python3 scripts/run_clan_batch.py \
  --execute \
  --commands check,kideval \
  --corpus Rescorla \
  --append \
  --clan-bin-dir ~/Downloads/talkbank/tools/unix-clan/unix-clan/unix/bin

python3 scripts/run_clan_batch.py \
  --execute \
  --commands check,kideval \
  --corpus EisenbergGuo \
  --append \
  --clan-bin-dir ~/Downloads/talkbank/tools/unix-clan/unix-clan/unix/bin

python3 scripts/parse_clan_kideval.py
python3 scripts/build_reference_coverage_report.py
```

## Metadata Notes

Reference feature rows keep `age_months_source` and
`age_months_source_detail` audit columns. Prefer the child age in the CHAT
`@ID` header. When that header age is absent, the cohort builder may use only
supported official path fallbacks:

- `NewEngland/download_YYYY-MM-DD/{14,20,32,60}/...`
- `Rescorla/download_YYYY-MM-DD/{LT,TD}/{36,48,60,108,156}/...`

The ENNI `TD/B/523.cha` transcript has no child age in its `@ID` header. The
downloaded `0demo.xls` sidecar also contains an ID `523`, but that row maps to
`SLI-A` and corresponds to the separate `SLI/A/0noaudio/523.cha` transcript.
Do not copy the SLI sidecar age onto the TD transcript; keep the TD row out of
age-band Reference Cohort summaries unless an unambiguous official source is
added later. The reference builder records this as `known_unresolved` age
metadata and the coverage report groups it under `known_exclusion`.

After rebuilding coverage, use the `triage_bucket` and `triage_action` columns
in `data/reference/english_child_reference_coverage.csv` before choosing any
new corpus download. Buckets such as `candidate_gillam`,
`candidate_rollins_or_asd_addon`, `no_direct_phase2_fill`, and
`defer_or_keep_low_confidence` are research intake guidance only; they do not
change clinical readiness or justify multiclass modeling.

Before treating `candidate_gillam` cells as a reason to download more data,
run the source-exhaustion audit:

```bash
python3 scripts/audit_reference_source_exhaustion.py \
  --corpus Gillam \
  --triage-bucket candidate_gillam
python3 scripts/build_reference_coverage_report.py
```

The audit writes `data/reference/english_child_source_exhaustion_audit.csv`.
For Gillam, `policy_exhausted_keep_low_confidence` means no additional
analysis-ready rows remain under the current 50-child-utterance Reference
Cohort policy. It does not mean the raw Gillam corpus has no files left; short
samples remain visible only as counts and must not be merged into the main
Reference Cohort.

## Outputs

The manager writes:

- `data/manifests/talkbank_download_manifest.csv`
- `data/manifests/talkbank_file_inventory.csv`
- `data/manifests/talkbank_qc_summary.csv`
- raw copied files under
  `data/raw/talkbank/{bank}/{corpus}/download_YYYY-MM-DD/`

The raw mirror is ignored by git. Confirm this after intake:

```bash
git status --short --ignored data/raw data/manifests
```

## Existing Corpus Audit

When no new `--corpus`, `--bank`, or `--source-dir` is provided, the manager
audits existing `data/Nadig` and `data/NYU-Emerson` by default:

```bash
python3 scripts/talkbank_download_manager.py --dry-run
```

This is useful before any new download because it confirms the manifest schema,
checksums, and lightweight CHAT QC with the data already in the repository.

## Safety Notes

- Raw TalkBank data is research source material, not user upload data.
- Do not upload the raw mirror to a public bucket or frontend bundle.
- Use manifest rows and derived aggregate features for app-facing reference
  work, not raw transcript text or media.
- Official CLAN/CHATTER validation can be added later; this phase uses
  `pylangacq` because it is already available in the project environment.
