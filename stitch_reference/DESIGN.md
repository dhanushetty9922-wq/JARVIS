---
name: Synthetic Intelligence HUD
colors:
  surface: '#0f131c'
  surface-dim: '#0f131c'
  surface-bright: '#353943'
  surface-container-lowest: '#0a0e17'
  surface-container-low: '#181b25'
  surface-container: '#1c1f29'
  surface-container-high: '#262a34'
  surface-container-highest: '#31353f'
  on-surface: '#dfe2ef'
  on-surface-variant: '#b9cacb'
  inverse-surface: '#dfe2ef'
  inverse-on-surface: '#2c303a'
  outline: '#849495'
  outline-variant: '#3b494b'
  surface-tint: '#00dbe9'
  primary: '#dbfcff'
  on-primary: '#00363a'
  primary-container: '#00f0ff'
  on-primary-container: '#006970'
  inverse-primary: '#006970'
  secondary: '#bdc2ff'
  on-secondary: '#131e8c'
  secondary-container: '#2f3aa3'
  on-secondary-container: '#a8afff'
  tertiary: '#ecf7ff'
  on-tertiary: '#003547'
  tertiary-container: '#a9e1ff'
  on-tertiary-container: '#006686'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#7df4ff'
  primary-fixed-dim: '#00dbe9'
  on-primary-fixed: '#002022'
  on-primary-fixed-variant: '#004f54'
  secondary-fixed: '#e0e0ff'
  secondary-fixed-dim: '#bdc2ff'
  on-secondary-fixed: '#000767'
  on-secondary-fixed-variant: '#2f3aa3'
  tertiary-fixed: '#c0e8ff'
  tertiary-fixed-dim: '#7bd1fa'
  on-tertiary-fixed: '#001e2b'
  on-tertiary-fixed-variant: '#004d66'
  background: '#0f131c'
  on-background: '#dfe2ef'
  surface-variant: '#31353f'
typography:
  display-hero:
    fontFamily: Space Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.03em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Space Grotesk
    fontSize: 18px
    fontWeight: '500'
    lineHeight: 26px
    letterSpacing: 0em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0.01em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0.01em
  telemetry-data:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0.04em
  telemetry-unit:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 14px
    letterSpacing: 0.08em
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '600'
    lineHeight: 12px
    letterSpacing: 0.14em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  margin: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

This design system channels an advanced diagnostic and executive AI companion interface. It merges the kinetic precision of tactical aerospace heads-up displays (HUD) and Stark-grade arc-reactor aesthetics with the refined ergonomics of native Windows 11 Fluent architecture. The tone is authoritative, hyper-responsive, analytical, and distinctly futuristic without descending into unusable novelty.

### Aesthetic Axioms
- **Kinetic Telemetry:** The interface communicates continuous vitality through micro-pulses, radial status readouts, and directional scanning lines rather than static cards.
- **Luminous Hierarchy:** Light represents active computational focus. Elements brighten and sharpen as priority elevates; idle elements recede into cold, deep midnight voids.
- **Glass-Steel Hybridization:** Semi-translucent layered acrylics combined with laser-sharp sub-pixel borders emulate advanced multi-pane projection glass.
- **Restraint Over Clutter:** Despite HUD inspirations, information density is rigorously structured through precise spatial anchors, monospaced numeric tracking, and unobtrusive ambient states.

## Colors

The palette balances abyssal baseline depths with high-luminance coherent light emissions. Background surfaces do not use neutral blacks or grays; they are deeply saturated with graphite and oceanic navy to allow cyan and violet photons to resonate with zero muddying.

### Palette Architecture
- **Deep Graphite & Void Foundations:** Primary background canvas sits at `#05070E`, with surface tier 1 at `#090D16` and floating windows/acrylic containers at `#0D111D`.
- **Photon Primary:** Electric Cyan (`#00F0FF`) serves as the core vector of active intelligence, operational focus, and affirmative state indicators.
- **Holographic Violet Secondary:** Spectral Indigo/Violet (`#818CF8` to `#A855F7`) governs background heuristics, neural thread processing, synthesis states, and deep contextual tags.
- **Cryo Accent:** Ice-Blue (`#7DD3FC`) provides lower-contrast telemetry labels, calm scanlines, and intermediate informational markers.
- **Structural Outlines:** Borders leverage 15% to 30% alpha channels of cyan (`rgba(0, 240, 255, 0.2)`) and slate (`rgba(148, 163, 184, 0.12)`) to delineate planes without occluding the canvas.

## Typography

The typographic hierarchy enforces a division between human communication, tactical readouts, and core system telemetry.

- **Primary Display (Space Grotesk):** Provides structural, architectural authority with subtle geometric oddities that invoke advanced computation. Used for major module headings and primary agent status labels.
- **General Interface (Inter):** Highly legible, neutral workhorse engineered for conversational streams, generated analysis, system descriptions, and long-form interaction logs.
- **Telemetry & Metadata (JetBrains Mono):** Reserved for raw data feeds, hardware diagnostic outputs, system clocks, latency monitors, coordinates, and micro-caps status pills. Set in tabular figures by default to prevent numerical jitter during live streaming updates.

## Layout & Spacing

The layout operates on a desktop-native composite grid inspired by Windows 11 window management and multi-pane mission control dashboards. 

### Structural Framework
- **Master Grid:** 12-column variable responsive canvas anchored inside standard desktop viewports (1440px to 4K ultrawide). Content adheres strictly to nested sub-grids with uniform gutters.
- **HUD Shell:** A permanent 64px left-hand utility telemetry bar; a persistent 40px top system command ribbon with integrated title bar draggable zones; a primary modular cockpit pane (variable flex width); and an optional auxiliary 360px collapsible intelligence canvas (diagnostic graphs, raw telemetry streams).
- **Rhythm Rules:** Spacing tokens apply cleanly to component internals. Complex data widgets must rely on `space-xs` and `space-sm` for high-density layout economy, while discursive message streams utilize `space-md` to `space-lg` to provide breathing room.

## Elevation & Depth

Spatial separation avoids opaque dropdown drop-shadows. Instead, elevation is simulated through back-surface illumination, refractive translucency, and electromagnetic border glows.

### Layering Levels
- **Canvas Base (Level 0):** Pure solid `#05070E` with micro-radial vignette and optional 3% opacity isometric coordinate grid.
- **Docked Panels / Modules (Level 1):** Background `rgba(9, 13, 22, 0.72)` paired with `backdrop-filter: blur(16px)` and an interior 1px stroke of `rgba(56, 189, 248, 0.12)`.
- **Floating Modals & Flyouts (Level 2):** Background `rgba(13, 17, 29, 0.85)` with `backdrop-filter: blur(28px)`, a border of `rgba(0, 240, 255, 0.28)`, and an ambient back-glow: `box-shadow: 0 0 32px -4px rgba(0, 240, 255, 0.15), 0 20px 40px -10px rgba(0, 0, 0, 0.7)`.
- **Active Focus & Reactor Centers (Level 3):** Reserved for active core indicators and priority alerts. High-frequency glow: `box-shadow: 0 0 16px rgba(0, 240, 255, 0.45), inset 0 0 12px rgba(0, 240, 255, 0.2)`.

## Shapes

The geometric architecture avoids bubbly or toy-like roundness, settling on a controlled, technical profile (`roundedness: 1`, 4px base radius) evocative of precision-milled hardware casings and Windows Fluent app frames.

### Shape Rules
- **Base Surfaces & Panels:** 4px to 6px corner radii to balance technical rigidity with modern OS cohesion.
- **HUD Telemetry Chips & Pointers:** Sharp-beveled edges or crisp 2px radii for raw metric containers.
- **Reactor Core & Telemetry Rings:** Pure circles (`border-radius: 9999px`) used strictly for contextual status nodes, holographic orbital activity spinners, and voice interaction rings.

## Components

### 1. Interactive Core (Voice / AI Engine Indicator)
- **Structure:** Multi-layered concentric orbital SVG rings enclosing an arc-reactor energy core.
- **Idle State:** Pulsing outer cyan ring (`opacity: 0.3`, 4s ease-in-out cycle), inner core glowing steady at `#00F0FF` with a subtle violet orbital thread.
- **Listening / Processing:** Rings rotate along opposite axes with frequency-driven stroke oscillations; neon blooms expand dynamically (`box-shadow: 0 0 40px rgba(0, 240, 255, 0.5)`).

### 2. Buttons & Triggers
- **Primary Cyber:** Translucent cyan surface (`rgba(0, 240, 255, 0.12)`), outer 1px stroke (`rgba(0, 240, 255, 0.6)`), text set in `JetBrains Mono` bold uppercase with `0.08em` tracking. Hover initiates an instantaneous light fill transition to `rgba(0, 240, 255, 0.24)` and subtle cyan ray drop-shadow.
- **Secondary Ghost:** Transparent canvas, stroke `rgba(148, 163, 184, 0.2)`, text in muted ice-blue (`#7DD3FC`). Hover brings stroke to `rgba(129, 140, 248, 0.5)`.

### 3. Glassmorphic Data Cards
- Panels rendered with `bg-[#0D111D]/60`, `backdrop-blur-md`, and `border border-cyan-500/20`.
- Top-right corner displays a subtle 8px technical registration reticle or monospaced telemetry tag (e.g., `SYS.08 // ACTIVE`).

### 4. Input Fields
- Monospaced input text field set against `rgba(5, 7, 14, 0.8)`.
- 1px boundary of `rgba(125, 211, 252, 0.2)`. Focus triggers a glowing line scan animation across the bottom border transitioning into solid `#00F0FF` with an inner shadow beam.

### 5. Chips & Diagnostic Badges
- Pill or chamfered geometry (`roundedness: 1`). Monospaced micro-caps (`10px`).
- Accompanied by a 4px solid neon indicator dot (Cyan = nominal, Violet = neural compute, Amber = thermal anomaly).

### 6. Telemetry Progress & Waveforms
- Audio waveforms and computational loads rendered via sharp 2px bar arrays using linear gradients from `#00F0FF` up to `#818CF8`. Zero rounded ends on progress indicators to emphasize technical fidelity.