# THEME_RECON.md — Forge Theme Inspection & Diagnosis

## 1. Frontend Architecture
- **Framework**: Vanilla JS with ES modules
- **CSS Organization**: Multiple files loaded in index.html:
  - `/static/style.css?v=8` → imports `forge-gen4.css` (primary)
  - `/static/ai-settings.css`
  - `/static/motion/motion.css?v=20261015-1`
  - `/static/forge-motion.css?v=6`
  - `/static/forge-smooth.css?v=1`
- **Scripts loaded in order**: forge-fx.js, forge-fx-config.js, forge-flow.js, forge-trace.js, forge-smooth.js, forge-bench.js, app.js (module)
- **Main HTML**: app/static/index.html (single page app)

## 2. Color Definitions (all locations)

### Primary palette (forge-gen4.css:1-37) — **ACTIVE**
```css
--paper: #f4f0e7;           --paper-panel: #ebe4d8;
--paper-quiet: #e1d9ca;     --paper-bright: #fbf8f1;
--ink: #20211e;             --ink-soft: #35362f;
--ink-code: #171814;        --ink-code-2: #20211e;
--slate: #67675f;           --quiet: #929087;
--line: #c9c1b2;            --line-dark: #46463e;
--ember: #bd492d;           --ember-deep: #92341f;
--ember-wash: #f1d5ca;      --pine: #2d6959;
--pine-wash: #d9e7df;       --gold: #a36d18;
--danger: #a93a33;          --danger-wash: #f4d9d5;
--perimeter-stroke: #e8dfd0; --perimeter-stroke-dim: #c9c1b2;
```

### Alternative token system (tokens.css) — **NOT USED** (loaded but overridden)
- Dark mode (primary): --bg-void: #080a0c, --accent: #00d4aa (teal)
- Light mode (prefers-color-scheme): --bg-void: #f5f8f9, --accent: #00a888
- Forced dark: [data-theme="dark"] block

### forge-motion.css:1
```css
--flow-accent: #bd492d;  /* must be opaque hex/rgb for morph engine */
```

### Hard-coded colors in forge-gen4.css (remaining after variable usage)
- boot-index: #bbb7ab (line 66)
- boot-reading border: #626259 (line 70)
- boot-reading span: #bbb7ab (line 71)
- boot-note: #a8a59a (line 73)
- boot-action border: #8d897d (line 75)
- boot-action hover: #d45838 (line 76)
- boot-continue hover: #34352f (line 76)
- rail bg: #3b3b35 (line 100)
- rail-button hover: #30312c (line 100)
- rail-button active: #393a33 (line 100)
- tree-row hover: #dfd8ca (line 102)
- tree-row selected: #e3cfc3 (line 102)
- search-field focus: #dc795e (line 107)
- find-strip input focus: #dc795e (line 107)
- tab-dirty: #e2a04d (line 108)
- tab-close hover: #4a2a23 (line 108)
- editor empty index: #c8856f (line 109)
- statusbar span last: #fae4da (line 117)
- modal-backdrop: rgb(28 28 25 / .58) (line 120)
- command-palette shadow: rgb(32 33 30 / .2) (line 120)
- toast shadow: rgb(32 33 30 / .18) (line 120)
- empty-action: #fff8ef (line 154)
- empty-action quiet: #d9d1c4, #55564e (line 155)
- empty-action quiet hover: #34352f (line 157)
- panel-reveal: #d6cec0, #55564e (line 159)
- panel-reveal hover: #fff8ef, #34352f (line 160)
- surface-code-raised: #252621 (line 202)
- surface-code-deep: #1d1e1a (line 203)
- text-on-dark: #e7dfd0 (line 206)
- text-on-dark-muted: #aaa69a (line 207)
- border-dark: #45463e (line 208)
- scrollbar: #5c5d54 (line 211)
- tree-row active: #dfd8ca (line 237)
- result-row active: #dfd8ca (line 238)

### components.css hard-coded
- File icon colors (lines 733-745): #3776ab, #f7df1e, #3178c6, #e8b84d, #00d4aa, #e34f26, #1572b6, #cb171e, #9c4221, #dea584, #00add8, #4eaa25, #2496ed
- ai-primary: #fff8ef (line 89)
- ai-danger hover: #fff8ef (line 94)

### motion/motion.css hard-coded
- --surface-rail fallback: #20211e (line 34)
- --surface-sidebar fallback: #ebe4d8 (line 35)
- --surface-header fallback: #fbf8f1 (line 36)
- --surface-code fallback: #171814 (line 37)
- --surface-dock fallback: #20211e (line 38)
- --accent fallback: #bd492d (line 39)
- rail border: #3b3b35 (line 187)
- rail active bg: #e3cfc3 (lines 264, 341)
- tab-dirty: #e2a04d (line 381)
- dock bg: #20211e (line 497)
- dock text: #f4f0e7 (line 498)
- indicator stroke: #bd492d (line 507)
- indicator glow: #bd492d (line 512)

### motion/morph.js hard-coded
- rgba(224, 83, 60, 0.15) (line 373)
- #e0533c (line 374)
- #f4f0e7 (line 376)
- rgba(0,0,0,0.25) (line 381)

### app.js hard-coded (inline styles)
- boot-screen mask: radial-gradient with transparent/black
- shockwave, content, perimeter, app transforms
- Various inline style.color, backgroundColor, borderColor writes

### forge-smooth.js:309,325
- FPS overlay: #9f9, #f66, #fc6

## 3. Existing CSS Variables / Theme Code
- **forge-gen4.css**: Complete warm clay/paper system (light only, no dark mode)
- **tokens.css**: Complete dark-first teal system with @media prefers-color-scheme and [data-theme="dark"] — **but not active** (forge-gen4.css loads first and wins)
- **forge-motion.css**: --flow-accent for morph engine
- No existing theme switcher, no localStorage theme persistence

## 4. Settings System
- **AI Settings**: Saved to backend via `/api/ai/providers` (PUT/GET/DELETE), config returned with api_key_configured flag
- **Settings Panel**: Created in index.html (#settings-panel), shown via settingsFlow (ForgeFlow)
- **Persistence**: Backend JSON file (implied by API), no localStorage mirror for theme yet
- **Session Storage**: Used for "forge-gen4-intro" flag only

## 5. Loading Screen
- **Element**: `#boot-screen` (z-index: 100, fixed inset: 0)
- **Components**: `.boot-shockwave`, `.boot-perimeter` (SVG paths), `.boot-content` (index, title, reading, failure)
- **Transition**: `completeBootTransition()` in app.js:367-498
  - Adds `body.workspace-visible` class
  - Radial gradient mask aperture animation (110ms delay)
  - Spring animation with stagger for topbar, rail, mainStage
  - Removes boot-screen from DOM when settled

## 6. Syntax Highlighter
- **Location**: app.js:687-700 `highlight()` function
- **Token classes**: `.tok-keyword`, `.tok-string`, `.tok-comment`, `.tok-number`, `.tok-function`
- **Colors defined in forge-gen4.css:835-843**:
  - tok-keyword: #e7a586
  - tok-string: #b7d5a6
  - tok-comment: #87877f
  - tok-number: #c6abdc
  - tok-function: #a8cce0

## 7. Icons
- **SVG Sprite**: In index.html:138-154, all use `stroke="currentColor"` / `fill="currentColor"`
- **File icons**: components.css:720-746 use hardcoded hex colors per extension
- **Folder icons**: Use `--warning` (tokens.css) or hardcoded in motion.css

## 8. Scrollbar, Selection, Caret, Meta
- **Scrollbar**: `* { scrollbar-color: var(--line) transparent; }` (forge-gen4.css:210), code-scroller uses #5c5d54
- **Selection**: `::selection { background: var(--ember-wash); color: var(--ink); }` (forge-gen4.css:53)
- **Caret**: `#editor { caret-color: #f3c4b3; }` (forge-gen4.css:109)
- **Meta theme-color**: `#20211e` (index.html:6)

## 9. Surfaces to Theme (from current UI)
All surfaces listed in spec exist. Key mappings:
- Header: `.topbar` (bg: --paper-bright, border: --line)
- Rail: `.activity-rail` (bg: --ink, border: #3b3b35)
- Sidebar: `.sidebar` (bg: --paper-panel)
- Panel heading: `.panel-heading` (border: --line)
- Tree rows: `.tree-row` (hover: #dfd8ca, selected: #e3cfc3, border-left: --ember)
- Editor: `.editor-surface` (bg: --ink-code), gutter (#6f7068), current-line (rgba), selection (#785041), caret (#f3c4b3)
- Tabs: `.tab` (active bg: --ink-code, underline: --ember)
- Bottom dock: `.bottom-dock` (bg: --ink)
- Statusbar: `.statusbar` (bg: --ember-deep)
- Command palette: `.command-palette` (bg: --paper-bright)
- Settings/Keys popups: `.floating-panel` (bg: --paper-panel)
- Tooltips, toasts, dropdowns, modals, scrims
- Buttons: primary (--ember), secondary, ghost, danger
- Skeletons, diff colors, badges, banners, links, kbd

## 10. Hard-coded Color Count (before migration)
**Estimated 200+ occurrences** across:
- forge-gen4.css: ~60 hard-coded (after variable substitution)
- components.css: ~20 (file icons + AI buttons)
- motion/motion.css: ~15
- motion/morph.js: ~5
- app.js: ~20 inline styles
- forge-smooth.js: ~3
- ai-settings.css: ~2
- tokens.css: ~80 (but not active)

**Total unique hard-coded hex/rgb values: ~45**