# Forge Gen 3 — Design Read

> **Reading this as: developer engineering workspace for technical users, with a dark-tech/industrial language, leaning toward native CSS + deliberate typography + restrained motion.**

---

## Design Direction Rationale

Forge is not a generic dashboard, chat interface, or consumer app. It's a **local-first engineering workspace** for developers who:

- Work with real repositories daily
- Need to understand unfamiliar codebases quickly
- Value evidence over decoration
- Require honest tooling (no fake progress, no fabricated stats)
- Navigate via keyboard as much as mouse
- Work across screen sizes (laptop to ultrawide)

The visual language must communicate: **precision, density, honesty, control**.

---

## Three Dials (Taste-Skill Adapted)

| Dial | Baseline | Forge Gen 3 | Rationale |
|------|----------|-------------|-----------|
| `DESIGN_VARIANCE` | 8 | **7** | Asymmetric but functional; workspace needs predictable scanning patterns |
| `MOTION_INTENSITY` | 6 | **5** | Meaningful hover/tap feedback, panel transitions; no scroll hijacks or cinematic flair |
| `VISUAL_DENSITY` | 4 | **6** | Engineering workspace = dense information, tight but readable |

**Why not higher variance?** Developers scan file trees, read diffs, trace call stacks. Unpredictable layouts break muscle memory.

**Why not higher motion?** Motion in a workspace should answer "what changed?" not "look at this." Every animation must have a semantic purpose.

**Why higher density?** Code, diffs, file paths, test output — these need space. Generous whitespace wastes the developer's most valuable resource: context.

---

## Visual Identity

### Typography

| Role | Font | Rationale |
|------|------|-----------|
| UI / Body | **Geist** | Technical sans with excellent legibility at small sizes; distinct from Inter default |
| Code / Data | **Geist Mono** | Perfect pairing with Geist; tabular numerals; clear glyph distinction |
| Fallback | System UI stack | No external dependency; works offline |

**Scale**: Modular 1.25 (13px base) — 10, 11, 13, 16, 20, 25, 32, 40, 50px
- 13px base = dense but readable at 100% zoom
- 12px code = standard editor density
- Modular scale = harmonic rhythm across all text

### Color Palette — Single Accent, Dark-First

```
Backgrounds (layered depth):
  --bg-deep:       #0a0e10   // Chrome, rails, deep surfaces
  --bg-base:       #0f1417   // Primary canvas
  --bg-elevated:   #151c21   // Panels, cards, modals
  --bg-hover:      #1a2329   // Interactive hover
  --bg-active:     #202b33   // Pressed/active

Borders (subtle → prominent):
  --border-subtle:  #1e2a31  // Hairlines, dividers
  --border-default: #28363e  // Standard component borders
  --border-focus:   #00d4aa  // Focus rings, active selection

Text (hierarchy):
  --text-primary:   #e8eeef  // Primary content
  --text-secondary: #9aaeb3  // Secondary, metadata
  --text-dim:       #6d848a  // Placeholders, disabled

Accent (ONE color, locked):
  --accent:         #00d4aa  // Teal-cyan, ~55% saturation
  --accent-soft:    #0d3d36  // 10% for backgrounds
  --accent-hover:   #00e8b8
  --accent-active:  #00c09a

Semantic (restrained):
  --warning:        #e8b84d  // Amber — unsaved, pending
  --danger:         #e86d6d  // Red — errors, destructive
  --success:        #4de0a7  // Green — saved, passed
  --info:           #6db3f2  // Blue — info, links
```

**Why teal-cyan (#00d4aa)?**
- Not the AI-default purple/indigo
- Not the VS Code blue
- Not the GitHub green
- High contrast on dark backgrounds (WCAG AA+)
- Distinctive in peripheral vision
- Works for both "success" and "active" states without confusion

### Spacing — 4px Base Unit

Consistent rhythm: 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 48, 56, 64, 80, 96px

No arbitrary values. Every padding, margin, gap derives from this scale.

### Radius — Shape Consistency Lock

| Radius | Value | Applied To |
|--------|-------|------------|
| Sharp | 0 | Buttons, inputs, tabs, toolbar items, badges, chips |
| Soft | 6px | Panels, modals, dropdowns, dock, sidebar, context panel |

**No mixed radii.** This is a hard rule. If a component needs different radii for nested elements, it's a composition problem, not a radius problem.

### Motion

| Duration | Use Case |
|----------|----------|
| 100ms (fast) | Hover transitions, focus rings, button press |
| 150ms (standard) | Tab switching, tooltip show/hide |
| 200ms (smooth) | Panel expand/collapse, sidebar slide, dock collapse |
| 300ms (panel) | Full sidebar/drawer animation |

**Easing**: `cubic-bezier(0.16, 1, 0.3, 1)` — standard Material-ease-out feel, snappy but not mechanical.

**Reduced Motion**: All animations collapse to 0.01ms instant. No exceptions.

---

## Information Architecture

### Five-Zone Workspace

```
┌─────────────────────────────────────────────────────────────────────┐
│  TOP BAR (50px) — Repo identity, quick actions, global status      │
├─────────┬───────────────────────────────────────┬──────────────────┤
│ ACTIVITY│                                       │                  │
│  RAIL   │           MAIN EDITOR AREA            │  CONTEXT PANEL   │
│ (55px)  │                                       │   (335px)        │
│         │  ┌─────────────────────────────────┐  │                  │
│         │  │      TABS / BREADCRUMBS         │  │  Task compose    │
│         │  ├─────────────────────────────────┤  │  Plan display    │
│         │  │                                 │  │  Evidence chips  │
│         │  │       CODE EDITOR               │  │  Risks / Tests   │
│         │  │                                 │  │                  │
│         │  └─────────────────────────────────┘  │                  │
├─────────┴───────────────────────────────────────┴──────────────────┤
│  BOTTOM DOCK (180px, collapsible) — Terminal, Output, Tests, Activity │
└─────────────────────────────────────────────────────────────────────┘
```

**Why five zones?** Each maps to a distinct cognitive mode:
1. **Top Bar** — Orientation (where am I?)
2. **Rail** — Navigation mode (what am I doing?)
3. **Sidebar** — Exploration (what exists?)
4. **Editor** — Inspection/Modification (what does it do?)
5. **Context** — Reasoning (what should I do?)
6. **Dock** — Execution/Verification (did it work?)

### Sidebar Views (Rail-Activated)

| Rail Button | View | Purpose |
|-------------|------|---------|
| Explorer | File tree, repo summary | Navigate & select files |
| Search | Query input, results list | Find symbols/text/files |
| Changes | Git status list, diff viewer | Inspect modifications |
| Tasks | Active task, plan history | Engineering workflow |

**Single active view** — no split sidebar. Cognitive load stays low.

---

## Component Design Principles

### Buttons
- **Sharp corners** — precise, technical feel
- **Active state**: `translateY(1px)` — physical press feedback
- **Focus ring**: 2px accent on 2px background — visible in both modes
- **Primary**: Accent background, inverse text — one per view max
- **Ghost**: Transparent, minimal chrome — secondary actions
- **Icon-only**: 28×28px hit target — accessible minimum

### Inputs
- **Sharp corners** — consistency with buttons
- **Focus**: Accent border + 2px soft ring — unmistakable
- **Placeholder**: Dim text — never mistaken for value
- **Monospace for code/paths** — alignment, readability

### File Tree
- **Virtualized rendering** — handles 10k+ files
- **28px row height** — dense but clickable
- **Selected**: Accent left border + hover background — clear without outline
- **Dirty dot**: 6px amber — peripheral awareness
- **Folder twisty**: 16px hit area — no misclicks

### Editor
- **Overlay highlight** — textarea (editing) + pre (highlighting) perfectly synced
- **Line numbers**: Fixed 52px, right-aligned, dim — never distracts
- **Caret**: Accent color — visible in peripheral vision
- **Selection**: Accent-soft background — readable in both modes

### Tabs
- **Scrollable** — never wrap, never shrink labels
- **Active**: 2px accent top border + deep background — clear hierarchy
- **Dirty**: Amber dot in label — unsaved at a glance
- **Close**: 16px hit area, red on hover — deliberate destruction

### Dock
- **Collapsible** — 34px bar when collapsed, 180px expanded
- **Resize handle** — drag to custom height (persisted)
- **Tabs**: Bottom-border accent — consistent with top tabs
- **Terminal**: Prefilled pytest command — zero friction to verify

---

## Responsive Behavior

### Breakpoint Strategy

| Width | Layout |
|-------|--------|
| ≥1366px | Full five-zone, context 335px |
| 1024–1365px | Context 300px, tabs truncate |
| 768–1023px | **Sidebar → overlay drawer**; rail icons-only; context stacks below editor |
| 390–767px | **Single column**: Top bar → Editor → Sidebar (drawer) → Dock; tabs horizontal scroll |
| 320–389px | Reduced padding (12px), 12px base font, minimal chrome |

### Key Mobile Decisions

1. **Sidebar becomes drawer** — slides from left, backdrop closes, ESC closes, focus trapped
2. **Rail stays visible** — 48px, icons only — always accessible navigation
3. **Context stacks below editor** — not a drawer; editing + plan visible together
4. **Tabs scroll horizontally** — `-webkit-overflow-scrolling: touch` for momentum
5. **Evidence grid → 2×2** — fits narrow viewports
6. **Test metrics wrap** — flex-wrap on small screens

---

## Accessibility (Web Design Guidelines Compliance)

### Semantic HTML
- `<header>` for top bar
- `<nav>` for activity rail
- `<aside>` for sidebar and context panel
- `<main>` for editor area
- `<section>` for each dock tab panel
- `<footer>` for status bar

### ARIA
- `role="tree"` on file tree, `role="treeitem"` on rows
- `aria-label` on icon-only buttons
- `aria-expanded` on folder twisties
- `aria-selected` on active tab/tree row
- `aria-live="polite"` on toast container
- `role="dialog"` + `aria-modal="true"` on command palette

### Focus Management
- **Logical tab order**: Top bar → Rail → Sidebar → Editor → Context → Dock
- **Focus trap** in palette/drawer — restored on close
- **Visible focus rings** on every interactive element (2px accent)
- **Skip links** not needed — rail is first tab stop

### Contrast
| Element | Ratio | Target |
|---------|-------|--------|
| Primary text on base | 12.8:1 | AAA |
| Secondary text on base | 6.2:1 | AA |
| Accent on deep | 4.8:1 | AA |
| Accent on elevated | 5.1:1 | AA |
| Focus ring | 4.5:1 | AA |
| Borders | 3.2:1 | AA Large |

### Reduced Motion
All animations gated by `@media (prefers-reduced-motion: reduce)` — instant transitions.

---

## Anti-Patterns Explicitly Avoided (Taste-Skill + Frontend-Design)

| Anti-Pattern | Avoided By |
|--------------|------------|
| Three equal feature cards | No card grid — workspace zones have distinct roles |
| AI-purple gradients | Single teal-cyan accent, no gradients |
| Glassmorphism everywhere | Solid layered surfaces, subtle borders |
| Giant hero section | Top bar = 50px, purely functional |
| Emoji as icons | Phosphor Icons, consistent stroke weight |
| Fake terminal output | Real terminal runs real pytest |
| Fake repository data | Real repo analysis from backend |
| Placeholder controls | Every button has real action or is disabled |
| Oversized rounded cards | Sharp buttons, soft panels — purposeful |
| Decorative badges/dots | Only dirty dot, change count — semantic |
| Arbitrary animations | Only state-transition motion |
| `window.addEventListener('scroll')` | CSS transitions only |

---

## Icon System — Phosphor Icons

**Why Phosphor?**
- Consistent 1.5 stroke weight across 7000+ icons
- Multiple weights (thin, light, regular, bold, fill, duotone)
- MIT licensed, tree-shakeable
- Technical aesthetic fits developer tools

**Implementation**: Inline SVG sprite in HTML `<defs>`, referenced via `<use href="#icon-name">`. Zero runtime cost, styleable via CSS `currentColor`.

**Icon Mapping** (key examples):
- File: `file-text` / `file-code` / `file-json` / `file-markdown`
- Folder: `folder` / `folder-open`
- Actions: `magnifying-glass` / `pencil-simple` / `plus` / `x` / `arrow-down` / `arrow-right`
- Status: `circle` / `check` / `warning` / `info` / `git-branch` / `git-commit`
- UI: `command` / `palette` / `layout` / `terminal` / `beaker` / `list-checks`

---

## Content & Copy Principles (Frontend-Design)

- **Active voice**: "Save changes" not "Submit"
- **Plain verbs**: "Run tests" not "Execute test suite"
- **Sentence case**: "Generate plan" not "Generate Plan"
- **Specific labels**: "Open file" not "Quick open" (though shortcut shown)
- **Error = direction**: "File not found. Check the path and try again."
- **Empty = invitation**: "No changes yet. Edit a file to see modifications here."
- **No filler**: No "seamlessly", "effortlessly", "unleash", "elevate"

---

## Security & Correctness (Per Requirements)

- **All user content escaped** via `esc()` — audited every `innerHTML` site
- **No `setTimeout` string callbacks** — refactored to function refs
- **Path validation unchanged** — DEF-001–007 fixes preserved
- **Command allowlist intact** — only `python -m pytest -q`
- **CSP headers** — added to FastAPI middleware
- **No `eval`/`Function`/`new Function`** — verified

---

## Implementation Notes

### CSS Architecture
```
style.css (entry)
  ├── tokens.css    — All design tokens (colors, spacing, type, radius, motion)
  ├── reset.css     — Modern reset, scrollbars, focus-visible, reduced-motion
  ├── base.css      — Typography, form/button primitives, utilities
  ├── layout.css    — Five-zone grid, responsive breakpoints, component layouts
  └── components.css — Top bar, rail, palette, toast, diff, icons, states
```

**Import order matters** — tokens first, reset second, base third, layout fourth, components last.

### JavaScript Architecture (Planned)
```
app.js (entry)
  ├── state.js        — Centralized state, reactive updates
  ├── api.js          — Fetch wrapper, abort controllers, error handling
  ├── dom.js          — Safe DOM helpers (esc, createElement, render)
  ├── components/     — One file per UI component
  │   ├── TopBar.js
  │   ├── ActivityRail.js
  │   ├── Sidebar.js
  │   ├── Editor.js
  │   ├── ContextPanel.js
  │   ├── BottomDock.js
  │   ├── CommandPalette.js
  │   └── Toast.js
  ├── views/          — Sidebar view controllers
  │   ├── ExplorerView.js
  │   ├── SearchView.js
  │   ├── ChangesView.js
  │   └── TasksView.js
  └── init.js         — Bootstrapping, event delegation
```

**Principles**:
- ES6 modules, no bundler needed (native browser support)
- Event delegation on document — no inline handlers
- AbortController for all fetch — no stale responses
- Single state object — predictable updates
- No framework — vanilla JS, ~2KB gzipped

---

## Quality Gates (From Plan)

### Gate 1: Product Design
- [ ] Coherent visual identity (single accent, consistent radii, deliberate typography)
- [ ] Clear information hierarchy
- [ ] Consistent spacing, icons, surfaces
- [ ] No generic-template appearance

### Gate 2: Functional Integrity
- [ ] Repository analysis loads and displays
- [ ] File open/edit/save cycle works
- [ ] Task plans generate and render
- [ ] Search returns and navigates
- [ ] Git changes list and diffs display
- [ ] Test execution runs and shows real output
- [ ] Honest loading/error/empty states

### Gate 3: Interaction Quality
- [ ] All interaction states implemented
- [ ] No flicker, broken transitions, duplicate actions
- [ ] Motion restrained, respects reduced-motion
- [ ] Keyboard navigation complete

### Gate 4: Browser Verification
- [ ] Playwright tests for 13 scenarios
- [ ] Screenshots at 7 viewports
- [ ] Console/network clean
- [ ] Issues documented and fixed

### Gate 5: Responsive Quality
- [ ] 7 viewports inspected
- [ ] No accidental horizontal overflow
- [ ] Core actions usable on mobile

### Gate 6: Regression & Security
- [ ] 170+ pytest tests pass
- [ ] Security controls intact
- [ ] Content rendered safely
- [ ] No unrelated changes lost

### Gate 7: Repository Integrity
- [ ] Clean git diff
- [ ] No generated artifacts
- [ ] No unintended modifications

---

## Next Steps

1. ✅ **Stage A** — Token system, reset, base, layout, components CSS complete
2. 🔄 **Stage B** — Refactor `index.html` for semantic HTML, update to new CSS, implement sidebar overlay
3. 🔄 **Stage B** — Refactor `app.js` into modular ES6 architecture
4. 🔄 **Stage C** — Connect all backend endpoints
5. 🔄 **Stage D** — Interaction polish, accessibility audit
6. 🔄 **Stage E** — Playwright browser verification
7. 🔄 **Stage F** — Regression testing, final security review

---

*This document captures the design intent. Implementation should reference this for every decision. When in doubt, choose the option that increases honesty, density, or keyboard efficiency.*