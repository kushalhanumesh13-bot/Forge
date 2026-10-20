# FROZEN MORPH RECORD

## 0.2 File Hashes
- app/static/forge-flow.js: 80980697763addb04ce60fabb95185bbcbc26a426d3bd1d13630a2d4a7bc096c
- app/static/forge-fx.js: af151fc334eb7abb1b456722a4238982aafa6b54f63d70d0b475d41848e87f54

## 0.3 Frozen App Code

### a) Every ForgeFlow.attach({Ellipsis}) Block Complete

#### app.js:1672-1691 (sideFlow)
`javascript
  sideFlow = window.ForgeFlow.attach({
    name: 'side',
    panel: $("sidebar"),
    trigger: document.querySelector('.rail-button[data-view="explorer"]') || document.querySelector('.rail-button'),
    knobs: { open: [0.38, 0.88], close: [0.28, 0.92], neck: 0.10, lag: 0.10, stretch: 0.02, wobble: 0.01, shadow: false, edgeN: 8, cornerN: 6 },
    onSettle: function (state) {
      const sidebar = $("sidebar");
      if (state === 'closed') {
        sidebar.classList.remove("is-open");
        sidebar.classList.add("is-collapsed");
        if (window.ForgeFlow && window.ForgeFlow.restore) {
          window.ForgeFlow.restore(sidebar);
        }
      } else {
        if (window.ForgeFlow && window.ForgeFlow.restore) {
          window.ForgeFlow.restore(sidebar);
        }
      }
    }
  });
`

#### app.js:1712-1731 (settingsFlow)
`javascript
  settingsFlow = window.ForgeFlow.attach({
    name: 'settings',
    panel: $("settings-panel"),
    trigger: document.querySelector('.rail-button[data-view="settings"]'),
    knobs: { open: [0.34, 0.86], close: [0.26, 0.92], neck: 0.10, lag: 0.10, stretch: 0.02, wobble: 0.01 },
    onSettle: function (state) {
      if (state === 'closed') {
        const p = $("settings-panel");
        if (p) {
          p.hidden = true;
          p.classList.remove("is-open");
        }
        const btn = document.querySelector('.rail-button[data-view="settings"]');
        if (btn) {
          btn.classList.remove("is-popup-open");
          btn.focus();
        }
      }
    }
  });
`

#### app.js:1745-1764 (keysFlow)
`javascript
  keysFlow = window.ForgeFlow.attach({
    name: 'keys',
    panel: $("keys-panel"),
    trigger: $("help"),
    knobs: { open: [0.34, 0.86], close: [0.26, 0.92], neck: 0.10, lag: 0.10, stretch: 0.02, wobble: 0.01 },
    onSettle: function (state) {
      if (state === 'closed') {
        const p = $("keys-panel");
        if (p) {
          p.hidden = true;
          p.classList.remove("is-open");
        }
        const btn = $("help");
        if (btn) {
          btn.classList.remove("is-popup-open");
          btn.focus();
        }
      }
    }
  });
`

#### app.js:1767-1781 (dockFlow)
`javascript
  dockFlow = window.ForgeFlow.attach({
    name: 'dock',
    panel: $("bottom-dock"),
    trigger: document.querySelector(".dock-bar") || $("dock-toggle"),
    knobs: { open: [0.38, 0.88], close: [0.28, 0.92], neck: 0.10, lag: 0.10, stretch: 0.02, wobble: 0.01 },
    onSettle: function (state) {
      if (state === 'closed') {
        const dock = $("bottom-dock");
        if (dock) {
          dock.classList.add("is-collapsed");
          dock.style.height = "";
        }
      }
    }
  });
`

#### app.js:1847-1860 (paletteFlow)
`javascript
    paletteFlow = window.ForgeFlow.attach({
      name: 'palette',
      panel: paletteDialog,
      trigger: $("quick-open") || $("command-open") || document.body,
      knobs: { open: [0.34, 0.86], close: [0.26, 0.92], neck: 0.10, lag: 0.10, stretch: 0.02, wobble: 0.01 },
      onSettle: function (state) {
        if (state === 'closed') {
          const backdrop = $("modal-backdrop");
          if (backdrop) backdrop.hidden = true;
          if (state.returnFocus) state.returnFocus.focus();
          state.returnFocus = null;
        }
      }
    });
`

---

### b) Every Open and Close Function Calling flow.to(...)

#### app.js:808-843 (setSidebarOpen)
`javascript
function setSidebarOpen(open, triggerEl) {
  const compact = window.matchMedia("(max-width: 1110px)").matches;
  const sidebar = $("sidebar");
  const workbench = $("workbench");

  if (open) {
    const trigger = triggerEl || document.querySelector(`.rail-button[data-view="${state.activeView}"]`) || document.querySelector('.rail-button[data-view="explorer"]');
    const tgRect = trigger ? trigger.getBoundingClientRect() : null;

    sidebar.classList.toggle("is-open", true);
    sidebar.classList.toggle("is-collapsed", false);
    if (workbench) workbench.classList.remove("explorer-is-collapsed");
    $("sidebar-scrim").hidden = !compact;
    $("explorer-open").hidden = true;

    sideFlow?.to(1, trigger, tgRect);
  } else {
    // 1) FIRST LINE: take panel out of layout, still visible
    if (window.ForgeFlow && window.ForgeFlow.pullOut) {
      window.ForgeFlow.pullOut(sidebar);
    }

    // 2) app logic, synchronous: collapse layout space (do not hide panel here)
    if (workbench) workbench.classList.add("explorer-is-collapsed");
    $("sidebar-scrim").hidden = true;
    $("explorer-open").hidden = false;

    // 3) soften main editor element
    if (window.ForgeFlow && window.ForgeFlow.soften) {
      window.ForgeFlow.soften($("main-content"), 240);
    }

    // 4) animation
    sideFlow?.to(0);
  }
}
`

#### app.js:845-857 (openSettings / closeSettings)
`javascript
function openSettings() {
  const panel = $("settings-panel");
  if (!panel) return;
  panel.hidden = false;
  panel.classList.add("is-open");
  const btn = document.querySelector('.rail-button[data-view="settings"]');
  if (btn) btn.classList.add("is-popup-open");
  settingsFlow?.to(1, btn);
}

function closeSettings() {
  settingsFlow?.to(0);
}
`

#### app.js:868-881 (openKeys / closeKeys)
`javascript
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

function closeKeys() {
  keysFlow?.to(0);
}
`

#### app.js:1302-1304 (closePalette) & app.js:1342-1357 (openPalette)
`javascript
function closePalette() {
  paletteFlow?.to(0);
}

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
`

#### app.js:1359-1394 (openDock / closeDock / toggleDock)
`javascript
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

function toggleDock() {
  const dock = $("bottom-dock");
  const isCurrentlyCollapsed = dock.classList.contains("is-collapsed");
  if (isCurrentlyCollapsed) {
    openDock();
  } else {
    closeDock();
  }
}
`

---

### c) .ff-active Rules and --flow-accent Line from forge-motion.css

#### forge-motion.css:1
`css
:root { --flow-accent: #bd492d; } /* Forge ember accent color from forge-gen4.css */
`

#### forge-motion.css:10-18
`css
.ff-active {
  background: transparent !important;
  box-shadow: none !important;
  border-color: transparent !important;
  /* old code, disconnected by lag fix: will-change: clip-path; */
  contain: layout paint;
}
`

---

### d) Loading-Screen -> Home Transition Code

#### app.js:95-324 (setBoot through showBootFailure)
`javascript
function setBoot(label, detail) {
  $("boot-label").textContent = label;
  $("boot-detail").textContent = detail;
}

function renderBootProgress(progress) {
  const offset = 200 * (1 - progress / 100);
  document.querySelectorAll(".boot-perimeter-progress").forEach((path) => {
    path.style.strokeDashoffset = offset;
  });
}

function animateBootProgress(time) {
  bootMotion.frame = 0;
  const elapsed = bootMotion.lastTime ? Math.min(64, time - bootMotion.lastTime) : 16;
  bootMotion.lastTime = time;
  const stageElapsed = bootMotion.stageStartedAt ? Math.max(0, time - bootMotion.stageStartedAt) : 0;
  const inStageTarget = state.bootReady
    ? 100
    : Math.min(bootMotion.stageCap, bootMotion.confirmed + (stageElapsed / 1000) * 8);
  const remaining = inStageTarget - bootMotion.displayed;
  if (Math.abs(remaining) < 0.05) {
    bootMotion.displayed = inStageTarget;
  } else {
    const response = state.bootReady ? 90 : 180;
    bootMotion.displayed += remaining * (1 - Math.exp(-elapsed / response));
  }
  if (Math.abs(inStageTarget - bootMotion.displayed) < 0.05) {
    bootMotion.displayed = inStageTarget;
  }
  bootProgress = bootMotion.displayed;
  renderBootProgress(bootMotion.displayed);
  const stageIsActive = !state.bootReady && bootMotion.displayed < bootMotion.stageCap - 0.05;
  if (Math.abs(inStageTarget - bootMotion.displayed) >= 0.05 || stageIsActive) {
    bootMotion.frame = window.requestAnimationFrame(animateBootProgress);
    return;
  }
  bootMotion.lastTime = 0;
  if (bootMotion.displayed >= 100 && state.bootReady) {
    bootProgress = 100;
    completeBootTransition();
  }
}

function resetBootProgress() {
  if (bootMotion.frame) window.cancelAnimationFrame(bootMotion.frame);
  bootMotion.frame = 0;
  bootMotion.lastTime = 0;
  bootMotion.displayed = 0;
  bootMotion.confirmed = 0;
  bootMotion.stageCap = 0;
  bootMotion.stageStartedAt = 0;
  bootProgress = 0;
  renderBootProgress(0);
}

function setBootProgress(progress) {
  if (!state.booting) return;
  const nextProgress = Math.max(0, Math.min(100, progress));
  if (nextProgress < bootMotion.confirmed) return;
  bootMotion.confirmed = nextProgress;
  if (!bootMotion.frame) bootMotion.frame = window.requestAnimationFrame(animateBootProgress);
}

function beginBootStage(index) {
  if (!state.booting) return;
  currentBootStage = Math.min(index, bootStages.length - 1);
  const stage = bootStages[currentBootStage];
  setBoot(stage.label, stage.detail);
  bootMotion.stageCap = Math.max(bootMotion.confirmed, stage.cap);
  bootMotion.stageStartedAt = performance.now();
  if (!bootMotion.frame) bootMotion.frame = window.requestAnimationFrame(animateBootProgress);
}

function completeBootStage() {
  setBootProgress(bootStages[currentBootStage].progress);
}

function completeBootTransition() {
  if (bootMotion.frame) { window.cancelAnimationFrame(bootMotion.frame); bootMotion.frame = 0; }
  const screen = $("boot-screen");
  const app = $("forge-app");
  if (state.transitioning) return;
  state.transitioning = true;
  document.body.classList.add("workspace-visible");
  app.setAttribute("aria-busy", "false");
  localSession("forge-gen4-intro", "seen");
  state.booting = false;

  if (isReducedMotion()) {
    screen.hidden = true;
    screen.style.display = "none";
    return;
  }

  // Phase 1: Lock-in ignition pulse on perimeter and brand mark
  screen.classList.add("is-ignited");

  const shockwave = $("boot-shockwave");
  const topbar = document.querySelector(".topbar");
  const rail = document.querySelector(".activity-rail");
  const mainStage = $("main-content");
  const content = screen.querySelector(".boot-content");
  const perimeter = screen.querySelector(".boot-perimeter");

  // Let the crisp lock-in register for 110ms, then launch liquid aperture bloom
  window.setTimeout(() => {
    const bootSpring = new Spring({
      stiffness: 155,
      damping: 20,
      mass: 1,
      value: 0,
      target: 1,
      precision: 0.001,
    });

    const transitionTask = {
      step(dt) {
        const settled = bootSpring.step(dt);
        const p = bootSpring.value;

        // Aperture expands outward from center (0% to 150%) revealing workspace underneath
        const apertureRadius = Math.max(0, p * 150);
        const feather = 18;
        const maskVal = `radial-gradient(circle at 50% 50%, transparent ${apertureRadius.toFixed(1)}%, black ${(apertureRadius + feather).toFixed(1)}%)`;
        screen.style.webkitMaskImage = maskVal;
        screen.style.maskImage = maskVal;

        // Shockwave expansion wave
        if (shockwave) {
          const shockScale = (p * 280).toFixed(1);
          const shockOpacity = Math.max(0, (1 - p * 1.3) * 0.85).toFixed(3);
          shockwave.style.transform = `translate(-50%, -50%) scale(${shockScale})`;
          shockwave.style.opacity = shockOpacity;
        }

        // Screen fade and perimeter dissolve
        screen.style.opacity = Math.max(0, 1 - p * 1.45).toFixed(3);
        if (perimeter) {
          perimeter.style.opacity = Math.max(0, 1 - p * 2.2).toFixed(2);
        }

        // Boot content dissolves with subtle upward dissipation
        if (content) {
          content.style.opacity = Math.max(0, 1 - p * 2.5).toFixed(2);
          content.style.transform = `scale(${(1 + 0.06 * p).toFixed(3)}) translate3d(0, ${(-14 * p).toFixed(1)}px, 0)`;
        }

        // Workspace emerges with depth bloom and optical focus pull
        if (app) {
          const scale = (0.968 + 0.032 * Math.min(1, p)).toFixed(4);
          const blur = Math.max(0, 6 * (1 - p)).toFixed(1);
          const brightness = (0.86 + 0.14 * Math.min(1, p)).toFixed(3);
          app.style.transform = `scale(${scale})`;
          app.style.filter = `blur(${blur}px) brightness(${brightness})`;
        }

        // Staggered architectural docking
        const dockP = Math.min(1, Math.max(0, (p - 0.1) / 0.9));
        if (topbar) {
          topbar.style.transform = `translate3d(0, ${(-16 * (1 - dockP)).toFixed(1)}px, 0)`;
        }
        if (rail) {
          rail.style.transform = `translate3d(${(-18 * (1 - dockP)).toFixed(1)}px, 0, 0)`;
        }
        if (mainStage) {
          mainStage.style.transform = `translate3d(0, ${(10 * (1 - dockP)).toFixed(1)}px, 0)`;
        }

        if (settled) {
          screen.hidden = true;
          screen.style.display = "none";
          screen.style.webkitMaskImage = "";
          screen.style.maskImage = "";
          screen.style.opacity = "";
          screen.classList.remove("is-ignited");
          if (shockwave) {
            shockwave.style.transform = "";
            shockwave.style.opacity = "";
          }
          if (content) {
            content.style.opacity = "";
            content.style.transform = "";
          }
          if (perimeter) {
            perimeter.style.opacity = "";
          }
          if (app) {
            app.style.transform = "";
            app.style.filter = "";
          }
          if (topbar) topbar.style.transform = "";
          if (rail) rail.style.transform = "";
          if (mainStage) mainStage.style.transform = "";

          // Ensure rail indicator is properly situated
          const activeRailBtn = document.querySelector(`.rail-button[data-view="${state.activeView}"]`);
          if (activeRailBtn && railIndicator) {
            railIndicator.moveTo(activeRailBtn, false);
          }

          return true;
        }
        return false;
      },
    };

    scheduler.register(transitionTask);
  }, 110);
}

function finishBoot() {
  if (state.transitioning) return;
  state.bootReady = true;
  setBootProgress(100);
  if (bootProgress >= 99.5 || bootMotion.displayed >= 99.5) {
    completeBootTransition();
  } else {
    window.setTimeout(() => {
      if (!state.transitioning) completeBootTransition();
    }, 250);
  }
}

function showBootFailure(error) {
  setBoot("The workspace could not be analyzed", error.message || "The local service did not respond.");
  $("boot-failure").hidden = false;
  $("forge-app").setAttribute("aria-busy", "false");
  setStatus("Unavailable", false, true);
}
`

---

### e) Sidebar Content-Switch Code

#### app.js:982-1088 (switchSideView)
`javascript
function switchSideView(oldView, newView, labels) {
  if (currentViewSpring) {
    scheduler.unregister(currentViewSpring);
    currentViewSpring = null;
  }

  const outEl = $(`${oldView}-view`);
  const inEl = $(`${newView}-view`);
  if (!outEl || !inEl || oldView === newView) {
    if (inEl) {
      inEl.hidden = false;
      inEl.style.position = "";
      inEl.style.opacity = "";
      inEl.style.transform = "";
    }
    return;
  }

  const fromIdx = RAIL_ORDER.indexOf(oldView);
  const toIdx = RAIL_ORDER.indexOf(newView);
  const shiftDir = toIdx >= fromIdx ? 1 : -1;

  const eyebrowEl = $("side-eyebrow");
  const titleEl = $("side-title");
  let headingUpdated = false;

  inEl.hidden = false;
  inEl.style.position = "absolute";
  inEl.style.top = "76px";
  inEl.style.left = "0px";
  inEl.style.right = "0px";
  inEl.style.bottom = "0px";
  inEl.style.opacity = "0";
  inEl.style.transform = `translate3d(0, ${shiftDir * 14}px, 0) scale(0.985)`;

  outEl.style.transformOrigin = "top center";
  inEl.style.transformOrigin = "top center";

  const spring = new Spring({
    stiffness: 220,
    damping: 24,
    mass: 1,
    value: 0,
    target: 1,
    precision: 0.001,
  });

  currentViewSpring = {
    step(dt) {
      const settled = spring.step(dt);
      const p = spring.value;

      if (eyebrowEl && titleEl && labels && labels[newView]) {
        if (p < 0.35) {
          const hp = p / 0.35;
          eyebrowEl.style.opacity = (1 - hp).toFixed(2);
          titleEl.style.opacity = (1 - hp).toFixed(2);
          eyebrowEl.style.transform = `translate3d(0, ${(-3 * hp).toFixed(1)}px, 0)`;
          titleEl.style.transform = `translate3d(0, ${(-3 * hp).toFixed(1)}px, 0)`;
        } else {
          if (!headingUpdated) {
            headingUpdated = true;
            eyebrowEl.textContent = labels[newView][0];
            titleEl.textContent = labels[newView][1];
            $("sidebar").setAttribute("aria-label", labels[newView][2]);
          }
          const hp = Math.min(1, (p - 0.35) / 0.65);
          eyebrowEl.style.opacity = hp.toFixed(2);
          titleEl.style.opacity = hp.toFixed(2);
          eyebrowEl.style.transform = `translate3d(0, ${(3 * (1 - hp)).toFixed(1)}px, 0)`;
          titleEl.style.transform = `translate3d(0, ${(3 * (1 - hp)).toFixed(1)}px, 0)`;
        }
      }

      const pOut = Math.min(1, Math.max(0, p * 2.2));
      const pIn = Math.max(0, (p - 0.2) / 0.8);

      if (pOut >= 1) {
        outEl.hidden = true;
      } else {
        outEl.hidden = false;
        outEl.style.opacity = (1 - pOut).toFixed(3);
        outEl.style.transform = `translate3d(0, ${(-shiftDir * 10 * pOut).toFixed(1)}px, 0) scale(${(1 - 0.015 * pOut).toFixed(3)})`;
      }

      inEl.style.opacity = pIn.toFixed(3);
      inEl.style.transform = `translate3d(0, ${(shiftDir * 14 * (1 - pIn)).toFixed(1)}px, 0) scale(${(0.985 + 0.015 * pIn).toFixed(3)})`;

      if (settled) {
        outEl.hidden = true;
        outEl.style.opacity = "";
        outEl.style.transform = "";
        inEl.style.position = "";
        inEl.style.top = "";
        inEl.style.left = "";
        inEl.style.right = "";
        inEl.style.bottom = "";
        inEl.style.opacity = "";
        inEl.style.transform = "";
        if (eyebrowEl) { eyebrowEl.style.opacity = ""; eyebrowEl.style.transform = ""; }
        if (titleEl) { titleEl.style.opacity = ""; titleEl.style.transform = ""; }
        currentViewSpring = null;
        return true;
      }
      return false;
    },
  };
`
