# Transcript workspace performance benchmark

Run `npm run bench:transcript`. The command builds the production frontend, starts the memory-backed local API, creates isolated non-identifying cases/sessions, and measures the directly editable transcript at 100, 500, and 1,000 lines.

Each size runs five times and records navigation-to-ready, keystroke, selection, filtering, scroll-frame rate, and Chromium heap data. Raw measurements and reference-machine metadata are written to `results/transcript-benchmark-latest.json` before budget assertions execute.

## CI baseline gate

The `therapist-benchmark` job in `.github/workflows/deploy.yml` runs the
benchmark on every push and then `npm run bench:check`, which compares the run
against the committed reference (`results/transcript-benchmark-reference.json`)
with a 2x latency tolerance plus absolute scroll-fps floors. The job **blocks
merge**: a real interaction regression (e.g. the 79/137 ms keystroke regression
documented below) exceeds even the tolerant band, while shared-runner noise does
not. Recalibrate the reference file from actual runner results after a few green
runs if the runner consistently differs; keep the tolerance factor.

## Current baseline — 2026-07-23

Reference environment: Apple M2, 8 logical CPUs, 16 GB memory, macOS/Darwin 25.2.0, headless Chromium 149.0.7827.55, 1280×720, warmed local production server.

| Lines | Ready p95 | Keystroke median / p95 | Selection p95 | Filter p95 | Worst scroll FPS |
|---:|---:|---:|---:|---:|---:|
| 100 | 309.62 ms | 27.1 / 31.8 ms | 25.1 ms | 32.5 ms | 61.10 |
| 500 | 203.83 ms | 15.1 / 31.9 ms | 31.3 ms | 31.3 ms | 61.62 |
| 1,000 | 289.08 ms | 15.9 / 16.0 ms | 27.7 ms | 35.9 ms | 61.81 |

Budgets:

- 500 lines: keystroke p95 ≤ 50 ms and every sampled scroll run ≥ 50 fps.
- 1,000 lines: keystroke p95 ≤ 100 ms and every sampled scroll run ≥ 45 fps.

## Rendering decision

The final remediation benchmark first exposed two separate issues: its filter
locator still targeted the retired button control, and the denser production
row layout caused off-screen layout/paint work to exceed the keystroke budgets
(79.2 ms p95 at 500 lines and 136.9 ms p95 at 1,000 lines). Updating only the
benchmark interaction made the real regression visible; no budget was raised.

Transcript rows now use a memoized reconciliation boundary with stable mutation
callbacks plus browser-native `content-visibility: auto` and responsive
intrinsic block sizes. All rows remain mounted in the DOM for direct editing,
keyboard navigation, accessible list semantics, selection/focus restoration,
audio synchronization, and filtering. The fresh production benchmark passes
with substantial margin, and the paired full-page screenshot still renders all
rows. JavaScript list virtualization is therefore not justified by current
evidence. Reconsider it only if a future production benchmark exceeds a budget;
any implementation must preserve those contracts.
