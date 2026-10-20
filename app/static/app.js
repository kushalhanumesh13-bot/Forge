import { MorphPanel, stack, SlidingIndicator, BadgeRoller, FlipGroup, animateFileToTab, Spring, scheduler, Presence, isReducedMotion } from "/static/motion/index.js";

let sidebarMorph = null;
let sideFlow = null;
let settingsMorph = null;
let settingsFlow = null;
let keysMorph = null;
let keysFlow = null;
let contextMorph = null;
let palettePresence = null;
let paletteFlow = null;
let dockFlow = null;
let dockHeightSpring = null;
let dockActiveSpring = null;
let railIndicator = null;
let treeIndicator = null;
let tabsIndicator = null;
let journeyIndicator = null;
let dockTabsIndicator = null;
let reviewBadgeRoller = null;
let currentViewSpring = null;
let contextDrawerSpring = null;
let contextDrawerActive = null;
const RAIL_ORDER = ["explorer", "search", "changes", "tasks"];

const state = {
  analysis: null,
  files: [],
  openFiles: [],
  activePath: null,
  fileContents: {},
  dirty: new Set(),
  changes: [],
  activity: [],
  activeView: "explorer",
  activeDock: "terminal",
  fileRequest: 0,
  toastTimer: null,
  searchTimer: null,
  returnFocus: null,
  booting: true,
  bootReady: false,
  transitioning: false,
  resizingSidebar: false,
  ai: { providers: [], config: null },
};

const $ = (id) => document.getElementById(id);
const $$ = (selector, context = document) => [...context.querySelectorAll(selector)];
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[character]));

function icon(name) {
  return `<svg aria-hidden="true"><use href="#i-${name}"></use></svg>`;
}

function localSession(key, value) {
  try {
    if (value === undefined) return sessionStorage.getItem(key);
    sessionStorage.setItem(key, value);
  } catch (_) {
    return null;
  }
  return value;
}

async function api(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

let bootProgress = 0;
const bootMotion = {
  displayed: 0,
  confirmed: 0,
  stageCap: 0,
  stageStartedAt: 0,
  frame: 0,
  lastTime: 0,
};
const bootStages = [
  { label: "Opening the workbench", detail: "Waiting for the local workspace.", progress: 0, cap: 4 },
  { label: "Reading the repository", detail: "Requesting local structure and Git state.", progress: 15, cap: 13 },
  { label: "Mapping the codebase", detail: "Analyzing files, symbols, and dependencies.", progress: 45, cap: 40 },
  { label: "Preparing the editor", detail: "Loading syntax highlighting and Git state.", progress: 75, cap: 70 },
  { label: "Repository mapped", detail: "Opening the workbench with local evidence.", progress: 100, cap: 96 },
];
let currentBootStage = 0;

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

function toast(message, type = "info") {
  const node = $("toast");
  node.textContent = message;
  node.className = `toast is-showing${type === "error" ? " is-error" : type === "warning" ? " is-warning" : ""}`;
  window.clearTimeout(state.toastTimer);
  state.toastTimer = window.setTimeout(() => { node.className = "toast"; }, 3600);
}

function setStatus(value, busy = false, failed = false) {
  $("status").textContent = value;
  const connection = document.querySelector(".connection");
  connection.classList.toggle("is-busy", busy);
  connection.classList.toggle("is-error", failed);
}

function addActivity(message, mark = "·") {
  state.activity.unshift({
    mark,
    message,
    time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  });
  state.activity = state.activity.slice(0, 60);
  $("activity-count").textContent = String(state.activity.length);
  $("activity").innerHTML = state.activity.length
    ? state.activity.map((entry) => `<div class="activity-row"><span class="activity-time">${esc(entry.time)}</span><span class="activity-mark">${esc(entry.mark)}</span><span>${esc(entry.message)}</span></div>`).join("")
    : '<p class="dock-empty">The local activity record is empty.</p>';
}

function workspaceName() {
  return state.analysis?.readme?.title || "Workspace";
}

function setAIStatus(message, kind = "") {
  const status = $("ai-status");
  status.className = `ai-status${kind ? ` is-${kind}` : ""}`;
  $("ai-status-text").textContent = message;
}

function renderAISettings() {
  const config = state.ai.config;
  const provider = $("ai-provider");
  const currentProvider = config?.provider || provider.value || "ollama";
  provider.innerHTML = state.ai.providers.map((item) => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join("");
  provider.value = state.ai.providers.some((item) => item.id === currentProvider) ? currentProvider : "ollama";
  $("ai-model").value = config?.model || "";
  $("ai-endpoint").value = config?.endpoint || "http://127.0.0.1:11434";
  $("ai-api-key").value = "";
  $("ai-key-state").textContent = config?.api_key_configured ? "Saved" : "Not saved";
  $("ai-test").disabled = !config;
  $("ai-remove").disabled = !config;
  $("ai-remove").textContent = config?.api_key_configured ? "Remove saved key" : "Remove configuration";
  updateAIProviderFields();
  if (config) setAIStatus("Saved; connection not tested");
  else setAIStatus("Not configured");
}

function updateAIProviderFields() {
  const ollama = $("ai-provider").value === "ollama";
  const defaults = {
    ollama: "http://127.0.0.1:11434",
    openai: "https://api.openai.com/v1",
    anthropic: "https://api.anthropic.com/v1",
  };
  const currentEndpoint = $("ai-endpoint").value;
  if (!currentEndpoint || Object.values(defaults).includes(currentEndpoint)) {
    $("ai-endpoint").value = defaults[$("ai-provider").value] || "";
  }
  $("ai-endpoint").placeholder = ollama ? "http://127.0.0.1:11434" : "https://api.example.com/v1";
  $("ai-model").placeholder = ollama ? "llama3.2" : "Model identifier";
  $("ai-help").textContent = ollama
    ? "Ollama is local-only and does not require an API key."
    : "Hosted provider configuration is saved locally; connection testing is not enabled yet.";
}

async function loadAIProviders() {
  try {
    const data = await api("/api/ai/providers");
    state.ai.providers = data.providers || [];
    state.ai.config = data.config || null;
    renderAISettings();
  } catch (error) {
    setAIStatus("Settings unavailable", "error");
    $("ai-feedback").textContent = error.message;
    $("ai-feedback").className = "ai-feedback is-error";
  }
}

async function saveAIProvider(event) {
  event.preventDefault();
  const payload = {
    provider: $("ai-provider").value,
    model: $("ai-model").value.trim(),
    endpoint: $("ai-endpoint").value.trim(),
    api_key: $("ai-api-key").value || null,
  };
  $("ai-save").disabled = true;
  $("ai-feedback").textContent = "";
  setAIStatus("Saving", "busy");
  try {
    const data = await api("/api/ai/providers", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    state.ai.config = data.config;
    renderAISettings();
    $("ai-feedback").textContent = "Configuration saved. Test the connection when you are ready.";
    $("ai-feedback").className = "ai-feedback is-success";
  } catch (error) {
    setAIStatus("Save failed", "error");
    $("ai-feedback").textContent = error.message;
    $("ai-feedback").className = "ai-feedback is-error";
  } finally {
    $("ai-save").disabled = false;
  }
}

async function testAIProvider() {
  $("ai-test").disabled = true;
  $("ai-feedback").textContent = "";
  setAIStatus("Testing connection", "busy");
  try {
    const result = await api("/api/ai/providers/test", { method: "POST" });
    const kind = result.success ? "success" : "error";
    setAIStatus(result.status === "connected" ? "Connected" : result.status.replaceAll("_", " "), kind);
    $("ai-feedback").textContent = result.message;
    $("ai-feedback").className = `ai-feedback is-${kind}`;
  } catch (error) {
    setAIStatus("Test failed", "error");
    $("ai-feedback").textContent = error.message;
    $("ai-feedback").className = "ai-feedback is-error";
  } finally {
    $("ai-test").disabled = false;
  }
}

async function removeAIProvider() {
  if (!window.confirm("Remove the saved AI provider configuration and key?")) return;
  $("ai-remove").disabled = true;
  try {
    await api("/api/ai/providers", { method: "DELETE" });
    state.ai.config = null;
    renderAISettings();
    $("ai-feedback").textContent = "Saved provider key removed.";
    $("ai-feedback").className = "ai-feedback is-success";
  } catch (error) {
    $("ai-remove").disabled = false;
    setAIStatus("Remove failed", "error");
    $("ai-feedback").textContent = error.message;
    $("ai-feedback").className = "ai-feedback is-error";
  }
}

function hasUnsavedChanges() {
  return state.dirty.size > 0;
}

function confirmNavigation() {
  return !hasUnsavedChanges() || window.confirm("You have unsaved changes. Continue without saving?");
}

function fileIcon(path) {
  const extension = path.includes(".") ? path.split(".").pop().toLowerCase() : "";
  return ["py", "js", "ts", "tsx", "jsx", "html", "css", "json", "yaml", "yml", "toml", "xml", "sh", "ps1"].includes(extension) ? "code" : "file";
}

function isTransientFolder(name) {
  return [".playwright-cli", ".pytest_cache", "__pycache__", "node_modules"].includes(name);
}

function folderRow(name, node, depth, parentPath) {
  const key = `${parentPath}/${name}`;
  const folders = Object.keys(node.folders).sort((a, b) => a.localeCompare(b))
    .map((child) => folderRow(child, node.folders[child], depth + 1, key)).join("");
  const files = [...node.files].sort((a, b) => a.path.localeCompare(b.path))
    .map((file) => fileRow(file, depth + 1)).join("");
  const encodedKey = encodeURIComponent(key);
  const collapsed = isTransientFolder(name);
  return `<div class="tree-folder${collapsed ? " is-collapsed" : ""}"><button class="tree-row folder" type="button" data-folder="${encodedKey}" style="padding-left:${8 + depth * 14}px"><span class="twisty" aria-hidden="true">▾</span><span class="file-symbol">${icon("folder")}</span><span class="file-name">${esc(name)}</span></button><div class="tree-folder-wrapper${collapsed ? " is-collapsed" : ""}"><div class="tree-children" data-children="${encodedKey}">${folders}${files}</div></div></div>`;
}

function fileRow(file, depth) {
  const selected = file.path === state.activePath ? " is-selected" : "";
  const dirty = state.dirty.has(file.path) ? '<span class="modified-dot" aria-label="Unsaved change"></span>' : "";
  return `<button class="tree-row${selected}" role="treeitem" aria-selected="${file.path === state.activePath}" type="button" data-file="${encodeURIComponent(file.path)}" style="padding-left:${8 + depth * 14}px"><span class="twisty" aria-hidden="true"></span><span class="file-symbol">${icon(fileIcon(file.path))}</span><span class="file-name">${esc(file.path.split("/").pop())}</span>${dirty}</button>`;
}

function buildTree() {
  const root = { folders: {}, files: [] };
  state.files.forEach((file) => {
    const parts = file.path.split("/");
    let node = root;
    parts.slice(0, -1).forEach((part) => {
      node.folders[part] ??= { folders: {}, files: [] };
      node = node.folders[part];
    });
    node.files.push(file);
  });
  const folders = Object.keys(root.folders).sort((a, b) => a.localeCompare(b))
    .map((name) => folderRow(name, root.folders[name], 1, "root")).join("");
  const files = [...root.files].sort((a, b) => a.path.localeCompare(b.path))
    .map((file) => fileRow(file, 0)).join("");
  $("tree").innerHTML = `<div class="tree-folder"><button class="tree-row folder" type="button" data-folder="root" style="padding-left:8px"><span class="twisty" aria-hidden="true">▾</span><span class="file-symbol">${icon("folder")}</span><span class="file-name">${esc(workspaceName())}</span></button><div class="tree-folder-wrapper"><div class="tree-children" data-children="root">${folders}${files}</div></div></div>`;
  $("file-count").textContent = `${state.files.length} files`;

  if (treeIndicator) {
    const activeRow = $("tree").querySelector(".tree-row.is-selected");
    if (activeRow) treeIndicator.moveTo(activeRow, true);
  }
}

function renderRepositorySummary() {
  const git = state.analysis?.git || {};
  const frameworks = Array.isArray(state.analysis?.frameworks) ? state.analysis.frameworks : [];
  const worktree = git.is_repository
    ? (git.is_clean ? "Clean worktree" : `${git.changed_files?.length || 0} changed files`)
    : "Git state unavailable";
  $("repo-summary").innerHTML = `<span class="summary-rule" aria-hidden="true"></span><div><strong>${esc(state.analysis?.project_type || "Local project")}</strong><span>${esc(frameworks.join(" · ") || worktree)}</span></div>`;
}

async function loadAnalysis({ initial = false } = {}) {
  if (initial) {
    state.bootReady = false;
    state.transitioning = false;
    currentBootStage = 0;
    resetBootProgress();
    setBoot(bootStages[0].label, bootStages[0].detail);
    beginBootStage(0);
  }
  setStatus("Reading", true);
  addActivity("Repository analysis started", "○");
  try {
    // Stage 1: Reading repository
    beginBootStage(1);
    state.analysis = await api("/api/repository/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });

    // Stage 2: Mapping codebase
    completeBootStage();
    beginBootStage(2);
    state.files = state.analysis.codebase_understanding?.files || [];
    const summary = state.analysis.summary || {};
    const git = state.analysis.git || {};
    $("repo-title").textContent = workspaceName();
    $("repo-name").textContent = workspaceName();
    $("branch-name").textContent = git.branch ? `branch / ${git.branch}` : "branch unavailable";
    $("status-meta").textContent = `${summary.total_files || state.files.length} files · ${summary.python_files || 0} Python · ${summary.test_files || 0} tests`;
    renderRepositorySummary();
    buildTree();

    // Stage 3: Preparing editor
    completeBootStage();
    beginBootStage(3);
    setStatus("Ready");
    addActivity(`Repository read · ${state.files.length} files`, "✓");
    await loadChanges();

    // Stage 4: Ready
    if (initial) {
      completeBootStage();
      beginBootStage(4);
      finishBoot();
    }
  } catch (error) {
    setStatus("Read failed", false, true);
    addActivity(`Repository analysis failed · ${error.message}`, "!");
    if (initial) showBootFailure(error);
    else toast(`Could not refresh the repository: ${error.message}`, "error");
  }
}

async function loadChanges() {
  try {
    const data = await api("/api/changes");
    state.changes = data.changes || [];
    if (reviewBadgeRoller) reviewBadgeRoller.set(state.changes.length);
    else $("change-count").textContent = String(state.changes.length);
    $("changes-count").textContent = `${state.changes.length} files`;
    $("changes-list").innerHTML = state.changes.length
      ? state.changes.map((change) => `<button class="change-row" type="button" data-change="${encodeURIComponent(change.path)}"><span class="change-status">${esc(change.status)}</span><span class="change-path">${esc(change.path)}</span></button>`).join("")
      : '<p class="side-empty">No local changes.<br><small>Edit and save a file to review it here.</small></p>';
  } catch (error) {
    addActivity(`Git status unavailable · ${error.message}`, "!");
    $("changes-list").innerHTML = `<p class="side-empty">Could not read Git changes.<br><small>${esc(error.message)}</small></p>`;
  }
}

async function openFile(path) {
  if (path === state.activePath || !confirmNavigation()) return;
  const requestId = ++state.fileRequest;
  const isNew = !state.openFiles.includes(path);
  const rowEl = document.querySelector(`.tree-row[data-file="${encodeURIComponent(path)}"]`);

  if (isNew) state.openFiles.push(path);
  state.activePath = path;

  // Move selection indicator on tree
  if (rowEl) {
    document.querySelectorAll(".tree-row.is-selected").forEach((r) => {
      r.classList.remove("is-selected");
      r.setAttribute("aria-selected", "false");
    });
    rowEl.classList.add("is-selected");
    rowEl.setAttribute("aria-selected", "true");
    if (treeIndicator) treeIndicator.moveTo(rowEl);
  }

  renderTabs();
  renderEditor(true);

  // File to tab morph animation
  if (isNew && rowEl) {
    const tabEl = document.querySelector(`.tab[data-tab="${encodeURIComponent(path)}"]`);
    if (tabEl) {
      animateFileToTab(rowEl, tabEl);
    }
  }

  setStatus("Reading", true);
  try {
    const data = await api(`/api/file?path=${encodeURIComponent(path)}`);
    if (requestId !== state.fileRequest || state.activePath !== path) return;
    state.fileContents[path] = data.content;
    renderTabs();
    renderEditor();
    setStatus("Ready");
    addActivity(`Inspected ${path}`, "→");
  } catch (error) {
    if (requestId !== state.fileRequest) return;
    toast(`Unable to read ${path}: ${error.message}`, "error");
    addActivity(`Read failed · ${path}`, "!");
    state.openFiles = state.openFiles.filter((item) => item !== path);
    state.activePath = state.openFiles.at(-1) || null;
    renderTabs();
    renderEditor();
    setStatus("Ready");
  }
}

function renderTabs() {
  $("tabs").innerHTML = state.openFiles.length
    ? state.openFiles.map((path) => {
      const active = path === state.activePath ? " is-active" : "";
      const dirty = state.dirty.has(path) ? '<span class="tab-dirty" aria-label="Unsaved change"></span>' : "";
      return `<button class="tab${active}" role="tab" type="button" aria-selected="${path === state.activePath}" data-tab="${encodeURIComponent(path)}"><span class="tab-name">${esc(path.split("/").pop())}</span>${dirty}<span class="tab-close" role="button" aria-label="Close ${esc(path)}" data-close="${encodeURIComponent(path)}">${icon("close")}</span></button>`;
    }).join("")
    : '<p class="tab-empty">No source in focus</p>';

  if (tabsIndicator) {
    const activeTab = $("tabs").querySelector(".tab.is-active");
    if (activeTab) {
      tabsIndicator.moveTo(activeTab, !state.bootReady);
    } else {
      tabsIndicator.hide();
    }
  }
}

function highlight(source) {
  let html = esc(source);
  const tokens = [];
  const ph = (tag, content) => {
    const i = tokens.length;
    tokens.push(`<span class="tok-${tag}">${content}</span>`);
    return `\x00${i}\x00`;
  };
  html = html.replace(/(&quot;.*?&quot;|&#39;.*?&#39;)/g, (m) => ph("string", m));
  html = html.replace(/(^|\n)(\s*#.*)/g, (m, pre, body) => pre + ph("comment", body));
  html = html.replace(/\b(def|class|return|from|import|if|else|elif|for|in|not|and|or|True|False|None|async|await|with|as|try|except|raise|const|let|function|export|new|public|private)\b/g, (m) => ph("keyword", m));
  html = html.replace(/\b(\d+)\b/g, (m) => ph("number", m));
  return html.replace(/\x00(\d+)\x00/g, (_, i) => tokens[i]);
}

function renderEditor(loading = false) {
  const content = state.activePath ? (state.fileContents[state.activePath] || "") : "";
  const active = Boolean(state.activePath) && !loading;
  $("editor").value = content;
  $("editor").disabled = !active;
  $("save").disabled = !active || !state.dirty.has(state.activePath);
  $("editor-empty").hidden = Boolean(state.activePath);
  if (loading) {
    $("editor-empty").hidden = false;
    $("editor-empty").innerHTML = '<span class="empty-index">READING LOCAL FILE</span><strong>Opening source.</strong><p>Fetching the selected file from the workspace.</p>';
  } else if (!state.activePath) {
    $("editor-empty").innerHTML = '<span class="empty-index">OBSERVE / 01</span><strong>Start with evidence.</strong><p>Choose a file to inspect the current implementation before you change it.</p>';
  }
  const parts = (state.activePath || "").split("/").filter(Boolean);
  $("breadcrumbs").innerHTML = state.activePath
    ? `<span class="crumb-segment" style="animation-delay: 0ms">${esc(workspaceName())}</span>` +
      parts.map((part, index) =>
        `<span class="breadcrumb-slash">/</span><span class="crumb-segment" style="animation-delay: ${(index + 1) * 30}ms">${esc(part)}</span>`
      ).join("")
    : `<span class="crumb-segment">${esc(workspaceName())}</span><span class="crumb-muted">Select a file to inspect</span>`;
  $("line-numbers").textContent = content ? content.split("\n").map((_, index) => index + 1).join("\n") : "";
  $("code-highlight").innerHTML = highlight(content);
  $("status-path").textContent = `${workspaceName()} / ${state.activePath || "orientation"}`;
  $$('[data-file]').forEach((row) => {
    const selected = decodeURIComponent(row.dataset.file) === state.activePath;
    row.classList.toggle("is-selected", selected);
    row.setAttribute("aria-selected", String(selected));
  });
  updateFind();
}

function markDirty() {
  if (!state.activePath) return;
  state.fileContents[state.activePath] = $("editor").value;
  state.dirty.add(state.activePath);
  $("save").disabled = false;
  $("code-highlight").innerHTML = highlight($("editor").value);
  $("line-numbers").textContent = $("editor").value.split("\n").map((_, index) => index + 1).join("\n");
  renderTabs();
  buildTree();
  updateFind();
}

async function saveFile() {
  if (!state.activePath || !state.dirty.has(state.activePath)) return;
  const path = state.activePath;
  $("save").disabled = true;
  setStatus("Saving", true);
  try {
    await api("/api/file/write", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, content: $("editor").value }),
    });
    state.dirty.delete(path);
    renderTabs();
    buildTree();
    setStatus("Ready");
    toast("Saved to the local workspace", "success");
    addActivity(`Saved ${path}`, "✓");
    await loadChanges();
  } catch (error) {
    $("save").disabled = false;
    setStatus("Save failed", false, true);
    toast(`Unable to save ${path}: ${error.message}`, "error");
    addActivity(`Save failed · ${path}`, "!");
  }
}

function updateFind() {
  const strip = $("file-find");
  if (strip.hidden) return;
  const query = $("file-find-input").value;
  const source = $("editor").value;
  if (!query || !source) {
    $("file-find-count").textContent = query ? "No source selected" : "";
    return;
  }
  const haystack = source.toLocaleLowerCase();
  const needle = query.toLocaleLowerCase();
  let cursor = 0;
  let count = 0;
  let first = -1;
  while (cursor < haystack.length) {
    const index = haystack.indexOf(needle, cursor);
    if (index === -1) break;
    if (first === -1) first = index;
    count += 1;
    cursor = index + needle.length;
  }
  $("file-find-count").textContent = `${count} match${count === 1 ? "" : "es"}`;
  if (first >= 0 && document.activeElement === $("file-find-input")) {
    $("editor").focus({ preventScroll: true });
    $("editor").setSelectionRange(first, first + query.length);
    $("file-find-input").focus({ preventScroll: true });
  }
}

function isSidebarVisible() {
  if (sideFlow && sideFlow.live) {
    return sideFlow.p.target === 1;
  }
  const sidebar = $("sidebar");
  return Boolean(sidebar && sidebar.classList.contains("is-open") && !sidebar.classList.contains("is-collapsed"));
}

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

/* Theme setting binding */
function bindThemeSetting(scope) {
  var group = (scope || document).querySelector('.theme-seg');
  if (!group || !window.ForgeTheme || group.__bound) return; group.__bound = true;
  var opts = Array.prototype.slice.call(group.querySelectorAll('[data-theme-option]'));
  var hint = document.getElementById('theme-hint');
  function sync() {
    var pref = ForgeTheme.get(), res = ForgeTheme.resolved();
    opts.forEach(function (b) { var on = b.dataset.themeOption === pref; b.setAttribute('aria-checked', on ? 'true' : 'false'); b.tabIndex = on ? 0 : -1; });
    if (hint) hint.textContent = pref === 'system' ? 'Following your device. Currently ' + res + '.' : 'Always ' + pref + '.';
  }
  group.addEventListener('click', function (e) { var b = e.target.closest('[data-theme-option]'); if (b) ForgeTheme.set(b.dataset.themeOption); });
  group.addEventListener('keydown', function (e) {
    var i = opts.findIndex(function (b) { return b.getAttribute('aria-checked') === 'true'; }), n = i, k = e.key;
    if (k === 'ArrowRight' || k === 'ArrowDown') n = (i + 1) % opts.length;
    else if (k === 'ArrowLeft' || k === 'ArrowUp') n = (i - 1 + opts.length) % opts.length;
    else if (k === 'Home') n = 0; else if (k === 'End') n = opts.length - 1; else return;
    e.preventDefault(); opts[n].focus(); ForgeTheme.set(opts[n].dataset.themeOption);
  });
  ForgeTheme.onChange(sync); sync();
}

function openSettings() {
  const panel = $("settings-panel");
  if (!panel) return;
  panel.hidden = false;
  panel.classList.add("is-open");
  const btn = document.querySelector('.rail-button[data-view="settings"]');
  if (btn) btn.classList.add("is-popup-open");
  settingsFlow?.to(1, btn);
  bindThemeSetting(panel);
}

function closeSettings() {
  settingsFlow?.to(0);
}

function toggleSettings() {
  const isOpen = settingsFlow && (settingsFlow.p.target === 1);
  if (isOpen) {
    closeSettings();
  } else {
    openSettings();
  }
}

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

function toggleKeys() {
  const isOpen = keysFlow && (keysFlow.p.target === 1);
  if (isOpen) {
    closeKeys();
  } else {
    openKeys();
  }
}

function setContextOpen(open) {
  const panel = $("context-panel");
  const workbench = $("workbench");
  if (!panel || !workbench) return;

  const isAlreadyOpen = !panel.classList.contains("is-minimized") && !workbench.classList.contains("context-is-minimized");
  if (open === isAlreadyOpen && !contextDrawerActive) return;

  panel.setAttribute("aria-hidden", String(!open));
  $("context-open").hidden = open;

  if (isReducedMotion()) {
    panel.classList.toggle("is-minimized", !open);
    workbench.classList.toggle("context-is-minimized", !open);
    return;
  }

  if (!contextDrawerSpring) {
    contextDrawerSpring = new Spring({
      stiffness: 220,
      damping: 25,
      mass: 1,
      value: open ? 0 : 1,
      target: open ? 1 : 0,
      precision: 0.001,
    });
  } else {
    contextDrawerSpring.retarget(open ? 1 : 0);
  }

  // During transition, promote context-panel to overlay on the right with initial spring state
  panel.classList.remove("is-minimized");
  panel.style.transform = open ? "translate3d(100%, 0, 0)" : "translate3d(0, 0, 0)";
  panel.style.opacity = open ? "0" : "1";
  panel.hidden = false;
  panel.style.position = "fixed";
  panel.style.right = "0px";
  panel.style.top = "64px";
  panel.style.bottom = "25px";
  panel.style.width = "344px";
  panel.style.zIndex = "25";
  workbench.classList.add("context-is-minimized");

  if (!contextDrawerActive) {
    contextDrawerActive = {
      step(dt) {
        const settled = contextDrawerSpring.step(dt);
        const p = contextDrawerSpring.value;

        // Slide from 100% (off-screen right) to 0% (settled)
        const slideX = (1 - p) * 100;
        panel.style.transform = `translate3d(${slideX.toFixed(1)}%, 0, 0)`;
        panel.style.opacity = Math.min(1, Math.max(0, p * 1.5)).toFixed(3);

        // Compress main-content margin-right smoothly
        const mainStage = $("main-content");
        if (mainStage) {
          mainStage.style.marginRight = `${(p * 344).toFixed(1)}px`;
        }

        if (settled) {
          contextDrawerActive = null;
          const target = contextDrawerSpring.target;
          panel.style.position = "";
          panel.style.right = "";
          panel.style.top = "";
          panel.style.bottom = "";
          panel.style.width = "";
          panel.style.zIndex = "";
          panel.style.transform = "";
          panel.style.opacity = "";
          if (mainStage) mainStage.style.marginRight = "";

          if (target === 1) {
            workbench.classList.remove("context-is-minimized");
            panel.classList.remove("is-minimized");
          } else {
            workbench.classList.add("context-is-minimized");
            panel.classList.add("is-minimized");
            panel.hidden = true;
          }
          return true;
        }
        return false;
      },
    };
    scheduler.register(contextDrawerActive);
  }
}

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

  scheduler.register(currentViewSpring);
}

function setView(view, { focus = false, triggerEl = null } = {}) {
  const labels = {
    explorer: ["01 / ORIENTATION", "Repository", "Repository explorer"],
    search: ["02 / INVESTIGATION", "Search", "Repository search"],
    changes: ["04 / REVIEW", "Changes", "Git changes"],
    tasks: ["03 / DECISION THREAD", "Plan", "Engineering task"],
  };

  const oldView = state.activeView;
  state.activeView = view;

  $$(".rail-button[data-view]").forEach((button) => {
    const active = button.dataset.view === view;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });

  const activeBtn = document.querySelector(`.rail-button[data-view="${view}"]`);
  if (activeBtn && railIndicator && oldView !== view) {
    if (window.ForgeFX) {
      ForgeFX.afterIdle(() => railIndicator.moveTo(activeBtn));
    } else {
      railIndicator.moveTo(activeBtn);
    }
  }

  const isSidebarOpen = isSidebarVisible();

  if (isSidebarOpen && oldView && oldView !== view && labels[oldView] && labels[view]) {
    switchSideView(oldView, view, labels);
    sideFlow?.setTrigger(activeBtn);
  } else {
    Object.keys(labels).forEach((name) => {
      const el = $(`${name}-view`);
      if (el) el.hidden = name !== view;
    });
    if (labels[view]) {
      $("side-eyebrow").textContent = labels[view][0];
      $("side-title").textContent = labels[view][1];
      $("sidebar").setAttribute("aria-label", labels[view][2]);
    }
  }

  if (view === "changes") {
    if (window.ForgeFX && window.ForgeFX.busy()) {
      window.ForgeFX.afterIdle(() => void loadChanges());
    } else {
      void loadChanges();
    }
  }
  if (!isSidebarVisible()) {
    setSidebarOpen(true, triggerEl);
  }
  if (view === "tasks") setContextOpen(true);
  if (focus && view === "search") $("search-input").focus();
}

async function searchRepository() {
  const query = $("search-input").value.trim();
  if (!query) {
    $("search-results").innerHTML = "";
    $("search-meta").textContent = "Search the local repository.";
    return;
  }
  $("search-meta").textContent = "Searching local source…";
  try {
    const data = await api("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    const matches = data.matches || [];
    $("search-meta").textContent = `${data.match_count || 0} match${data.match_count === 1 ? "" : "es"} · ${data.files_scanned || 0} files read`;
    $("search-results").innerHTML = matches.length
      ? matches.map((match) => `<button class="result-row" type="button" data-result="${encodeURIComponent(match.path)}"><span class="result-path">${esc(match.path)}</span><span class="result-line"><b>${esc(match.line)}</b> · ${esc(match.snippet)}</span></button>`).join("")
      : '<p class="side-empty">No local matches for this query.</p>';
  } catch (error) {
    $("search-meta").textContent = "Search could not be completed.";
    $("search-results").innerHTML = `<p class="side-empty">${esc(error.message)}</p>`;
    toast(error.message, "error");
  }
}

async function showDiff(path) {
  setView("changes");
  void openFile(path);
  setDock("output");
  $("output-log").textContent = "Reading the current Git diff…";
  try {
    const data = await api(`/api/changes/diff?path=${encodeURIComponent(path)}`);
    $("output-log").textContent = data.diff || "No textual diff is available for this file.";
    addActivity(`Reviewed diff · ${path}`, "→");
  } catch (error) {
    $("output-log").textContent = `Unable to read diff: ${error.message}`;
    toast(error.message, "error");
  }
}

function renderPlan(result) {
  const plan = result.plan || {};
  const impact = plan.impact || {};
  const tests = plan.tests || {};
  const task = plan.task || {};
  const confidence = { high: "High", medium: "Medium", low: "Low" }[plan.confidence || result.confidence] || "Unrated";
  const risks = Array.isArray(plan.risks) ? plan.risks : [];
  const ambiguity = plan.ambiguity || {};
  const steps = Array.isArray(plan.steps) ? plan.steps : [];
  const affectedSymbols = Array.isArray(plan.affected_symbols) ? plan.affected_symbols : [];
  $("plan").innerHTML = `<div class="plan-summary"><div class="plan-title">${esc(plan.objective || task.description || "No objective returned")}</div><div class="plan-badges"><span class="badge">${esc((task.type || result.classification || "unknown").replaceAll("_", " "))}</span><span class="confidence">${esc(confidence)} confidence</span><span class="plan-state">Plan only</span></div></div>
    <div class="evidence"><div><strong>${Number(plan.affected_files?.length || 0)}</strong><span>affected files</span></div><div><strong>${Number(impact.dependents?.length || 0)}</strong><span>dependents</span></div><div><strong>${Number(tests.existing_tests?.length || 0)}</strong><span>related tests</span></div><div><strong>${Number(risks.length)}</strong><span>risks</span></div></div>
    ${ambiguity.needs_clarification ? `<div class="callout"><strong>CLARIFICATION NEEDED</strong><span>${esc((ambiguity.questions || []).join(" "))}</span></div>` : ""}
    <p class="section-label">IMPLEMENTATION PATH</p><ol class="plan-steps">${steps.map((step, index) => `<li class="plan-step"><span class="step-num">${String(step.order || index + 1).padStart(2, "0")}</span><div><div class="step-text">${esc(step.description || step.action || step)}</div>${step.targets?.length ? `<div class="step-files">${step.targets.map(esc).join(" · ")}</div>` : ""}${step.depends_on?.length ? `<div class="step-dependency">Depends on step ${step.depends_on.join(", ")}</div>` : ""}</div></li>`).join("") || '<li class="plan-step"><span class="step-num">—</span><div class="step-text">No steps were returned.</div></li>'}</ol>
    ${affectedSymbols.length ? `<p class="section-label">RELEVANT SYMBOLS</p><div class="chip-list">${affectedSymbols.map((symbol) => `<span class="chip">${esc(symbol.name || symbol)} <small>${esc(symbol.file || "")}${symbol.line ? `:${Number(symbol.line)}` : ""}</small></span>`).join("")}</div>` : ""}
    ${risks.length ? `<p class="section-label">RISKS</p><div class="risk-list">${risks.map((risk) => `<div class="risk"><strong>${esc(String(risk.type || "risk").replaceAll("_", " "))}</strong><span>${esc(risk.description || risk)}</span></div>`).join("")}</div>` : ""}
    <p class="section-label">VERIFY</p><div class="step-files">${(tests.proposed_tests || []).map(esc).join("<br>") || "No verification strategy was returned."}</div>`;
  $("task-list").innerHTML = `<div class="task-brief"><strong>${esc(plan.objective || task.description || "Current engineering task")}</strong><span>${steps.length} planned step${steps.length === 1 ? "" : "s"} · ${esc(confidence)} confidence</span><button type="button" id="task-open-plan">Open decision thread</button></div>`;
  $("task-open-plan").addEventListener("click", () => {
    $("context-panel").classList.remove("is-minimized");
    $("workbench").classList.remove("context-is-minimized");
    $("task").focus();
  });
}

async function generatePlan() {
  const description = $("task").value.trim();
  if (!description) {
    toast("Describe the engineering work first.", "warning");
    $("task").focus();
    return;
  }
  setStatus("Planning", true);
  $("generate").disabled = true;
  addActivity("Generating an evidence-based plan", "○");
  try {
    const result = await api("/api/task/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description }),
    });
    renderPlan(result);
    setStatus("Ready");
    addActivity(`Plan ready · ${result.plan?.steps?.length || 0} steps`, "✓");
    setView("tasks");
    toast("Engineering plan ready", "success");
  } catch (error) {
    setStatus("Plan failed", false, true);
    addActivity(`Planning failed · ${error.message}`, "!");
    toast(error.message, "error");
  } finally {
    $("generate").disabled = false;
  }
}

function setDock(name) {
  state.activeDock = name;
  $$(".dock-tab").forEach((tab) => {
    const active = tab.dataset.dock === name;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  const activeTab = document.querySelector(`.dock-tab[data-dock="${name}"]`);
  if (activeTab && dockTabsIndicator) {
    dockTabsIndicator.moveTo(activeTab);
  }
  $$(".dock-content").forEach((panel) => {
    const active = panel.id === `dock-${name}`;
    panel.classList.toggle("is-active", active);
    panel.hidden = !active;
  });
  const dock = $("bottom-dock");
  if (dock.classList.contains("is-collapsed")) {
    toggleDock();
  }
}

async function runCommand() {
  const command = $("command").value.trim();
  setDock("terminal");
  setStatus("Verifying", true);
  $("run-command").disabled = true;
  $("terminal-output").textContent = "Running the allowed local verification command…";
  addActivity(`Ran ${command}`, "▶");
  try {
    const result = await api("/api/command/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command }),
    });
    const output = result.output || "(no output)";
    $("terminal-output").textContent = output;
    $("output-log").textContent = output;
    const passed = Number((output.match(/(\d+) passed/) || [])[1] || 0);
    const skipped = Number((output.match(/(\d+) skipped/) || [])[1] || 0);
    const failed = result.exitCode === 0 ? 0 : Number((output.match(/(\d+) failed/) || [])[1] || 1);
    $("test-summary").innerHTML = `<div class="test-metric"><strong>${passed}</strong><span>passed</span></div><div class="test-metric"><strong>${skipped}</strong><span>skipped</span></div><div class="test-metric${failed ? " failed" : ""}"><strong>${failed}</strong><span>failed</span></div><div class="test-command">${esc(command)}<br>exit code ${Number(result.exitCode)}</div>`;
    setStatus(result.exitCode === 0 ? "Ready" : "Verification failed", false, result.exitCode !== 0);
    addActivity(result.exitCode === 0 ? "Verification passed" : "Verification failed", result.exitCode === 0 ? "✓" : "!");
    toast(result.exitCode === 0 ? "Verification passed" : "Verification reported a failure", result.exitCode === 0 ? "success" : "error");
    setDock("tests");
  } catch (error) {
    setStatus("Verification unavailable", false, true);
    $("terminal-output").textContent = error.message;
    addActivity(`Verification unavailable · ${error.message}`, "!");
    toast(error.message, "error");
  } finally {
    $("run-command").disabled = false;
  }
}

function closePalette() {
  paletteFlow?.to(0);
}

function paletteItems() {
  return [
    ["Open a file", "Ctrl P", () => openPalette("files")],
    ["Search repository", "Ctrl Shift F", () => setView("search", { focus: true })],
    ["Build an engineering plan", "", () => { setContextOpen(true); $("task").focus(); }],
    ["Review Git changes", "", () => setView("changes")],
    ["Run verification", "", () => runCommand()],
    ["Analyze repository again", "", () => loadAnalysis()],
    ["Toggle verification panel", "Ctrl `", () => toggleDock()],
  ];
}

function renderPalette(filter = "", mode = "commands") {
  const query = filter.toLocaleLowerCase();
  if (mode === "files") {
    const files = state.files.filter((file) => file.path.toLocaleLowerCase().includes(query)).slice(0, 60);
    $("palette-results").innerHTML = files.length
      ? files.map((file) => `<button class="palette-command" type="button" data-quick="${encodeURIComponent(file.path)}"><span>${esc(file.path)}</span><kbd>${esc(file.path.split("/").pop())}</kbd></button>`).join("")
      : '<p class="palette-empty">No matching repository files.</p>';
    $$('[data-quick]').forEach((button) => button.addEventListener("click", () => {
      closePalette();
      void openFile(decodeURIComponent(button.dataset.quick));
    }));
    return;
  }
  const items = paletteItems().filter((item) => item[0].toLocaleLowerCase().includes(query));
  $("palette-results").innerHTML = items.length
    ? items.map((item, index) => `<button class="palette-command" type="button" data-command="${index}"><span>${esc(item[0])}</span><kbd>${esc(item[1])}</kbd></button>`).join("")
    : '<p class="palette-empty">No command matches this query.</p>';
  $$('[data-command]').forEach((button) => button.addEventListener("click", () => {
    const item = items[Number(button.dataset.command)];
    closePalette();
    item[2]();
  }));
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

/* old animation, disconnected by motion upgrade:
// Legacy dockHeightSpring and dockActiveSpring
*/

function activateJourney(name) {
  $$(".journey-step").forEach((button) => button.classList.toggle("is-active", button.dataset.journey === name));
  const activeStep = document.querySelector(`.journey-step[data-journey="${name}"]`);
  if (activeStep && journeyIndicator) {
    journeyIndicator.moveTo(activeStep);
  }
  const workbench = $("workbench");
  if (name === "understand") { setView("explorer"); return; }
  if (name === "investigate") { setView("search", { focus: true }); return; }
  if (name === "plan") {
    setContextOpen(true);
    $("task").focus();
    return;
  }
  if (name === "review") { setView("changes"); setDock("output"); return; }
  if (name === "verify") { setDock("terminal"); $("command").focus(); }
}

function toggleFind(show) {
  const strip = $("file-find");
  const visible = show ?? strip.hidden;
  strip.hidden = !visible;
  $("find-file").setAttribute("aria-expanded", String(visible));
  if (visible) {
    $("file-find-input").focus();
    updateFind();
  }
}

function closeCurrentFile(path) {
  if (state.dirty.has(path) && !window.confirm(`Discard unsaved changes in ${path}?`)) return;
  const tabEl = document.querySelector(`.tab[data-tab="${encodeURIComponent(path)}"]`);
  const flip = new FlipGroup("#tabs", { preset: "glide" });
  flip.snapshot(".tab");

  if (tabEl) {
    tabEl.classList.add("tab-leaving");
  }

  window.setTimeout(() => {
    state.openFiles = state.openFiles.filter((item) => item !== path);
    state.dirty.delete(path);
    const wasActive = state.activePath === path;
    if (wasActive) state.activePath = state.openFiles.at(-1) || null;
    renderTabs();
    flip.play(".tab");
    if (wasActive) renderEditor();
    buildTree();
  }, 100);
}

function bindEvents() {
  $("tree").addEventListener("click", (event) => {
    const file = event.target.closest("[data-file]");
    const folder = event.target.closest("[data-folder]");
    if (file) {
      void openFile(decodeURIComponent(file.dataset.file));
    }
    if (folder) {
      const folderContainer = folder.closest(".tree-folder");
      const wrapper = folderContainer ? folderContainer.querySelector(":scope > .tree-folder-wrapper") : null;
      if (!folderContainer || !wrapper) return;
      const willCollapse = !folderContainer.classList.contains("is-collapsed");
      folderContainer.classList.toggle("is-collapsed", willCollapse);
      wrapper.classList.toggle("is-collapsed", willCollapse);
      if (!willCollapse) {
        const children = wrapper.querySelectorAll(":scope > .tree-children > .tree-row, :scope > .tree-children > .tree-folder > .tree-row");
        const count = Math.min(children.length, 6);
        for (let i = 0; i < count; i++) {
          const el = children[i];
          el.style.animation = `tree-child-enter var(--t-fast, 160ms) var(--ease-out) ${i * 20}ms backwards`;
        }
      }
      if (treeIndicator) {
        const sel = $("tree").querySelector(".tree-row.is-selected");
        if (sel) treeIndicator.moveTo(sel);
      }
    }
  });
  $("tabs").addEventListener("click", (event) => {
    const close = event.target.closest("[data-close]");
    if (close) {
      event.stopPropagation();
      closeCurrentFile(decodeURIComponent(close.dataset.close));
      return;
    }
    const tab = event.target.closest("[data-tab]");
    if (tab) {
      state.activePath = decodeURIComponent(tab.dataset.tab);
      renderTabs();
      renderEditor();
    }
  });
  $("changes-list").addEventListener("click", (event) => {
    const row = event.target.closest("[data-change]");
    if (row) void showDiff(decodeURIComponent(row.dataset.change));
  });
  $("search-results").addEventListener("click", (event) => {
    const row = event.target.closest("[data-result]");
    if (row) void openFile(decodeURIComponent(row.dataset.result));
  });
  $("editor").addEventListener("scroll", () => {
    $("line-numbers").scrollTop = $("editor").scrollTop;
    $("code-highlight").style.transform = `translate(${-$("editor").scrollLeft}px, ${-$("editor").scrollTop}px)`;
  });
  $("editor").addEventListener("input", markDirty);
  $("save").addEventListener("click", () => void saveFile());
  $("explorer-open").addEventListener("click", () => setSidebarOpen(true));
  $("context-open").addEventListener("click", () => { setContextOpen(true); $("task").focus(); });
  $("empty-open").addEventListener("click", () => openPalette("files"));
  $("empty-search").addEventListener("click", () => setView("search", { focus: true }));
  $("find-file").addEventListener("click", () => toggleFind());
  $("file-find-close").addEventListener("click", () => toggleFind(false));
  $("file-find-input").addEventListener("input", updateFind);
  $("generate").addEventListener("click", () => void generatePlan());
  $("ai-settings-form").addEventListener("submit", (event) => void saveAIProvider(event));
  $("ai-provider").addEventListener("change", updateAIProviderFields);
  $("ai-test").addEventListener("click", () => void testAIProvider());
  $("ai-remove").addEventListener("click", () => void removeAIProvider());
  $("run-command").addEventListener("click", () => void runCommand());
  $("refresh").addEventListener("click", () => void loadAnalysis());
  $("quick-open").addEventListener("click", () => openPalette("files"));
  $("command-open").addEventListener("click", () => openPalette());
  $("palette-close").addEventListener("click", closePalette);
  $("modal-backdrop").addEventListener("click", (event) => { if (event.target === $("modal-backdrop")) closePalette(); });
  $("palette-input").addEventListener("input", (event) => renderPalette(event.target.value, event.target.dataset.mode));
  $("search-input").addEventListener("input", () => {
    window.clearTimeout(state.searchTimer);
    state.searchTimer = window.setTimeout(() => void searchRepository(), 180);
  });
  $("search-input").addEventListener("keydown", (event) => { if (event.key === "Enter") void searchRepository(); });
  $("task").addEventListener("keydown", (event) => { if ((event.ctrlKey || event.metaKey) && event.key === "Enter") void generatePlan(); });
  $("command").addEventListener("keydown", (event) => { if (event.key === "Enter") void runCommand(); });
  $$(".rail-button[data-view]").forEach((button) => button.addEventListener("click", () => {
    const view = button.dataset.view;
    if (view === "settings") {
      toggleSettings();
      return;
    }
    if (view === state.activeView && isSidebarVisible()) {
      setSidebarOpen(false);
      return;
    }
    const alreadyOpen = isSidebarVisible();
    if (alreadyOpen) {
      sideFlow?.setTrigger(button);
    }
    setView(view, { triggerEl: button });
  }));
  $$(".journey-step").forEach((button) => button.addEventListener("click", () => activateJourney(button.dataset.journey)));
  $$(".dock-tab").forEach((tab) => tab.addEventListener("click", () => setDock(tab.dataset.dock)));
  $("dock-toggle").addEventListener("click", toggleDock);
  $("sidebar-close").addEventListener("click", () => setSidebarOpen(false));
  $("sidebar-scrim").addEventListener("click", () => setSidebarOpen(false));
  $("settings-close")?.addEventListener("click", () => closeSettings());
  $("keys-close")?.addEventListener("click", () => closeKeys());
  $$(".rail-button").forEach((btn) => {
    btn.addEventListener("pointerdown", () => btn.classList.add("is-pressed"));
    const release = () => btn.classList.remove("is-pressed");
    btn.addEventListener("pointerup", release);
    btn.addEventListener("pointercancel", release);
    btn.addEventListener("pointerleave", release);
  });
  $("sidebar-resize").addEventListener("pointerdown", (event) => {
    if (window.matchMedia("(max-width: 1110px)").matches) return;
    state.resizingSidebar = true;
    $("sidebar-resize").setPointerCapture(event.pointerId);
    document.body.classList.add("is-resizing");
  });
  $("sidebar-resize").addEventListener("pointermove", (event) => {
    if (!state.resizingSidebar) return;
    const width = Math.min(420, Math.max(210, event.clientX - 58));
    document.documentElement.style.setProperty("--explorer-width", `${width}px`);
  });
  $("sidebar-resize").addEventListener("pointerup", () => {
    state.resizingSidebar = false;
    document.body.classList.remove("is-resizing");
  });
  $("context-close").addEventListener("click", () => {
    setContextOpen(false);
  });
  $("home").addEventListener("click", () => {
    setView("explorer");
  });
  $("help").addEventListener("click", () => toggleKeys());
  $("boot-retry").addEventListener("click", () => {
    $("boot-failure").hidden = true;
    setBoot("Trying the local workspace again", "Requesting repository analysis.");
    void loadAnalysis({ initial: true });
  });
  $("boot-continue").addEventListener("click", finishBoot);
  document.addEventListener("keydown", (event) => {
    const modifier = event.ctrlKey || event.metaKey;
    if (event.key === "Escape") {
      if (!$("modal-backdrop").hidden) closePalette();
      else if (settingsFlow && settingsFlow.p.target === 1) closeSettings();
      else if (keysFlow && keysFlow.p.target === 1) closeKeys();
      else if (window.matchMedia("(max-width: 1110px)").matches) setSidebarOpen(false);
      return;
    }
    if (modifier && event.shiftKey && event.key.toLowerCase() === "p") {
      event.preventDefault();
      window.ForgeFX?.pulse(document.querySelector("#command-open"));
      openPalette();
      return;
    }
    if (modifier && event.shiftKey && event.key.toLowerCase() === "f") {
      event.preventDefault();
      window.ForgeFX?.pulse(document.querySelector('.rail-button[data-view="search"]'));
      setView("search", { focus: true });
      return;
    }
    if (modifier && event.key.toLowerCase() === "p") {
      event.preventDefault();
      window.ForgeFX?.pulse(document.querySelector("#quick-open"));
      openPalette("files");
      return;
    }
    if (modifier && event.key.toLowerCase() === "s") {
      event.preventDefault();
      window.ForgeFX?.pulse(document.querySelector("#save"));
      void saveFile();
      return;
    }
    if (modifier && event.key === "`") {
      event.preventDefault();
      window.ForgeFX?.pulse(document.querySelector("#dock-toggle"));
      toggleDock();
      return;
    }
    if (modifier && event.key.toLowerCase() === "b") {
      event.preventDefault();
      window.ForgeFX?.pulse(document.querySelector('.rail-button[data-view="explorer"]'));
      setSidebarOpen(!$("sidebar").classList.contains("is-open"));
    }
  });

  document.addEventListener("pointerdown", (event) => {
    if (settingsFlow && (settingsFlow.p.target === 1 || (settingsFlow.live && settingsFlow.p.target === 1))) {
      const panel = $("settings-panel");
      const btn = document.querySelector('.rail-button[data-view="settings"]');
      if (panel && !panel.contains(event.target) && btn && !btn.contains(event.target)) {
        closeSettings();
      }
    }
    if (keysFlow && (keysFlow.p.target === 1 || (keysFlow.live && keysFlow.p.target === 1))) {
      const panel = $("keys-panel");
      const btn = $("help");
      if (panel && !panel.contains(event.target) && btn && !btn.contains(event.target)) {
        closeKeys();
      }
    }
  }, true);
}

function initialize() {
  // old animation, disconnected by motion upgrade:
  /*
  sidebarMorph = MorphPanel.attach({
    id: "sidebar",
    trigger: () => document.querySelector(`.rail-button[data-view="${state.activeView}"]`) || $("explorer-open"),
    panel: () => $("sidebar"),
    group: "rail",
    anchor: "left",
    direction: "right",
    closeOnOutsideClick: false,
    closeOnEsc: false,
    layoutReflow: { target: "#main-content", container: "#workbench", collapsedClass: "explorer-is-collapsed", axis: "x", size: 274 },
  });
  window.__sidebarMorph = sidebarMorph;
  */

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
  if (isSidebarVisible()) {
    sideFlow.p.value = 1;
    sideFlow.p.target = 1;
  }
  window.__sideFlow = sideFlow;
  window.setSidebarOpen = setSidebarOpen;
  window.setView = setView;
  window.isSidebarVisible = isSidebarVisible;

  /* old animation, disconnected by motion upgrade:
  settingsMorph = MorphPanel.attach({
    id: "settings",
    trigger: () => document.querySelector('.rail-button[data-view="settings"]'),
    panel: () => $("settings-panel"),
    group: "floating",
    anchor: "bottom-left",
    direction: "right",
  });
  */

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
  window.__settingsFlow = settingsFlow;

  /* old animation, disconnected by motion upgrade:
  keysMorph = MorphPanel.attach({
    id: "keys",
    trigger: () => $("help"),
    panel: () => $("keys-panel"),
    group: "floating",
    anchor: "bottom-left",
    direction: "right",
  });
  */

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
  window.__keysFlow = keysFlow;

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
  window.__dockFlow = dockFlow;

  railIndicator = new SlidingIndicator({
    container: ".activity-rail",
    selector: ".rail-button.is-active",
    className: "rail-indicator",
    axis: "y",
    stretch: true,
  });

  treeIndicator = new SlidingIndicator({
    container: "#tree",
    selector: ".tree-row.is-selected",
    className: "tree-selection-indicator",
    axis: "y",
    stretch: false,
  });

  tabsIndicator = new SlidingIndicator({
    container: "#tabs",
    selector: ".tab.is-active",
    className: "tab-indicator",
    axis: "x",
    stretch: true,
  });

  journeyIndicator = new SlidingIndicator({
    container: ".journey",
    selector: ".journey-step.is-active",
    className: "journey-indicator",
    axis: "x",
    stretch: true,
  });

  /* old animation, disconnected by motion upgrade:
  sidebarMorph.on("opening", () => {
    $("explorer-open").hidden = true;
  });
  sidebarMorph.on("closed", () => {
    $("sidebar").classList.remove("is-open");
    $("explorer-open").hidden = false;
  });
  */

  dockTabsIndicator = new SlidingIndicator({
    container: ".dock-tabs",
    selector: ".dock-tab.is-active",
    className: "dock-tab-indicator",
    axis: "x",
    stretch: true,
  });

  /* old animation, disconnected by motion upgrade:
  const paletteDialog = document.querySelector(".command-palette");
  if (paletteDialog) {
    palettePresence = new Presence(paletteDialog, {
      preset: "settle",
      offsetY: 16,
      initialScale: 0.96,
    });
  }
  */

  const paletteDialog = document.querySelector(".command-palette");
  if (paletteDialog) {
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
    window.__paletteFlow = paletteFlow;
  }

  reviewBadgeRoller = new BadgeRoller("change-count");

  /* old animation, disconnected by motion upgrade:
  settingsMorph.on("opening", () => {
    const btn = document.querySelector('.rail-button[data-view="settings"]');
    if (btn) btn.classList.add("is-popup-open");
  });
  settingsMorph.on("closed", () => {
    const btn = document.querySelector('.rail-button[data-view="settings"]');
    if (btn) btn.classList.remove("is-popup-open");
  });
  */

  /* old animation, disconnected by motion upgrade:
  keysMorph.on("opening", () => {
    const btn = $("help");
    if (btn) btn.classList.add("is-popup-open");
  });
  keysMorph.on("closed", () => {
    const btn = $("help");
    if (btn) btn.classList.remove("is-popup-open");
  });
  */

  // Sidebar starts open in initial layout
  $("sidebar").classList.add("is-open");
  /* old animation, disconnected by motion upgrade:
  sidebarMorph.state = "open";
  sidebarMorph.progress = 1;
  sidebarMorph.spring.value = 1;
  sidebarMorph.spring.target = 1;
  */
  if (sideFlow) {
    sideFlow.p.value = 1;
    sideFlow.p.target = 1;
  }

  // Initial indicators placement
  const initialBtn = document.querySelector(`.rail-button[data-view="${state.activeView}"]`);
  if (initialBtn && railIndicator) {
    railIndicator.moveTo(initialBtn, true);
  }

  const initialStep = document.querySelector(".journey-step.is-active");
  if (initialStep && journeyIndicator) {
    journeyIndicator.moveTo(initialStep, true);
  }

  bindEvents();
  bindThemeSetting();
  void loadAIProviders();
  void loadAnalysis({ initial: true });
}

initialize();
