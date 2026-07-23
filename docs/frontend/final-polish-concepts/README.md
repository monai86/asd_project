# LinguaLens final-polish visual concepts

Status: approved-direction implementation contract, created before production
visual changes on 2026-07-21.

The source storyboard is `concepts.html`. It is intentionally static and uses
only anonymized case labels. It translates the Airtable reference's structural
restraint into the existing LinguaLens information architecture and clinical
palette; it does not copy Airtable branding, typography, marketing surfaces, or
brand colors.

## Required concept matrix

| Surface | Query | Native concept viewport | Contract |
|---|---|---:|---|
| Today | `?surface=today` | 1440×900 | Preserve focused workbench, one queue, one row action, one Start session action, quiet rail |
| Cases | `?surface=cases` | 1440×900 | Next action first; list + compact authorized selected-case summary |
| Transcript desktop | `?surface=transcript-desktop` | 1440×900 | Direct editor at about 65%; collapsible/resizable inspector at about 35% |
| Transcript iPad portrait | `?surface=transcript-tablet-portrait` | 768×1024 | Transcript stays full width; Audio/QA is a keyboard-accessible switchable panel |
| Transcript iPad landscape | `?surface=transcript-tablet-landscape` | 1024×768 | Measured 65/35 editor/inspector split; inspector can hide without clipping |
| Transcript mobile | `?surface=transcript-mobile` | 390×844 | Context → sticky compact player → editable transcript → safe-area sticky Save/QA; secondary details collapsed |
| Findings | `?surface=findings` | 1440×900 | Level 1 groups, level 2 feature details on demand, level 3 evidence/limits disclosures |
| Settings mobile | `?surface=settings-mobile` | 390×844 | Category navigation and drill-down; admin categories shown only in the admin variant |

## Visual language

- Noto Sans Thai / Noto Sans / system sans-serif.
- True-white reading surfaces on a very light cool neutral canvas.
- Near-black ink, neutral hairlines, and restrained teal for action, focus, and
  selection.
- 5 px controls, 8 px panels, and 10 px maximum workspace radius.
- No ordinary panel shadows; elevation is reserved for temporary layers.
- Compact controls retain a 44 px touch target in touch layouts.
- Moderate weights and spacing create hierarchy; large display typography,
  decorative gradients, glass surfaces, and nested card grids are excluded.

## Interaction and safety annotations

- Transcript rows remain directly editable and selected state remains explicit.
- Secondary line actions stay in overflow.
- Tablet portrait switches views instead of squeezing the transcript.
- Mobile sticky regions reserve space and include the safe-area inset.
- Settings administrator categories are a variant, not therapist placeholders.
- Findings keeps one contextual non-diagnostic boundary and does not expose all
  methods and cautions at once.
- Today is documented as preserved; its concept is a fidelity reference, not
  permission to change its product hierarchy.

Implementation captures must be compared against these concepts at 390×844,
768×1024, 1024×1366, 1280×800, and 1440×900. A visual difference is acceptable
only when it preserves an existing safety/accessibility requirement or is
recorded in the final fidelity ledger.
