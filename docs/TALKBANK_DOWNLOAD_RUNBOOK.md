# TalkBank Download Runbook

This runbook covers transcript and sidecar intake for the TalkBank Raw Mirror.
It does not cover raw audio/video media downloads.

## Scope

- Download transcripts and sidecar files for `EllisWeismer`, `ENNI`, and
  `Ambrose`.
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
