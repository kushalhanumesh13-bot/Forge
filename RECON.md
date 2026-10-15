# RECON: Forge Motion Upgrade

## A1. Project Structure & Scripts
- **HTML Template:** `app/static/index.html` (served by FastAPI at `app/main.py:18` via `FileResponse(static_dir / "index.html")`).
- **Static JS:** `app/static/app.js`, `app/static/motion/*.js`
- **Static CSS:** `app/static/style.css` (imports `forge-gen4.css`), `app/static/ai-settings.css`, `app/static/motion/motion.css`
- **Script Loading Order in `index.html`:**
  - `<link rel="stylesheet" href="/static/style.css">`
  - `<link rel="stylesheet" href="/static/ai-settings.css">`
  - `<link rel="stylesheet" href="/static/motion/motion.css?v=20261015-1">`
  - Body scripts: `<script type="module" src="/static/app.js?v=20261015-1"></script>` (no defer/async; ES module)

---

## A2. JS and CSS Inventory
| File | Lines | Role |
|---|---|---|
| `app/static/app.js` | 1538 | **Main App Script** |
| `app/static/style.css` | 1 | **Main Stylesheet** (imports `forge-gen4.css`) |
| `app/static/forge-gen4.css` | 241 | Primary app styling, tokens & layout |
| `app/static/motion/motion.css` | 500 | Existing motion tokens, sliding indicators & overrides |
| `app/static/ai-settings.css` | 111 | AI Settings popup styling |
| `app/static/motion/morph.js` | 332 | Existing morph panel engine |
| `app/static/motion/presence.js` | 72 | Modal and dialog presence animation |
| `app/static/motion/scheduler.js` | 112 | rAF animation loop |
| `app/static/motion/spring.js` | 80 | 1D and Multi-D spring solvers |
| `app/static/motion/stack.js` | 96 | Surface stacking and ESC/outside-click manager |
| `app/static/motion/indicator.js` | 123 | Sliding indicator implementation |
| `app/static/motion/debug.js` | 570 | Dev motion overlay & profiling |
| `app/static/motion/config.js` | 184 | Motion stiffness/damping presets |
| `app/static/motion/outline.js` | 108 | Geometry and outline helpers |
| `app/static/motion/badge.js` | 86 | Review count digit roller |
| `app/static/motion/flip.js` | 53 | FLIP list reordering |
| `app/static/motion/index.js` | 149 | Motion system entry exports |
| `app/static/motion.js` | 4 | Legacy shim |
| `app/static/base.css` | 824 | Legacy base styles |
| `app/static/components.css` | 925 | Legacy component styles |
| `app/static/layout.css` | 1206 | Legacy layout styles |
| `app/static/motion.css` | 52 | Legacy motion styles |
| `app/static/reset.css` | 186 | Legacy reset styles |
| `app/static/tokens.css` | 266 | Legacy tokens |

---

## A3. Animation Keywords & Current Panel Opening Animation
- **Current Panel Opening Animation:**
  - Located in: `app/static/motion/morph.js:251-292` (`MorphPanel.renderProgress()`), which calculates scale and translation between trigger and panel geometry, and in lines 258-267 animates `--explorer-width` from `0` to `274px` on `#workbench` for `#sidebar`.
  - Also in `app/static/motion/presence.js:40-70` for Command Palette dialog.

---

## A4. Left Rail Icons (6 items)
| Icon | HTML Tag | Selector | Creation | Click Handler Function |
|---|---|---|---|---|
| Explore | `<button>` | `.rail-button[data-view="explorer"]` | Static HTML | `setView("explorer")` or `setSidebarOpen(false)` if already open |
| Search | `<button>` | `.rail-button[data-view="search"]` | Static HTML | `setView("search")` or `setSidebarOpen(false)` if already open |
| Review | `<button>` | `.rail-button[data-view="changes"]` | Static HTML | `setView("changes")` or `setSidebarOpen(false)` if already open |
| Plan | `<button>` | `.rail-button[data-view="tasks"]` | Static HTML | `setView("tasks")` or `setSidebarOpen(false)` if already open |
| Settings | `<button>` | `.rail-button[data-view="settings"]` | Static HTML | `settingsMorph.toggle()` |
| Keys | `<button>` | `.rail-button#help` | Static HTML | `keysMorph.toggle()` |

---

## A5. Side Panel (`#sidebar`)
1. **Selector:** `#sidebar` (`aside.sidebar#sidebar`)
2. **Layout flow vs Overlay:** **IN THE LAYOUT FLOW** on desktop (>1110px). `#workbench` CSS grid uses `grid-template-columns: 58px var(--explorer-width) minmax(0, 1fr) ...`. The code editor (column 3) gets narrower when the sidebar opens. On mobile (<=1110px) it switches to a fixed overlay (`position: fixed; left: 56px; width: min(340px, calc(100vw - 56px)); transform: translateX(-110%)`).
3. **Open and close functions:**
   - Open: `setSidebarOpen(true)` in `app/static/app.js:800` (and `sidebarMorph.open()`).
   - Close: `setSidebarOpen(false)` in `app/static/app.js:800` (and `sidebarMorph.close()`).
4. **How it is hidden when closed:**
   - `.workbench.classList.add("explorer-is-collapsed")` (column 2 = 0px).
   - `.sidebar.classList.add("is-collapsed")` (`visibility: hidden; opacity: 0;`).
   - `.sidebar.classList.remove("is-open")`.
   - `--explorer-width: 0px`.
5. **Exact old animation:** `sidebarMorph` in `app/static/motion/morph.js:258-267` animating `--explorer-width` from `0` to `274px` and opacity from $0 \to 1$ via Spring in `scheduler.js`.
6. **How X button closes it:** `$("sidebar-close").addEventListener("click", () => setSidebarOpen(false));` in `app/static/app.js:1504`.
7. **How second click on same icon closes it:** `app/static/app.js:1495-1497`: `if (view === state.activeView && isSidebarVisible()) { setSidebarOpen(false); return; }`.

---

## A6. All Other Surfaces That Open / Close
| Surface | Trigger Selector | Surface Selector | Open Function | Close Function | Hide Method |
|---|---|---|---|---|---|
| Settings popup | `.rail-button[data-view="settings"]` | `#settings-panel` (`.floating-panel#settings-panel`) | `settingsMorph.open()` / `toggle()` | `settingsMorph.close()` / `#settings-close` / Esc / outside click | `panel.hidden = true; panel.classList.remove("is-open")` |
| Keys popup | `.rail-button#help` | `#keys-panel` (`.floating-panel#keys-panel`) | `keysMorph.open()` / `toggle()` | `keysMorph.close()` / `#keys-close` / Esc / outside click | `panel.hidden = true; panel.classList.remove("is-open")` |
| Bottom Verification Dock | `#dock-toggle` (or `.dock-bar`) | `#bottom-dock` (`.bottom-dock`) | `toggleDock()` | `toggleDock()` | `dock.classList.add("is-collapsed")` (height collapses to 41px, `.dock-content` hidden) |
| Command Palette | `#quick-open` ("Open Ctrl P") / `#command-open` / Ctrl+P / Ctrl+Shift+P | `.command-palette` inside `#modal-backdrop` | `openPalette()` | `closePalette()` / `#palette-close` / Esc / backdrop click | `#modal-backdrop.hidden = true` |
| Context Panel (Decision Thread) | `#context-open` / Plan tab | `#context-panel` (`.context-panel`) | `setContextOpen(true)` | `setContextOpen(false)` / `#context-close` | `workbench.classList.add("context-is-minimized")`, `panel.classList.add("is-minimized")` |
| Find in File strip | `#find-file` / Ctrl+F in editor | `#file-find` (`.find-strip#file-find`) | `showFind()` | `hideFind()` / `#file-find-close` / Esc | `hidden = true` |

---

## A7. Color Values
| Role | CSS Variable / Source | Exact Value |
|---|---|---|
| Accent (active step underline) | `--ember` (`app/static/forge-gen4.css:14`) | `#bd492d` (deep: `#92341f`) |
| Side-panel background (beige) | `--paper-panel` / `--surface-explorer` (`app/static/forge-gen4.css:3, 195`) | `#ebe4d8` |
| Rail background (dark) | `--surface-rail` / `--ink` (`app/static/forge-gen4.css:7, 196`) | `#20211e` |
| Selected rail icon tile color | `.rail-indicator` (`app/static/motion/motion.css:106`) | `rgba(255, 255, 255, 0.08)` over `#20211e` ($\approx$ `#323330`). Selected border mark uses `--ember` (`#bd492d`). Note: as instructed in Task C, since `#323330` is nearly the same dark color as the rail `#20211e`, we use the app's accent `#bd492d` for `--flow-accent`. |

---

## A8. UI Element Creation & Selectors
| UI Element | Creation | Selector |
|---|---|---|
| File-tree rows | JS-generated (`renderTree()`) | `.tree-row` (or `#tree .tree-row`) |
| Editor tabs | JS-generated (`renderTabs()`) | `.tab` (or `#tabs .tab`) |
| Top step items (01..05) | Static HTML | `.journey-step` (or `.journey .journey-step`) |
| Open Ctrl P button | Static HTML | `#quick-open` (`.command-trigger#quick-open`) |
| Header icons (glasses, refresh) | Static HTML | `#command-open`, `#refresh` (`.icon-button#command-open`, `.icon-button#refresh`) |
| Ready / status | Static HTML | `.connection` |
| Find button | Static HTML | `#find-file` (`.text-action#find-file`) |
| Save button | Static HTML | `#save` (`.save-action#save`) |
| Panel X close buttons | Static HTML | `#sidebar-close, #settings-close, #keys-close, #context-close, #palette-close, #file-find-close` |
| Tooltip/keyboard hints | Static HTML | `kbd`, `[title]`, `.statusbar span` |

---

## A9. CSS Rules That Could Fight Feedback System
1. `app/static/forge-gen4.css:226`:
   ```css
   .icon-button:active:not(:disabled) { transform: translateY(1px); transition: transform var(--t-instant) var(--ease-out); }
   ```
2. `app/static/forge-gen4.css:227`:
   ```css
   .rail-button:active:not(:disabled) { transform: scale(0.98); transition: transform var(--t-instant) var(--ease-out); }
   ```
3. `app/static/forge-gen4.css:228`:
   ```css
   .tab:active:not(:disabled) { transform: scale(0.99); transition: transform var(--t-instant) var(--ease-out); }
   ```
4. `app/static/forge-gen4.css:229`:
   ```css
   .command-trigger:active:not(:disabled) { transform: scale(0.99); transition: transform var(--t-instant) var(--ease-out); }
   ```
5. `app/static/forge-gen4.css:230`:
   ```css
   .save-action:active:not(:disabled) { transform: scale(0.99); transition: transform var(--t-instant) var(--ease-out); }
   ```
6. `app/static/motion/motion.css:149-152`:
   ```css
   .rail-button.is-pressed { transform: scale(0.94) !important; transition: transform 80ms var(--ease-out) !important; }
   ```
7. `app/static/motion/motion.css:473-477`:
   ```css
   .rail-button.is-pressed, .tree-row:active { transform: none !important; transition: none !important; }
   ```
8. Container overflow:
   - `.tabs` has `overflow-x: auto; overflow-y: hidden;` in `forge-gen4.css:75` (tabs have soft feedback with 1.02 pop, but will ensure tab strip allows 4px vertical clearance).
   - `.activity-rail`, `.topbar`, and `.stage-toolbar` do NOT have `overflow: hidden`.
