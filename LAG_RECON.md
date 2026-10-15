# LAG_RECON.md — Forge Flow & Wait Inventory

## Task A2: File Verification
- `forge-fx.js`: 12,985 bytes (Present)
- `forge-fx-config.js`: 1,038 bytes (Present)
- `forge-flow.js`: 15,313 bytes (Present)
- `forge-motion.css`: 718 bytes (Present)

---

## Task A3: Flow Inventory Table

| Flow Name | Panel Selector | Trigger Selector | Type | Open Function (file:line) | Close Function (file:line) |
|---|---|---|---|---|---|
| `side` | `#sidebar` (`$("sidebar")`) | `.rail-button[data-view="explorer"]` (or active rail btn) | **IN-FLOW** (Grid child of `#workbench`, col 2; pushes `#main-content`) | `setSidebarOpen(true, triggerEl)` (`app/static/app.js:805`) | `setSidebarOpen(false)` (`app/static/app.js:805`) |
| `dock` | `#bottom-dock` (`$("bottom-dock")`) | `.dock-bar` / `#dock-toggle` (`$("dock-toggle")`) | **IN-FLOW** (Grid child of `#main-content`, row 2; pushes editor) | `openDock()` (`app/static/app.js:1330`) | `closeDock()` (`app/static/app.js:1346`) |
| `settings` | `#settings-panel` (`$("settings-panel")`) | `.rail-button[data-view="settings"]` | **OVERLAY** (`position: fixed; left: 58px; bottom: 16px;`) | `openSettings()` (`app/static/app.js:826`) | `closeSettings()` (`app/static/app.js:836`) |
| `keys` | `#keys-panel` (`$("keys-panel")`) | `#help` (`$("help")`) | **OVERLAY** (`position: fixed; left: 58px; bottom: 58px;`) | `openKeys()` (`app/static/app.js:849`) | `closeKeys()` (`app/static/app.js:860`) |
| `palette` | `.command-palette` (`paletteDialog`) | `#quick-open` (`$("quick-open")`) / `#command-open` | **OVERLAY** (`#modal-backdrop` fixed inset 0) | `openPalette(mode)` (`app/static/app.js:1313`) | `closePalette()` (`app/static/app.js:1273`) |

---

## Task A4: Open and Close Functions Source (and Callees up to 2 Levels Deep)

### 1. `side` (`#sidebar`)
```javascript
// Open: setSidebarOpen(true, triggerEl) [app.js:805]
function setSidebarOpen(open, triggerEl) {
  const compact = window.matchMedia("(max-width: 1110px)").matches;
  const sidebar = $("sidebar");
  const workbench = $("workbench");

  if (open) {
    sidebar.classList.toggle("is-open", true);
    sidebar.classList.toggle("is-collapsed", false);
    if (workbench) workbench.classList.remove("explorer-is-collapsed");
    $("sidebar-scrim").hidden = !compact;
    $("explorer-open").hidden = true;

    const trigger = triggerEl || document.querySelector(`.rail-button[data-view="${state.activeView}"]`) || document.querySelector('.rail-button[data-view="explorer"]');
    sideFlow?.to(1, trigger);
  } else {
    sideFlow?.to(0);
  }
}

// Close: setSidebarOpen(false) [app.js:805]
// Hiding currently deferred to sideFlow.onSettle('closed'):
onSettle: function (state) {
  if (state === 'closed') {
    const sidebar = $("sidebar");
    const workbench = $("workbench");
    sidebar.classList.remove("is-open");
    sidebar.classList.add("is-collapsed");
    if (workbench) workbench.classList.add("explorer-is-collapsed");
    $("sidebar-scrim").hidden = true;
    $("explorer-open").hidden = false;
  }
}

// Callees / Related:
// Level 1: isSidebarVisible() [app.js:797]
function isSidebarVisible() {
  if (sideFlow && sideFlow.live) {
    return sideFlow.p.target === 1;
  }
  const sidebar = $("sidebar");
  return Boolean(sidebar && sidebar.classList.contains("is-open") && !sidebar.classList.contains("is-collapsed"));
}

// Level 1: setView(view, { focus }) [app.js:1074]
// Calls setSidebarOpen(true) if !isSidebarVisible(), or switchSideView() if already open
```

### 2. `dock` (`#bottom-dock`)
```javascript
// Open: openDock() [app.js:1330]
function openDock() {
  const dock = $("bottom-dock");
  if (!dock) return;
  dock.classList.remove("is-collapsed");
  dock.style.height = "190px";
  $("dock-toggle").setAttribute("aria-expanded", "true");
  $("dock-toggle").setAttribute("aria-label", "Collapse verification panel");
  const toggleSvg = $("dock-toggle").querySelector("svg");
  if (toggleSvg) {
    toggleSvg.style.transition = "transform var(--t-fast, 160ms) var(--ease-out)";
    toggleSvg.style.transform = "rotate(180deg)";
  }
  const trigger = document.querySelector(".dock-bar") || $("dock-toggle");
  dockFlow?.to(1, trigger);
}

// Close: closeDock() [app.js:1346]
function closeDock() {
  $("dock-toggle").setAttribute("aria-expanded", "false");
  $("dock-toggle").setAttribute("aria-label", "Expand verification panel");
  const toggleSvg = $("dock-toggle").querySelector("svg");
  if (toggleSvg) {
    toggleSvg.style.transition = "transform var(--t-fast, 160ms) var(--ease-out)";
    toggleSvg.style.transform = "rotate(0deg)";
  }
  dockFlow?.to(0);
}

// Hiding currently deferred to dockFlow.onSettle('closed'):
onSettle: function (state) {
  if (state === 'closed') {
    const dock = $("bottom-dock");
    if (dock) {
      dock.classList.add("is-collapsed");
      dock.style.height = "";
    }
  }
}

// Callees / Related:
// toggleDock() [app.js:1357]
function toggleDock() {
  const dock = $("bottom-dock");
  const isCurrentlyCollapsed = dock.classList.contains("is-collapsed");
  if (isCurrentlyCollapsed) {
    openDock();
  } else {
    closeDock();
  }
}
```

### 3. `settings` (`#settings-panel`)
```javascript
// Open: openSettings() [app.js:826]
function openSettings() {
  const panel = $("settings-panel");
  if (!panel) return;
  panel.hidden = false;
  panel.classList.add("is-open");
  const btn = document.querySelector('.rail-button[data-view="settings"]');
  if (btn) btn.classList.add("is-popup-open");
  settingsFlow?.to(1, btn);
}

// Close: closeSettings() [app.js:836]
function closeSettings() {
  settingsFlow?.to(0);
}

// onSettle('closed') hides panel and removes classes [app.js:1684]
```

### 4. `keys` (`#keys-panel`)
```javascript
// Open: openKeys() [app.js:849]
function openKeys() {
  if (settingsFlow && settingsFlow.p.target === 1) closeSettings();
  const panel = $("keys-panel");
  if (!panel) return;
  panel.hidden = false;
  panel.classList.add("is-open");
  const btn = $("help");
  if (btn) btn.classList.add("is-popup-open");
  keysFlow?.to(1, btn);
}

// Close: closeKeys() [app.js:860]
function closeKeys() {
  keysFlow?.to(0);
}

// onSettle('closed') hides panel and removes classes [app.js:1714]
```

### 5. `palette` (`.command-palette`)
```javascript
// Open: openPalette(mode) [app.js:1313]
function openPalette(mode = "commands") {
  state.returnFocus = document.activeElement;
  const backdrop = $("modal-backdrop");
  backdrop.hidden = false;
  backdrop.style.opacity = "1";
  $("palette-title").textContent = mode === "files" ? "OPEN LOCAL FILE" : "COMMAND PALETTE";
  $("palette-input").placeholder = mode === "files" ? "Filter repository files..." : "Find an action...";
  $("palette-input").value = "";
  $("palette-input").dataset.mode = mode;
  renderPalette("", mode);

  const trigger = $("quick-open") || $("command-open") || document.body;
  paletteFlow?.to(1, trigger);
  $("palette-input").focus();
}

// Close: closePalette() [app.js:1273]
function closePalette() {
  paletteFlow?.to(0);
}

// onSettle('closed') hides modal-backdrop and restores focus [app.js:1813]
```

---

## Task A5: Waits and Delay Inventory

| File:Line | Code / Keyword | Classification | Analysis |
|---|---|---|---|
| `app/static/app.js:198` | `setTimeout(..., 110)` | **Harmless** | Boot transition lock-in timer; runs once during initial page boot. |
| `app/static/app.js:310` | `setTimeout(..., 250)` | **Harmless** | Fallback boot transition completion; only runs during initial load if boot progress < 99.5%. |
| `app/static/app.js:328` | `setTimeout(..., 3600)` | **Harmless** | Toast auto-hide timeout after toast message displayed. |
| `app/static/app.js:1410` | `setTimeout(..., 100)` | **Harmless** | Tab removal flip animation delay when closing an editor file. |
| `app/static/app.js:1499` | `setTimeout(..., 180)` | **Harmless** | Debounce timer for repository text search input (`state.searchTimer`). |
| `app/static/app.js:1113` | `if (view === "changes") loadChanges()` | **Harmless** | Unawaited async call fetching `/api/changes`; does not block click or `setSidebarOpen`. |
| `app/static/app.js:1536-1545` | `$("sidebar-resize").addEventListener("pointermove", ...)` | **Harmless** | Manual drag resizing of sidebar width; does not trigger during panel open/close. |
| `app/static/motion/badge.js:81` | `setTimeout(..., 160)` | **Harmless** | Badge roll animation digit swap. |
| `app/static/motion/morph.js:101` | `setTimeout(..., 380)` | **Harmless** | Disconnected legacy morph landing class cleanup. |
| `app/static/motion/morph.js:395` | `setTimeout(..., 340)` | **Harmless** | Disconnected legacy morph clone removal. |
| `app/static/motion/scheduler.js:44` | `requestAnimationFrame` | **Potential Hazard** | Legacy motion scheduler runs RAF loop if any tasks registered. |
| `app/static/app.js:1339, 1351` | `toggleSvg.style.transition = "... 160ms ..."` | **Harmless** | CSS transition on dock arrow SVG rotation (visual only, no transitionend listener). |

*Note on Wait Findings:*
No `transitionend`, `animationend`, or `.finished` listeners exist in the active panel open/close paths.
However, in-flow panels (`#sidebar`, `#bottom-dock`) currently defer their grid/layout collapse until `onSettle('closed')`, leaving an empty space in the layout while the animation plays.
Task D Snap Mode (`ForgeFlow.pullOut` + instant layout collapse on close) directly resolves this.
