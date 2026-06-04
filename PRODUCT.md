# Product

## Register

product

## Users
Speech therapists, clinicians, and clinical advisors managing child developmental cases, reviewing CHAT transcript QA, tracking session timelines, analyzing developmental speech-language metrics, and generating progress reports.

## Product Purpose
A modular clinical decision-support prototype that helps speech therapists organize child cases, verify transcript accuracy, review linguistic feature trends (the 14-feature schema), and export safe progress reports. The interface must translate dense, complex data into clean, readable, and structured clinician workflows.

## Brand Personality
- **Minimalist & Calm Clinical**: Structured, professional, clean layout with ample whitespace to reduce cognitive fatigue during heavy clinical tasks.
- **Clinical Teal System**: Calm teal and cyan surfaces with restrained health-green success states, designed for trust, readability, and cross-platform consistency.
- **Readable Depth**: Light translucent panels, crisp borders, and very restrained motion may add depth, but never at the cost of text contrast or performance.

## Anti-references
- **The Visual Clutter of the Current UI**: Inconsistent alignment, nested boxes, hard-edged borders, crowded tables with no vertical rhythm, and pixelated font weights.
- **Dull Gray-on-Gray**: Avoid low-contrast text or washed-out clinical templates.
- **Decorative Glassmorphism**: Blur, glass overlays, and floating blobs must never obscure readability or cause performance jank.
- **Conflicting Crimson Legacy**: Do not reintroduce rose/crimson as the primary identity; keep red for destructive or critical clinical states.

## Design Principles
1. **Clinical Command Clarity**: Present dense clinical information in clean, highly structured layouts. Use surface contrast and spacing to separate sidebars, headers, queues, and detail panels.
2. **Restrained State Motion**: Use 150-250ms transitions only for state changes, navigation, loading, and pressed feedback.
3. **Contrast is King**: Every text block on clinical panels must remain perfectly readable. Bump text colors to near-ink shades and use solid semantic badges for warnings and critical alerts.
4. **Structured Rhythm**: Implement a strict 8px/8dp grid system for margins, padding, and gaps to resolve the currently messy layout.

## Accessibility & Inclusion
- **WCAG Level**: AA (specifically targeting text contrast >= 4.5:1 on all clinical surfaces).
- **Keyboard Navigation**: Ensure all interactive elements have visible focus states with sharp, contrasting focus rings.
- **Motion Accommodations**: Provide support for `prefers-reduced-motion` by freezing decorative motion and preserving instant access to content.
