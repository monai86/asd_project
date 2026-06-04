---
name: ASD Project Speech Therapist
description: Minimalist & Calm Clinical Design System (Crimson Rose & Liquid Glass)
colors:
  primary: "#E11D48"
  primary-soft: "#FFE4E6"
  peach: "#FB923C"
  peach-soft: "#FFEDD5"
  neutral-bg: "#FDFAF9"
  neutral-glass: "rgba(255, 255, 255, 0.45)"
  ink: "#1F080E"
  muted: "#644A50"
  border: "rgba(255, 255, 255, 0.6)"
  border-dark: "#F3E8E6"
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
    backgroundColor: "#BE123C"
  button-secondary:
    backgroundColor: "{colors.neutral-glass}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "10px 18px"
---

# Design System: ASD Project Speech Therapist

## 1. Overview

**Creative North Star: "The Crimson Oasis"**

The Crimson Oasis is a user interface system designed specifically for the ASD Clinical Decision-Support Prototype. It reconciles the density requirements of a professional clinical dashboard with a calming, empathetic, and distraction-free visual environment. It replaces the messy layout of the current site with an organized grid, soft translucency, and slow-moving organic peach and rose liquid glass backdrops.

### Key Characteristics:
- **Atmospheric Depth**: Semi-transparent glass cards floating over slowly changing, smooth peach and rose liquid blobs.
- **Calm, Warm-Contrast Typography**: Readable headings using the clean sans-serif *Outfit* paired with *Inter* for crisp body text.
- **Warm Ink & Muted Shades**: Replaces harsh pitch black with a deep wine-chocolate shade (#1F080E) for a gentler reading experience.
- **Intuitive Spacing**: A rigid 8px grid structure ensuring balanced alignment and clean vertical rhythm.
- **Ethical Integrity**: Clear warnings, explicit disclaimers, and human-in-the-loop labels using solid, highly visible status badges.

## 2. Colors

Calm crimson rose, peach, and soft pinks, layered over translucent glass panels.

### Primary
- **Crimson Rose** (#E11D48 / oklch(56% 0.20 15)): Primary branding, focus borders, active highlights.
- **Calm Peach** (#FB923C / oklch(70% 0.16 48)): Secondary highlights, progress tracking trends.

### Neutral
- **Wine Ink** (#1F080E / oklch(18% 0.04 15)): Body and heading text. Must meet WCAG AA contrast (>=4.5:1) against background gradients and glass panels.
- **Glass Surface** (rgba(255, 255, 255, 0.45) / oklch(100% 0 0 / 0.45)): The core panel container style. Backed by `backdrop-filter: blur(16px)`.
- **Soft Muted Wine** (#644A50 / oklch(40% 0.04 15)): Captions, labels, and secondary context text.
- **Liquid Background** (#FDFAF9 / oklch(98% 0.005 15)): The base container color.

### Named Rules
**The 10% Crimson Rule.** The highly saturated primary Crimson Rose is restricted to critical actions and active states. It must never occupy more than 10% of any screen surface to preserve visual calm.

**The Contrast Safety Rule.** Text on glass surfaces must never be rendered in light pink or light gray. Body text must remain Wine Ink (#1F080E) or Soft Muted Wine (#644A50) to guarantee readability.

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

Depth is conveyed through a combination of backdrop blurs, translucent borders, and very soft, low-opacity drop shadows. No harsh dark borders.

### Shadow Vocabulary
- **Glass Glow** (`0 8px 32px 0 rgba(190, 18, 60, 0.03)`): The primary glass card elevation.
- **Active Focus** (`0 0 0 3px rgba(225, 29, 72, 0.2)`): The interactive outline focus state.

### Named Rules
**The Glassmetaphor Rule.** Shadows must never appear on flat, non-glass backgrounds. They are strictly reserved for glass card layers to separate them from the flowing background blobs.

## 5. Components

### Buttons
- **Shape:** Medium rounded corners (12px).
- **Primary:** Crimson Rose background (#E11D48), white text, padding (10px 18px). On hover, background deepens to (#BE123C).
- **Secondary (Glass button):** Translucent background (rgba(255, 255, 255, 0.45)), Wine Ink text (#1F080E), border (1px solid rgba(255, 255, 255, 0.6)), padding (10px 18px).

### Chips
- **Style:** Background (rgba(255, 255, 255, 0.6)), border (1px solid rgba(255, 255, 255, 0.8)), rounded (12px), padding (4px 10px).
- **Concern Status Badges:**
  - *Low Concern*: Sage green (#10B981) text on soft green (#D1FAE5) background.
  - *Medium Concern*: Amber (#F59E0B) text on soft yellow (#FEF3C7) background.
  - *High Concern*: Rose red (#EF4444) text on soft red (#FEE2E2) background.

### Cards / Containers
- **Corner Style:** Large rounded corners (20px).
- **Background:** Translucent glass (rgba(255, 255, 255, 0.45)) with `backdrop-filter: blur(16px)`.
- **Border:** Soft white border (1px solid rgba(255, 255, 255, 0.6)).
- **Internal Padding:** Large (24px) spacing for content, medium (16px) for headers.

### Inputs / Fields
- **Style:** Background (rgba(255, 255, 255, 0.65)), border (1px solid rgba(255, 255, 255, 0.8)), radius (12px), padding (10px 14px).
- **Focus:** 3px outline glow in Crimson Rose (`0 0 0 3px rgba(225, 29, 72, 0.25)`).

### Navigation
- **Sidebar Layout:** Floating glass panel. Active nav items transition to a soft rose-tinted glass background (`rgba(225, 29, 72, 0.08)`) with a bold Crimson Rose typography link color.

## 6. Do's and Don'ts

### Do:
- **Do** check that all text overlays on the glass background achieve a contrast ratio of >=4.5:1.
- **Do** use `backdrop-filter: blur(16px)` on every glass container to preserve text readability.
- **Do** use vector SVG icons exclusively instead of emojis for dashboard controls.
- **Do** maintain a strict 8px spacing rhythm across cards and input paddings.

### Don't:
- **Don't** use neon, highly saturated color gradients for text or background cards.
- **Don't** use side-stripe borders (e.g. `border-left: 4px solid var(--primary-red)`) on alert boxes or cards; keep borders full and consistent.
- **Don't** use standard shadows with opacity greater than 10%. Keep them extremely soft and diffuse.
- **Don't** use extreme border radii (greater than 20px) on card panels.
- **Don't** let text overflow its containers on smaller viewports. Ensure all text adapts gracefully.
