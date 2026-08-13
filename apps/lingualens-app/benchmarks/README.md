# Transcript workspace performance benchmark

Run `npm run bench:transcript`. The command builds the production frontend, starts the memory-backed local API, creates isolated non-identifying cases/sessions, and measures the directly editable transcript at 100, 500, and 1,000 lines.

Each size runs five times and records navigation-to-ready, keystroke, selection, filtering, scroll-frame rate, and Chromium heap data. Raw measurements and reference-machine metadata are written to `results/transcript-benchmark-latest.json` before budget assertions execute.

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
