# Product

## Register

product

## Users
Speech therapists, clinicians, and clinical advisors managing child developmental cases, reviewing CHAT transcript QA, tracking session timelines, analyzing developmental speech-language metrics, and generating progress reports.

## Product Purpose
A modular clinical decision-support prototype that helps speech therapists organize child cases, verify transcript accuracy, review linguistic feature trends (the 14-feature schema), and export safe progress reports. The interface must translate dense, complex data into clean, readable, and structured clinician workflows.

## Brand Personality
- **Minimalist & Calm Clinical**: Structured, professional, clean layout with ample whitespace to reduce cognitive fatigue during heavy clinical tasks.
- **Liquid Glass Materials**: Soft glassmorphism cards, blurred backdrop layers, and organic liquid-like floating background animations that evoke a sense of calming flow, depth, and premium quality.
- **Calm, Crimson Tones**: Soft rose-red accents (Crimson Rose), warm peach highlights, and a warm off-white background combined with deep wine-chocolate typography for high-contrast legibility.

## Anti-references
- **The Visual Clutter of the Current UI**: Inconsistent alignment, nested boxes, hard-edged borders, crowded tables with no vertical rhythm, and pixelated font weights.
- **Dull Gray-on-Gray**: Avoid low-contrast text or washed-out clinical templates.
- **Aggressive/Intrusive Glassmorphism**: Glass overlays that obscure readability or cause performance jank. Glass cards must have clear borders, strong dark text contrast (>=4.5:1), and high legibility.

## Design Principles
1. **Clinical Command Clarity**: Present dense clinical information in clean, highly structured layouts. Leverage glass layers to establish clear visual hierarchy and separate sidebars, headers, queues, and detail panels.
2. **Organic Calming Motion**: Use subtle, slow-flowing liquid background blobs and smooth transitions (150-300ms) to make the clinical workspace feel alive yet peaceful.
3. **Contrast is King**: Every text block on glass panels must remain perfectly readable. Bump text colors to near-ink shades and use solid semantic badges for warnings and critical alerts.
4. **Structured Rhythm**: Implement a strict 8px/8dp grid system for margins, padding, and gaps to resolve the currently messy layout.

## Accessibility & Inclusion
- **WCAG Level**: AA (specifically targeting text contrast >= 4.5:1 on all glass/backdrop combinations).
- **Keyboard Navigation**: Ensure all interactive elements have visible focus states with sharp, contrasting focus rings.
- **Motion Accommodations**: Provide support for `prefers-reduced-motion` by freezing or fading out liquid background animations.
