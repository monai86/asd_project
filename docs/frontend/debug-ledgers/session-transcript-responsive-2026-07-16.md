# Transcript workbench responsive debugging ledger — 2026-07-16

## Intent

Implement the approved dominant Transcript workbench while preserving the
existing directly editable lines, clinical workflow gates, and intentional
surface-normalization WIP.

## Experiments and breadcrumbs

1. **Characterize interaction gaps**
   - Initial tests failed because rows had no single-selection semantics,
     secondary line actions were always exposed, and save state had no named
     live region.
   - Rows now use `aria-selected`; split/merge/delete are in an accessible menu;
     and save state is announced politely.

2. **Preserve direct editing and focus**
   - Timestamp, speaker, and utterance controls remain live inputs inside each
     selected row.
   - The overflow trigger selects its row. The menu autofocuses its first action,
     closes with Escape, and restores focus to that row's trigger.

3. **Prevent render-time lookup scans**
   - The previous render loop called `findIndex` for every visible line.
   - A memoized line-ID map now supplies indexes in constant time and also owns
     the selected-line status lookup.

4. **Responsive layout falsification**
   - Real-browser geometry confirms the desktop transcript occupies at least
     60% of the complete workbench while the inspector remains inside its right
     edge.
   - At tablet widths, switching to QA and hiding the inspector keeps the
     utterance editor visible.
   - At 390 px, computed styles confirm both sticky surfaces and at least 176 px
     of reserved workspace padding; document width stays within the viewport.

5. **Visual review corrections**
   - The first desktop capture stretched filter pills to the inspector row
     height. `content-start`, `items-start`, and `self-start` restored compact
     chips.
   - The initial mobile action bar wrapped six actions and became too tall. It is
     now one horizontally scrollable 44 px row with workflow-critical actions
     ordered first.
   - Evidence capture now returns to scroll origin before full-page screenshots,
     avoiding misleading mid-page sticky-shell placement.

## Verification

- Focused transcript/audio tests: 14/14 passed.
- Typecheck: passed.
- Changed-scope lint: no issues.
- Real-backend exact-viewport suite: 5/5 passed.
- Full frontend suite: 46 files, 352/352 passed.
- Optimized production build: passed; Session first-load JavaScript is 254 kB.
- Five screenshots regenerated; phone, tablet, small desktop, and desktop
  compositions reviewed against the approved responsive contract.
