// motion/debug.js - Tuning panel (Ctrl+Alt+T), slow motion (Ctrl+Alt+M), frame scrubber, and debug overlays

import {
  getActiveConfig,
  updateKnob,
  resetKnobs,
  getActivePresetName,
  setMotionPreset,
  toggleSlowMotion,
  isSlowMotion,
  SPRING_PRESETS,
  computeZeta,
} from "./config.js";
import { stack } from "./stack.js";

let tuningPanelEl = null;
let scrubberPanelEl = null;
let debugCanvas = null;
let showPathOverlay = false;

export function initDebugTools() {
  if (typeof window === "undefined") return;

  window.addEventListener("keydown", (e) => {
    if (e.ctrlKey && e.altKey && e.key.toLowerCase() === "t") {
      e.preventDefault();
      toggleTuningPanel();
    }
    if (e.ctrlKey && e.altKey && e.key.toLowerCase() === "m") {
      e.preventDefault();
      const isSlow = toggleSlowMotion();
      showPathOverlay = isSlow;
      updateDebugCanvas();
      console.log(`[Forge Motion] Slow motion (0.1x): ${isSlow ? "ENABLED" : "DISABLED"}`);
    }
    if (e.ctrlKey && e.altKey && e.key.toLowerCase() === "s") {
      e.preventDefault();
      toggleScrubberPanel();
    }
  });

  ensureDebugCanvas();
}

function ensureDebugCanvas() {
  if (debugCanvas || typeof document === "undefined") return;
  debugCanvas = document.createElement("canvas");
  debugCanvas.id = "motion-debug-canvas";
  debugCanvas.style.cssText = "position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none;z-index:9999;display:none;";
  document.body.appendChild(debugCanvas);

  const resize = () => {
    if (!debugCanvas) return;
    debugCanvas.width = window.innerWidth;
    debugCanvas.height = window.innerHeight;
  };
  window.addEventListener("resize", resize);
  resize();
}

export function drawDebugPoints(points, arcPoints = null) {
  if (!showPathOverlay || !debugCanvas) return;
  debugCanvas.style.display = "block";
  const ctx = debugCanvas.getContext("2d");
  ctx.clearRect(0, 0, debugCanvas.width, debugCanvas.height);

  if (arcPoints && arcPoints.length >= 2) {
    ctx.strokeStyle = "var(--focus-ring)";
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(arcPoints[0].x, arcPoints[0].y);
    for (let i = 1; i < arcPoints.length; i++) {
      ctx.lineTo(arcPoints[i].x, arcPoints[i].y);
    }
    ctx.stroke();
    ctx.setLineDash([]);
  }

  if (points) {
    const numPoints = points.length / 2;
    ctx.fillStyle = "var(--accent)";
    for (let i = 0; i < numPoints; i++) {
      const px = points[i * 2];
      const py = points[i * 2 + 1];
      ctx.beginPath();
      ctx.arc(px, py, 2.5, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

export function clearDebugCanvas() {
  if (!debugCanvas) return;
  const ctx = debugCanvas.getContext("2d");
  ctx.clearRect(0, 0, debugCanvas.width, debugCanvas.height);
  if (!showPathOverlay) {
    debugCanvas.style.display = "none";
  }
}

function updateDebugCanvas() {
  if (!debugCanvas) ensureDebugCanvas();
  debugCanvas.style.display = showPathOverlay ? "block" : "none";
  if (!showPathOverlay) clearDebugCanvas();
}

export function toggleTuningPanel() {
  if (tuningPanelEl) {
    tuningPanelEl.remove();
    tuningPanelEl = null;
    return;
  }

  const config = getActiveConfig();
  const panel = document.createElement("div");
  panel.id = "forge-motion-tuning-panel";
  panel.style.cssText = `
    position: fixed;
    top: 60px;
    right: 20px;
    width: 320px;
    max-height: 85vh;
    overflow-y: auto;
    background: var(--bg-editor);
    color: var(--text-on-rail);
    border: 1px solid var(--border-strong);
    box-shadow: var(--shadow-lg);
    z-index: 10000;
    font: 12px/1.4 "Cascadia Code", Consolas, monospace;
    padding: 16px;
    box-sizing: border-box;
  `;

  panel.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;border-bottom:1px solid var(--border-strong);padding-bottom:8px;">
      <strong style="color:var(--accent);font-size:13px;">MOTION TUNER</strong>
      <button id="tune-close" style="color:var(--text-muted);background:none;border:none;cursor:pointer;font-size:16px;">&times;</button>
    </div>

    <div style="margin-bottom:12px;">
      <label style="display:block;margin-bottom:4px;color:var(--text-muted);">Preset:</label>
      <select id="tune-preset" style="width:100%;background:var(--bg-gutter);color:var(--text-on-rail);border:1px solid var(--border-input);padding:4px;">
        <option value="elegant">Elegant</option>
        <option value="classic">Classic</option>
        <option value="dynamic">Dynamic</option>
        <option value="sweet">Sweet</option>
      </select>
    </div>

    <div id="tune-sliders" style="display:flex;flex-direction:column;gap:10px;"></div>

    <div style="display:flex;gap:8px;margin-top:16px;border-top:1px solid var(--border-strong);padding-top:12px;">
      <button id="tune-copy" style="flex:1;background:var(--accent);color:var(--text-on-accent);border:none;padding:6px;cursor:pointer;">Copy JSON</button>
      <button id="tune-reset" style="flex:1;background:var(--bg-hover);color:var(--text);border:none;padding:6px;cursor:pointer;">Reset</button>
    </div>
  `;

  document.body.appendChild(panel);
  tuningPanelEl = panel;

  const presetSelect = panel.querySelector("#tune-preset");
  presetSelect.value = getActivePresetName();
  presetSelect.addEventListener("change", (e) => {
    setMotionPreset(e.target.value);
    toggleTuningPanel();
    toggleTuningPanel();
  });

  panel.querySelector("#tune-close").addEventListener("click", () => toggleTuningPanel());

  panel.querySelector("#tune-copy").addEventListener("click", () => {
    const json = JSON.stringify(getActiveConfig(), null, 2);
    navigator.clipboard.writeText(json).then(() => {
      alert("Motion configuration copied to clipboard!");
    });
  });

  panel.querySelector("#tune-reset").addEventListener("click", () => {
    resetKnobs();
    toggleTuningPanel();
    toggleTuningPanel();
  });

  const slidersContainer = panel.querySelector("#tune-sliders");
  const knobsMeta = [
    { key: "speed", label: "Speed", min: 0.2, max: 2.5, step: 0.05 },
    { key: "overshoot", label: "Overshoot", min: 0, max: 2.0, step: 0.05 },
    { key: "curvature", label: "Curvature", min: 0, max: 0.35, step: 0.01 },
    { key: "stretch", label: "Stretch", min: 0, max: 0.30, step: 0.01 },
    { key: "lag", label: "Leading Lag", min: 0, max: 0.60, step: 0.01 },
    { key: "neckStrength", label: "Neck Strength", min: 0, max: 1.0, step: 0.05 },
    { key: "pointCount", label: "Point Count", min: 40, max: 120, step: 8 },
  ];

  for (const item of knobsMeta) {
    const val = config[item.key] !== undefined ? config[item.key] : 1.0;
    const row = document.createElement("div");
    row.innerHTML = `
      <div style="display:flex;justify-content:space-between;margin-bottom:2px;">
        <span>${item.label}</span>
        <span id="val-${item.key}" style="color:var(--accent);">${val}</span>
      </div>
      <input type="range" id="input-${item.key}" min="${item.min}" max="${item.max}" step="${item.step}" value="${val}" style="width:100%;accent-color:var(--accent);">
    `;
    slidersContainer.appendChild(row);

    const input = row.querySelector(`#input-${item.key}`);
    const display = row.querySelector(`#val-${item.key}`);
    input.addEventListener("input", (e) => {
      const n = parseFloat(e.target.value);
      display.textContent = n;
      updateKnob(item.key, n);
    });
  }
}

export function toggleScrubberPanel() {
  if (scrubberPanelEl) {
    scrubberPanelEl.remove();
    scrubberPanelEl = null;
    return;
  }

  const panel = document.createElement("div");
  panel.id = "forge-motion-scrubber-panel";
  panel.style.cssText = `
    position: fixed;
    bottom: 40px;
    left: 70px;
    width: 380px;
    background: var(--bg-editor);
    color: var(--text-on-rail);
    border: 1px solid var(--border-strong);
    box-shadow: var(--shadow-lg);
    z-index: 10000;
    font: 12px/1.4 "Cascadia Code", Consolas, monospace;
    padding: 14px;
    box-sizing: border-box;
  `;

  panel.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
      <strong style="color:var(--accent);">FRAME SCRUBBER</strong>
      <button id="scrub-close" style="color:var(--text-muted);background:none;border:none;cursor:pointer;font-size:16px;">&times;</button>
    </div>
    <div style="margin-bottom:8px;">
      <label style="color:var(--text-muted);display:block;margin-bottom:4px;">Surface:</label>
      <select id="scrub-surface" style="width:100%;background:var(--bg-gutter);color:var(--text-on-rail);border:1px solid var(--border-input);padding:4px;"></select>
    </div>
    <div>
      <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
        <span>Progress p</span>
        <span id="scrub-val" style="color:var(--accent);">0.000</span>
      </div>
      <input type="range" id="scrub-slider" min="0" max="1.05" step="0.005" value="0" style="width:100%;accent-color:var(--accent);">
    </div>
    <div style="display:flex;gap:4px;margin-top:10px;flex-wrap:wrap;">
      ${[0, 0.1, 0.25, 0.4, 0.55, 0.7, 0.85, 1.0, 1.03].map(p => `
        <button class="scrub-btn" data-p="${p}" style="background:var(--bg-hover);color:var(--text);border:none;padding:3px 6px;cursor:pointer;font-size:10px;">${p}</button>
      `).join("")}
    </div>
  `;

  document.body.appendChild(panel);
  scrubberPanelEl = panel;

  panel.querySelector("#scrub-close").addEventListener("click", () => toggleScrubberPanel());

  const select = panel.querySelector("#scrub-surface");
  const surfaces = stack.getAllSurfaces();
  for (const s of surfaces) {
    const opt = document.createElement("option");
    opt.value = s.id;
    opt.textContent = `${s.id} (${s.group || "default"})`;
    select.appendChild(opt);
  }

  const slider = panel.querySelector("#scrub-slider");
  const valDisplay = panel.querySelector("#scrub-val");

  const applyScrub = (p) => {
    valDisplay.textContent = Number(p).toFixed(3);
    slider.value = p;
    const surfaceId = select.value;
    scrub(surfaceId, p);
  };

  slider.addEventListener("input", (e) => {
    applyScrub(parseFloat(e.target.value));
  });

  panel.querySelectorAll(".scrub-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      applyScrub(parseFloat(btn.dataset.p));
    });
  });
}

/**
 * Public scrubber function: Forge.motion.scrub(surfaceId, p)
 */
export function scrub(surfaceId, p) {
  const surface = stack.getSurface(surfaceId);
  if (!surface) {
    console.warn(`[Forge Motion Scrubber] Surface '${surfaceId}' not found in registry.`);
    return;
  }
  if (typeof surface.renderProgress === "function") {
    surface.renderProgress(p, true); // true = static scrub
  }
}

/**
 * Scrub a side panel content switch between two rail views
 */
export function scrubSwitch(fromView = "explorer", toView = "changes", p = 0) {
  const order = ["explorer", "search", "changes", "tasks"];
  const fromIdx = order.indexOf(fromView);
  const toIdx = order.indexOf(toView);
  const shiftDir = toIdx >= fromIdx ? 1 : -1;

  const outEl = document.getElementById(`${fromView}-view`);
  const inEl = document.getElementById(`${toView}-view`);
  if (!outEl || !inEl) return;

  // Make sure sidebar is open
  const sidebar = document.getElementById("sidebar");
  if (sidebar) sidebar.classList.add("is-open");

  // Normalize timing: 0..1 maps to 0..280ms
  // Outgoing: 0..120ms (p: 0..0.428)
  // Incoming: 60..280ms (p: 0.214..1.0)
  const t = p * 280;
  const pOut = Math.min(1, Math.max(0, t / 120));
  const pIn = Math.min(1, Math.max(0, (t - 60) / 220));

  // Hide all other views
  order.forEach(view => {
    if (view !== fromView && view !== toView) {
      const vEl = document.getElementById(`${view}-view`);
      if (vEl) vEl.hidden = true;
    }
  });

  if (p <= 0) {
    outEl.hidden = false;
    outEl.style.opacity = "1";
    outEl.style.transform = "none";
    inEl.hidden = true;
  } else if (p >= 1) {
    outEl.hidden = true;
    outEl.style.opacity = "";
    outEl.style.transform = "";
    inEl.hidden = false;
    inEl.style.opacity = "1";
    inEl.style.transform = "none";
  } else {
    outEl.hidden = false;
    outEl.style.opacity = (1 - pOut).toFixed(3);
    outEl.style.transform = `translate3d(0, ${(-shiftDir * 8 * pOut).toFixed(1)}px, 0)`;

    if (t >= 60) {
      inEl.hidden = false;
      inEl.style.opacity = pIn.toFixed(3);
      inEl.style.transform = `translate3d(0, ${(shiftDir * 8 * (1 - pIn)).toFixed(1)}px, 0)`;
    } else {
      inEl.hidden = true;
    }
  }

  // Update header text
  const labels = {
    explorer: ["01 / ORIENTATION", "Repository"],
    search: ["02 / INVESTIGATION", "Search"],
    changes: ["04 / REVIEW", "Changes"],
    tasks: ["03 / DECISION THREAD", "Plan"],
  };
  const activeLabel = p < 0.5 ? labels[fromView] : labels[toView];
  const eyebrowEl = document.getElementById("side-eyebrow");
  const titleEl = document.getElementById("side-title");
  if (eyebrowEl && activeLabel) eyebrowEl.textContent = activeLabel[0];
  if (titleEl && activeLabel) titleEl.textContent = activeLabel[1];

  // Update rail indicator
  const fromBtn = document.querySelector(`.rail-button[data-view="${fromView}"]`);
  const toBtn = document.querySelector(`.rail-button[data-view="${toView}"]`);
  const rail = document.querySelector(".activity-rail");
  const indicator = document.querySelector(".rail-indicator");
  if (fromBtn && toBtn && rail && indicator) {
    const rRect = rail.getBoundingClientRect();
    const fRect = fromBtn.getBoundingClientRect();
    const tRect = toBtn.getBoundingClientRect();
    const yStart = fRect.top - rRect.top;
    const yEnd = tRect.top - rRect.top;
    const curY = yStart + (yEnd - yStart) * p;
    // Stretch mid-flight
    const stretch = Math.sin(p * Math.PI) * 7;
    indicator.style.transform = `translate3d(0, ${curY.toFixed(1)}px, 0)`;
    indicator.style.height = `${(fRect.height + stretch).toFixed(1)}px`;
    indicator.style.opacity = "1";
  }
}

/**
 * Scrub a review badge pop and digit roll
 */
export function scrubBadge(fromVal = 0, toVal = 34, p = 0) {
  const badge = document.getElementById("change-count");
  if (!badge) return;

  if (p <= 0) {
    badge.textContent = String(fromVal);
    badge.style.transform = "none";
    return;
  }
  if (p >= 1) {
    badge.textContent = String(toVal);
    badge.style.transform = "none";
    return;
  }

  // Settle spring scale approximation with ~3% overshoot at p ~ 0.7
  let scale;
  if (p < 0.7) {
    scale = 0.6 + (1.03 - 0.6) * (p / 0.7);
  } else {
    scale = 1.03 - 0.03 * ((p - 0.7) / 0.3);
  }
  badge.style.transform = `scale(${scale.toFixed(3)})`;

  // Digit roll
  const pOut = Math.min(1, p * 1.2);
  const pIn = Math.max(0, (p - 0.1) / 0.9);

  badge.innerHTML = `
    <span class="digit-roll-wrapper" style="display:inline-block;position:relative;height:14px;overflow:hidden;vertical-align:middle;width:100%;">
      <span class="digit-roll-item digit-roll-old" style="display:block;height:14px;line-height:14px;text-align:center;transform:translateY(${(-pOut * 100).toFixed(1)}%);opacity:${(1 - pOut).toFixed(2)};">${fromVal}</span>
      <span class="digit-roll-item digit-roll-new" style="display:block;position:absolute;top:0;left:0;right:0;height:14px;line-height:14px;text-align:center;transform:translateY(${((1 - pIn) * 100).toFixed(1)}%);opacity:${pIn.toFixed(2)};">${toVal}</span>
    </span>
  `;
}

/**
 * Scrub folder expand/collapse
 */
export function scrubFolder(folderKey = "root", p = 0) {
  const folderBtn = document.querySelector(`.tree-row.folder[data-folder="${folderKey}"]`);
  const folderEl = folderBtn?.closest(".tree-folder");
  const wrapper = folderEl?.querySelector(".tree-folder-wrapper");
  const children = wrapper?.querySelector(".tree-children");
  const twisty = folderBtn?.querySelector(".twisty");
  if (!folderEl || !wrapper || !children) return;

  // twisty rotates from -90deg (collapsed) to 0deg (open)
  const angle = -90 * (1 - p);
  if (twisty) {
    twisty.style.transform = `rotate(${angle.toFixed(1)}deg)`;
  }

  // grid-template-rows from 0fr to 1fr
  wrapper.style.gridTemplateRows = `${p.toFixed(3)}fr`;

  // Stagger children
  const directChildren = [...children.children].slice(0, 6);
  directChildren.forEach((child, i) => {
    const row = child.classList.contains("tree-row") ? child : child.querySelector(".tree-row");
    if (row) {
      const childStart = i * 0.1;
      const childP = Math.min(1, Math.max(0, (p - childStart) / 0.5));
      row.style.opacity = childP.toFixed(2);
      row.style.transform = `translate3d(0, ${(4 * (1 - childP)).toFixed(1)}px, 0)`;
    }
  });

  if (p <= 0) {
    folderEl.classList.add("is-collapsed");
    wrapper.classList.add("is-collapsed");
    wrapper.style.gridTemplateRows = "";
    if (twisty) twisty.style.transform = "";
  } else if (p >= 1) {
    folderEl.classList.remove("is-collapsed");
    wrapper.classList.remove("is-collapsed");
    wrapper.style.gridTemplateRows = "";
    if (twisty) twisty.style.transform = "";
    directChildren.forEach((child) => {
      const row = child.classList.contains("tree-row") ? child : child.querySelector(".tree-row");
      if (row) {
        row.style.opacity = "";
        row.style.transform = "";
      }
    });
  }
}

/**
 * Scrub a file click -> file-to-tab morph
 */
export function scrubFileClick(filePath = "app/main.py", p = 0) {
  const row = document.querySelector(`.tree-row[data-file="${encodeURIComponent(filePath)}"]`);
  const tabsContainer = document.getElementById("tabs");
  if (!row || !tabsContainer) return;

  let ghost = document.getElementById("file-to-tab-ghost");
  if (!ghost) {
    ghost = document.createElement("div");
    ghost.id = "file-to-tab-ghost";
    ghost.className = "file-to-tab-ghost";
    document.body.appendChild(ghost);
  }

  if (p <= 0) {
    ghost.style.display = "none";
    return;
  }
  if (p >= 1) {
    ghost.style.display = "none";
    return;
  }

  const rRect = row.getBoundingClientRect();
  const tRect = tabsContainer.getBoundingClientRect();

  // Target tab slot at start of tabs
  const targetX = tRect.left + 8;
  const targetY = tRect.top + 4;
  const targetW = 120;
  const targetH = 30;

  // Arc interpolation
  const curX = rRect.left + (targetX - rRect.left) * p;
  const arcY = -Math.sin(p * Math.PI) * 20; // 20px upward arc
  const curY = rRect.top + (targetY - rRect.top) * p + arcY;
  const curW = rRect.width + (targetW - rRect.width) * p;
  const curH = rRect.height + (targetH - rRect.height) * p;

  ghost.style.display = "block";
  ghost.style.left = `${curX.toFixed(1)}px`;
  ghost.style.top = `${curY.toFixed(1)}px`;
  ghost.style.width = `${curW.toFixed(1)}px`;
  ghost.style.height = `${curH.toFixed(1)}px`;
  ghost.style.opacity = (1 - p * 0.15).toFixed(2);
}

/**
 * Scrub Editor Tab indicator moving between tabs
 */
export function scrubTabs(fromIdx = 0, toIdx = 1, p = 0) {
  const container = document.getElementById("tabs");
  if (!container) return;
  const tabs = container.querySelectorAll(".tab");
  if (!tabs.length) return;
  const fromTab = tabs[Math.min(fromIdx, tabs.length - 1)];
  const toTab = tabs[Math.min(toIdx, tabs.length - 1)];
  if (!fromTab || !toTab) return;

  let ind = container.querySelector(".tab-indicator");
  if (!ind) {
    ind = document.createElement("div");
    ind.className = "tab-indicator";
    container.prepend(ind);
  }
  ind.style.opacity = "1";

  const cRect = container.getBoundingClientRect();
  const fRect = fromTab.getBoundingClientRect();
  const tRect = toTab.getBoundingClientRect();

  const startX = fRect.left - cRect.left + container.scrollLeft;
  const endX = tRect.left - cRect.left + container.scrollLeft;
  const startW = fRect.width;
  const endW = tRect.width;

  const curX = startX + (endX - startX) * p;
  // Subtle stretch mid-travel (sin curve peaking at p=0.5)
  const stretch = Math.sin(p * Math.PI) * Math.min(startW, endW) * 0.15;
  const curW = startW + (endW - startW) * p + stretch;

  ind.style.transform = `translate3d(${curX.toFixed(1)}px, 0, 0)`;
  ind.style.width = `${curW.toFixed(1)}px`;
}

/**
 * Scrub Top Step Bar (Journey) indicator moving between steps
 */
export function scrubJourney(fromStep = "understand", toStep = "investigate", p = 0) {
  const container = document.querySelector(".journey");
  if (!container) return;
  const fromEl = typeof fromStep === "number"
    ? container.querySelectorAll(".journey-step")[fromStep]
    : container.querySelector(`.journey-step[data-journey="${fromStep}"]`);
  const toEl = typeof toStep === "number"
    ? container.querySelectorAll(".journey-step")[toStep]
    : container.querySelector(`.journey-step[data-journey="${toStep}"]`);
  if (!fromEl || !toEl) return;

  let ind = container.querySelector(".journey-indicator");
  if (!ind) {
    ind = document.createElement("div");
    ind.className = "journey-indicator";
    container.prepend(ind);
  }
  ind.style.opacity = "1";

  const cRect = container.getBoundingClientRect();
  const fRect = fromEl.getBoundingClientRect();
  const tRect = toEl.getBoundingClientRect();

  const startX = fRect.left - cRect.left + container.scrollLeft;
  const endX = tRect.left - cRect.left + container.scrollLeft;
  const startW = fRect.width;
  const endW = tRect.width;

  const curX = startX + (endX - startX) * p;
  const stretch = Math.sin(p * Math.PI) * Math.min(startW, endW) * 0.18;
  const curW = startW + (endW - startW) * p + stretch;

  ind.style.transform = `translate3d(${curX.toFixed(1)}px, 0, 0)`;
  ind.style.width = `${curW.toFixed(1)}px`;
}

/**
 * Public report function: Forge.motion.report()
 */
export function report() {
  const current = getActivePresetName();
  const config = getActiveConfig();
  console.group("%c[Forge Motion Report]", "color:var(--accent);font-weight:bold;font-size:13px;");
  console.log(`Active System Preset: %c${current}%c`, "color:var(--success);font-weight:bold;", "");
  console.log("Configuration & Knobs:", config);
  console.log("\nSpring Presets & Damping Ratio (zeta):");
  const tableData = {};
  for (const [name, p] of Object.entries(SPRING_PRESETS)) {
    const z = computeZeta(p.stiffness, p.damping, p.mass);
    tableData[name] = {
      stiffness: p.stiffness,
      damping: p.damping,
      mass: p.mass,
      zeta: Number(z.toFixed(4)),
      type: z >= 1 ? "Overdamped / Critical" : "Underdamped",
    };
  }
  console.table(tableData);
  console.groupEnd();
  return { preset: current, config, presets: tableData };
}

