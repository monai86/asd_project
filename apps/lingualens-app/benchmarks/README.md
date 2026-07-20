# Transcript workspace performance benchmark

Run `npm run bench:transcript`. The command builds the production frontend, starts the memory-backed local API, creates isolated non-identifying cases/sessions, and measures the directly editable transcript at 100, 500, and 1,000 lines.

Each size runs five times and records navigation-to-ready, keystroke, selection, filtering, scroll-frame rate, and Chromium heap data. Raw measurements and reference-machine metadata are written to `results/transcript-benchmark-latest.json` before budget assertions execute.

## Current baseline — 2026-07-17

Reference environment: Apple M2, 8 logical CPUs, 16 GB memory, macOS/Darwin 25.2.0, headless Chromium 149.0.7827.55, 1280×720, warmed local production server.

| Lines | Ready p95 | Keystroke median / p95 | Selection p95 | Filter p95 | Worst scroll FPS |
|---:|---:|---:|---:|---:|---:|
| 100 | 1,179.73 ms | 20.2 / 23.4 ms | 24.0 ms | 33.3 ms | 60.51 |
| 500 | 962.91 ms | 17.3 / 23.0 ms | 28.9 ms | 34.0 ms | 60.45 |
| 1,000 | 966.47 ms | 19.4 / 19.7 ms | 14.0 ms | 47.8 ms | 61.84 |

Budgets:

- 500 lines: keystroke p95 ≤ 50 ms and every sampled scroll run ≥ 50 fps.
- 1,000 lines: keystroke p95 ≤ 100 ms and every sampled scroll run ≥ 45 fps.

## Rendering decision

The initial non-memoized implementation failed keystroke budgets at 118.6 ms p95 for 500 lines and 440.9 ms p95 for 1,000 lines while maintaining approximately 60 fps scrolling. That pattern identified full-row reconciliation—not the mounted editable DOM—as the bottleneck.

Transcript rows now use a memoized reconciliation boundary with stable mutation callbacks. The production benchmark passes with substantial margin while retaining direct editing, selection/focus semantics, complete accessibility structure, audio synchronization, and filter behavior. Virtualization is therefore not justified by current evidence. Reconsider it only if a future production benchmark exceeds a budget; any implementation must preserve those contracts.
