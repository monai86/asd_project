---
name: ASD Project Speech Therapist
description: Minimalist & Calm Clinical Design System (Clinical Teal)
colors:
  primary: "#0891B2"
  primary-soft: "#CCFBF1"
  secondary: "#22D3EE"
  accent: "#059669"
  neutral-bg: "#ECFEFF"
  neutral-glass: "rgba(255, 255, 255, 0.94)"
  ink: "#164E63"
  muted: "#475569"
  border: "#A5F3FC"
  border-dark: "#67E8F9"
  success: "#10B981"
  success-soft: "#D1FAE5"
  warning: "#F59E0B"
  warning-soft: "#FEF3C7"
  destructive: "#EF4444"
  destructive-soft: "#FEE2E2"
typography:
  display:
    fontFamily: "Outfit, Inter, sans-serif"
    fontSize: "clamp(2rem, 5vw, 3.5rem)"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Outfit, Inter, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Outfit, Inter, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 500
    lineHeight: 1.3
  body:
    fontFamily: "Inter, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Inter, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 500
    lineHeight: 1.4
rounded:
  sm: "6px"
  md: "12px"
  lg: "20px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#FFFFFF"
    rounded: "{rounded.md}"
    padding: "10px 18px"
  button-primary-hover:
    backgroundColor: "#0E7490"
  button-secondary:
    backgroundColor: "{colors.neutral-glass}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "10px 18px"
---

# Design System: ASD Project Speech Therapist

## 1. Overview

**Creative North Star: "Clinical Teal Workspace"**

Clinical Teal Workspace is a restrained product UI system for the ASD Clinical Decision-Support Prototype. It reconciles the density requirements of a professional clinical dashboard with high-contrast teal surfaces, predictable component states, and cross-platform layouts that work in web and iOS shells.

### Key Characteristics:
- **Readable Depth**: Light clinical surfaces with crisp cyan borders and minimal blur, never decorative glass as the default.
- **Calm Clinical Typography**: Readable headings using the clean sans-serif *Outfit* paired with *Inter* for crisp body text.
- **Teal Ink & Muted Slate**: Replaces washed-out gray with dark teal ink (#164E63) and slate secondary text.
- **Intuitive Spacing**: A rigid 8px grid structure ensuring balanced alignment and clean vertical rhythm.
- **Ethical Integrity**: Clear warnings, explicit disclaimers, and human-in-the-loop labels using solid, highly visible status badges.

## 2. Colors

Calm teal, cyan, and health green layered over high-contrast light clinical surfaces.

### Primary
- **Clinical Teal** (#0891B2 / oklch(60% 0.11 215)): Primary actions, focus borders, active navigation, and selection.
- **Health Green** (#059669 / oklch(58% 0.14 165)): Confirmed, reviewed, and success states.

### Neutral
- **Teal Ink** (#164E63): Body and heading text. Must meet WCAG AA contrast (>=4.5:1) against all clinical surfaces.
- **Clinical Surface** (rgba(255, 255, 255, 0.94)): The core panel container style with crisp border separation.
- **Muted Slate** (#475569): Captions, labels, and secondary context text.
- **Cool Clinical Background** (#ECFEFF): The base workspace color.

### Named Rules
**The 10% Teal Rule.** Saturated Clinical Teal is restricted to primary actions, active navigation, and focus states. It must never occupy more than 10% of any screen surface to preserve visual calm.

**The Contrast Safety Rule.** Text on clinical surfaces must never be rendered in pale cyan or light gray. Body text must remain Teal Ink (#164E63) or a darker slate tone to guarantee readability.

## 3. Typography

**Display Font:** Outfit (sans-serif)
**Body Font:** Inter (sans-serif)
**Label/Mono Font:** Inter (sans-serif)

The type system pairs the friendly geometric elegance of Outfit with the highly legible, structural form of Inter for long lists, transcript tables, and notes.

### Hierarchy
- **Display** (Semi-bold (600), clamp(2rem, 5vw, 3.5rem), 1.1): Big headlines, login welcome, report title.
- **Headline** (Semi-bold (600), 1.75rem, 1.2): Section titles, topbar title.
- **Title** (Medium (500), 1.25rem, 1.3): Card titles, panel headings.
- **Body** (Regular (400), 1rem, 1.5): Case summary description, transcript lines, notes (max line length 70ch).
- **Label** (Medium (500), 0.875rem, 1.4): Navigation sidebar labels, table column headers.

### Named Rules
**The Pretty-Balance Rule.** All h1-h3 headers must use `text-wrap: balance` to prevent awkward line breaks and orphan words.

## 4. Elevation

Depth is conveyed through crisp borders, controlled surface contrast, and very soft, low-opacity shadows. No harsh dark borders.

### Shadow Vocabulary
- **Clinical Lift** (`0 8px 18px rgba(8, 145, 178, 0.08)`): The primary panel elevation.
- **Active Focus** (`0 0 0 3px rgba(8, 145, 178, 0.2)`): The interactive outline focus state.

### Named Rules
**The Surface Discipline Rule.** Use either a crisp border or a tight shadow for panel separation. Avoid pairing decorative borders with wide soft shadows.

## 5. Components

### Buttons
- **Shape:** Medium rounded corners (12px).
- **Primary:** Clinical Teal background (#0891B2), white text, padding (10px 18px). On hover, background deepens to (#0E7490).
- **Secondary:** White clinical surface, Teal Ink text (#164E63), border (1px solid #A5F3FC), padding (10px 18px).

### Chips
- **Style:** Background (rgba(255, 255, 255, 0.6)), border (1px solid rgba(255, 255, 255, 0.8)), rounded (12px), padding (4px 10px).
- **Concern Status Badges:**
  - *Low Concern*: Sage green (#10B981) text on soft green (#D1FAE5) background.
  - *Medium Concern*: Amber (#F59E0B) text on soft yellow (#FEF3C7) background.
  - *High Concern*: Clinical red (#EF4444) text on soft red (#FEE2E2) background.

### Cards / Containers
- **Corner Style:** Large rounded corners (20px).
- **Background:** Near-white clinical surface (rgba(255, 255, 255, 0.94)).
- **Border:** Cyan border (1px solid #A5F3FC).
- **Internal Padding:** Large (24px) spacing for content, medium (16px) for headers.

### Inputs / Fields
- **Style:** Background (rgba(255, 255, 255, 0.65)), border (1px solid rgba(255, 255, 255, 0.8)), radius (12px), padding (10px 14px).
- **Focus:** 3px outline glow in Clinical Teal (`0 0 0 3px rgba(8, 145, 178, 0.25)`).

### Navigation
- **Sidebar Layout:** Calm clinical panel. Active nav items transition to a soft teal background (`rgba(8, 145, 178, 0.10)`) with bold Clinical Teal link color.

## 6. Do's and Don'ts

### Do:
- **Do** check that all text on clinical surfaces achieves a contrast ratio of >=4.5:1.
- **Do** reserve blur for drawer or modal backdrops, not ordinary content panels.
- **Do** use vector SVG icons exclusively instead of emojis for dashboard controls.
- **Do** maintain a strict 8px spacing rhythm across cards and input paddings.

### Don't:
- **Don't** use neon, highly saturated color gradients for text or background cards.
- **Don't** use side-stripe borders (e.g. `border-left: 4px solid var(--primary-red)`) on alert boxes or cards; keep borders full and consistent.
- **Don't** use standard shadows with opacity greater than 10%. Keep them extremely soft and diffuse.
- **Don't** use extreme border radii (greater than 20px) on card panels.
- **Don't** let text overflow its containers on smaller viewports. Ensure all text adapts gracefully.
