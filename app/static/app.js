const state = {
  analysis: null,
  files: [],
  openFiles: [],
  activePath: null,
  fileContents: {},
  dirty: new Set(),
  activity: [],
  changes: [],
  activeView: "explorer",
  activeDock: "terminal",
  fileRequest: 0,
};

const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[char]));

async function api(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

function toast(message, error = false) {
  const node = $("toast");
  node.textContent = message;
  node.className = `toast show${error ? " error" : ""}`;
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => { node.className = "toast"; }, 3000);
}

function setStatus(value, busy = false) {
  $("status").textContent = value;
  document.querySelector(".connection").classList.toggle("busy", busy);
}

function workspaceName() {
  return state.analysis?.readme?.title || "Workspace";
}

function hasUnsavedChanges() {
  return state.dirty.size > 0;
}

function confirmNavigation() {
  return !hasUnsavedChanges() || window.confirm("You have unsaved changes. Continue without saving?");
}

function log(message, icon = "•") {
  state.activity.unshift({
    time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    message,
    icon,
  });
  $("activity-count").textContent = state.activity.length;
  $("activity").innerHTML = state.activity.map((item) => `
    <div class="activity-row"><span class="activity-time">${item.time}</span>
    <span class="activity-icon">${item.icon}</span><span>${esc(item.message)}</span></div>
  `).join("");
}

function fileIcon(path) {
  const extension = path.split(".").pop().toLowerCase();
  return extension === "py" ? "◆" : extension === "md" ? "▤" : extension === "json" ? "{}" : "·";
}

function fileRow(file, depth) {
  const selected = file.path === state.activePath ? " selected" : "";
  const dirty = state.dirty.has(file.path) ? '<span class="modified-dot"></span>' : "";
  return `<div class="tree-row${selected}" role="treeitem" data-file="${encodeURIComponent(file.path)}" style="padding-left:${8 + depth * 14}px">
    <span class="twisty"></span><span class="file-symbol">${fileIcon(file.path)}</span>
    <span class="file-name">${esc(file.path.split("/").pop())}</span>${dirty}</div>`;
}

function folderRow(name, node, depth) {
  const key = `folder-${depth}-${name}`;
  const folders = Object.keys(node.folders).sort().map((child) => folderRow(child, node.folders[child], depth + 1)).join("");
  const files = node.files.sort((a, b) => a.path.localeCompare(b.path)).map((file) => fileRow(file, depth + 1)).join("");
  return `<div class="tree-folder"><div class="tree-row folder" data-folder="${esc(key)}" style="padding-left:${8 + depth * 14}px">
    <span class="twisty">▾</span><span class="file-symbol">▰</span><span class="file-name">${esc(name)}</span></div>
    <div data-children="${esc(key)}">${folders}${files}</div></div>`;
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
  const folders = Object.keys(root.folders).sort().map((name) => folderRow(name, root.folders[name], 1)).join("");
  const files = root.files.sort((a, b) => a.path.localeCompare(b.path)).map((file) => fileRow(file, 0)).join("");
  $("tree").innerHTML = `<div class="tree-folder"><div class="tree-row folder" style="padding-left:8px">
    <span class="twisty">▾</span><span class="file-symbol">▰</span><span class="file-name">${esc(workspaceName())}</span></div><div>${folders}${files}</div></div>`;
  $("file-count").textContent = `${state.files.length} files`;
  document.querySelectorAll("[data-folder]").forEach((row) => row.addEventListener("click", () => {
    const child = document.querySelector(`[data-children="${row.dataset.folder}"]`);
    const closed = child.classList.toggle("hidden");
    row.querySelector(".twisty").textContent = closed ? "▸" : "▾";
  }));
  document.querySelectorAll("[data-file]").forEach((row) => row.addEventListener("click", () => {
    openFile(decodeURIComponent(row.dataset.file));
  }));
}

async function loadAnalysis() {
  setStatus("Analyzing", true);
  log("Repository analysis started", "◌");
  try {
    state.analysis = await api("/api/repository/analyze", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
    });
    state.files = state.analysis.codebase_understanding?.files || [];
    const name = workspaceName();
    const git = state.analysis.git || {};
    $("repo-title").textContent = name;
    $("repo-name").textContent = name;
    $("branch-name").textContent = git.branch ? `branch ${git.branch}` : "branch unavailable";
    $("repo-summary").innerHTML = `<strong>${esc(state.analysis.project_type || "Unknown project")}</strong><span>${(state.analysis.frameworks || []).map(esc).join(" · ") || "No framework detected"}</span><span>${git.is_repository ? (git.is_clean ? "Clean worktree" : `${git.changed_files?.length || 0} changed files`) : "Not a Git repository"}</span>`;
    buildTree();
    const summary = state.analysis.summary;
    $("status-meta").textContent = `${summary.python_files} Python · ${summary.test_files} tests · ${state.analysis.project_type || "workspace"}`;
    setStatus("Ready");
    log(`Repository analyzed · ${summary.total_files} files`, "✓");
    await loadChanges();
  } catch (error) {
    setStatus("Error");
    log(`Analysis failed · ${error.message}`, "!");
    toast(error.message, true);
  }
}

async function loadChanges() {
  try {
    const data = await api("/api/changes");
    state.changes = data.changes || [];
    $("change-count").textContent = state.changes.length;
    $("changes-count").textContent = `${state.changes.length} files`;
    $("changes-list").innerHTML = state.changes.length
      ? state.changes.map((change) => `<div class="change-row" data-change="${encodeURIComponent(change.path)}">
        <span class="change-status">${esc(change.status)}</span><span class="change-path">${esc(change.path)}</span></div>`).join("")
      : '<div class="empty-side">No changes yet<br><small>Forge modifications will appear here.</small></div>';
    document.querySelectorAll("[data-change]").forEach((row) => row.addEventListener("click", () => {
      showDiff(decodeURIComponent(row.dataset.change));
    }));
  } catch (error) {
    log(`Could not load changes · ${error.message}`, "!");
  }
}

async function openFile(path) {
  if (path === state.activePath || !confirmNavigation()) return;
  const requestId = ++state.fileRequest;
  if (!state.openFiles.includes(path)) state.openFiles.push(path);
  state.activePath = path;
  try {
    const data = await api(`/api/file?path=${encodeURIComponent(path)}`);
    if (requestId !== state.fileRequest || state.activePath !== path) return;
    state.fileContents[path] = data.content;
    renderTabs();
    renderEditor();
    log(`Read ${path}`, "↳");
  } catch (error) {
    toast(`Unable to read ${path}: ${error.message}`, true);
    log(`Read failed · ${path}`, "!");
  }
}

function renderTabs() {
  $("tabs").innerHTML = state.openFiles.length ? state.openFiles.map((path) => `
    <div class="tab ${path === state.activePath ? "active" : ""}" data-tab="${encodeURIComponent(path)}">
      <span class="${state.dirty.has(path) ? "dirty" : ""}">${state.dirty.has(path) ? "● " : ""}${esc(path.split("/").pop())}</span>
      <button class="close" data-close="${encodeURIComponent(path)}" aria-label="Close ${esc(path)}">×</button>
    </div>`).join("") : '<div class="empty-tab">Select a file from Explorer</div>';
  document.querySelectorAll("[data-tab]").forEach((tab) => tab.addEventListener("click", (event) => {
    if (event.target.closest("[data-close]")) return;
    state.activePath = decodeURIComponent(tab.dataset.tab); renderTabs(); renderEditor();
  }));
  document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", (event) => {
    event.stopPropagation();
    const path = decodeURIComponent(button.dataset.close);
    if (state.dirty.has(path) && !window.confirm(`Discard unsaved changes in ${path}?`)) return;
    state.openFiles = state.openFiles.filter((item) => item !== path);
    if (state.activePath === path) state.activePath = state.openFiles.at(-1) || null;
    renderTabs(); renderEditor();
  }));
}

function highlight(source) {
  let html = esc(source);
  html = html.replace(/(&quot;.*?&quot;|&#39;.*?&#39;)/g, '<span class="tok-string">$1</span>');
  html = html.replace(/(^|\n)(\s*#.*)/g, '$1<span class="tok-comment">$2</span>');
  html = html.replace(/\b(def|class|return|from|import|if|else|elif|for|in|not|and|or|True|False|None|async|await|with|as|try|except|raise)\b/g, '<span class="tok-keyword">$1</span>');
  return html.replace(/\b(\d+)\b/g, '<span class="tok-number">$1</span>');
}

function renderEditor() {
  const content = state.activePath ? (state.fileContents[state.activePath] || "") : "";
  $("editor").value = content;
  $("editor").disabled = !state.activePath;
  $("save").disabled = !state.activePath;
  $("editor-empty").classList.toggle("hidden", Boolean(state.activePath));
  const parts = (state.activePath || "").split("/");
  $("breadcrumbs").innerHTML = `<span>${esc(workspaceName())}</span>${parts.map((part) => `<span>/</span><span>${esc(part)}</span>`).join("")}`;
  $("line-numbers").textContent = content ? content.split("\n").map((_, index) => index + 1).join("\n") : " ";
  $("code-highlight").innerHTML = highlight(content);
  $("status-path").textContent = `${workspaceName()} / ${state.activePath || "workspace"}`;
  document.querySelectorAll("[data-file]").forEach((row) => row.classList.toggle("selected", decodeURIComponent(row.dataset.file) === state.activePath));
}

function markDirty() {
  if (!state.activePath) return;
  state.fileContents[state.activePath] = $("editor").value;
  state.dirty.add(state.activePath);
  $("code-highlight").innerHTML = highlight($("editor").value);
  $("line-numbers").textContent = $("editor").value.split("\n").map((_, index) => index + 1).join("\n");
  renderTabs(); buildTree();
}

async function saveFile() {
  if (!state.activePath) return;
  try {
    await api("/api/file/write", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path: state.activePath, content: $("editor").value }) });
    state.dirty.delete(state.activePath); renderTabs(); buildTree(); toast("Saved"); log(`Updated ${state.activePath}`, "✓"); await loadChanges();
  } catch (error) { toast(`Unable to save ${state.activePath}: ${error.message}`, true); log(`Save failed · ${error.message}`, "!"); }
}

function setView(view) {
  state.activeView = view;
  document.querySelectorAll(".rail-button[data-view]").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  ["explorer", "search", "changes", "tasks"].forEach((name) => $(`${name}-view`).classList.toggle("hidden", name !== view));
  const labels = { explorer: ["WORKSPACE", "Explorer"], search: ["WORKSPACE", "Search"], changes: ["SOURCE CONTROL", "Changes"], tasks: ["WORKSPACE", "Tasks"] };
  $("side-eyebrow").textContent = labels[view][0]; $("side-title").textContent = labels[view][1];
  if (view === "changes") loadChanges();
}

async function searchRepository() {
  const query = $("search-input").value.trim();
  if (!query) { $("search-results").innerHTML = ""; $("search-meta").textContent = "Search files, symbols, and text"; return; }
  try {
    const data = await api("/api/search", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query }) });
    $("search-meta").textContent = `${data.match_count || 0} matches`;
    $("search-results").innerHTML = data.matches?.map((match) => `<div class="result" data-result="${encodeURIComponent(match.path)}"><div class="result-path">${esc(match.path)}</div><div class="result-line"><b>${match.line}</b> · ${esc(match.snippet)}</div></div>`).join("") || '<div class="empty-side">No matches found.</div>';
    document.querySelectorAll("[data-result]").forEach((row) => row.addEventListener("click", () => openFile(decodeURIComponent(row.dataset.result))));
  } catch (error) { toast(error.message, true); }
}

async function showDiff(path) {
  setView("changes"); openFile(path);
  try { const data = await api(`/api/changes/diff?path=${encodeURIComponent(path)}`); if (data.diff) { $("output-log").textContent = data.diff; setDock("output"); } else toast("No textual diff available for this file"); }
  catch (error) { toast(error.message, true); }
}

function renderPlan(result) {
  const plan = result.plan || {}; const impact = plan.impact || {}; const tests = plan.tests || {};
  const task = plan.task || {}; const confidence = { high: "High", medium: "Medium", low: "Low" }[plan.confidence || result.confidence] || "Unrated";
  const risks = plan.risks || []; const ambiguity = plan.ambiguity || {};
  $("plan").innerHTML = `<div class="plan-summary"><div class="plan-title">${esc(plan.objective || task.description || "No objective returned")}</div><div class="plan-badges"><span class="badge">${esc((task.type || result.classification || "unknown").replaceAll("_", " "))}</span><span class="confidence">${confidence} confidence</span><span class="plan-state">Plan only</span></div></div>
    <div class="evidence"><div><strong>${plan.affected_files?.length || 0}</strong><span>affected files</span></div><div><strong>${impact.dependents?.length || 0}</strong><span>dependents</span></div><div><strong>${tests.existing_tests?.length || 0}</strong><span>related tests</span></div><div><strong>${risks.length}</strong><span>risks</span></div></div>
    ${ambiguity.needs_clarification ? `<div class="callout warning"><strong>Clarification needed</strong><span>${(ambiguity.questions || []).map(esc).join(" ")}</span></div>` : ""}
    <div class="section-label">IMPLEMENTATION PLAN</div><ol class="plan-steps">${(plan.steps || []).map((step, index) => `<li class="plan-step"><span class="step-num">${String(step.order || index + 1).padStart(2, "0")}</span><div><div class="step-text">${esc(step.description || step.action || step)}</div>${step.targets?.length ? `<div class="step-files">${step.targets.map(esc).join(" · ")}</div>` : ""}${step.depends_on?.length ? `<div class="step-dependency">Depends on step ${step.depends_on.join(", ")}</div>` : ""}</div></li>`).join("")}</ol>
    ${plan.affected_symbols?.length ? `<div class="section-label">RELEVANT SYMBOLS</div><div class="chip-list">${plan.affected_symbols.map((symbol) => `<span class="chip">${esc(symbol.name)} <small>${esc(symbol.file)}:${symbol.line}</small></span>`).join("")}</div>` : ""}
    ${risks.length ? `<div class="section-label">RISKS</div><div class="risk-list">${risks.map((risk) => `<div class="risk"><strong>${esc(risk.type.replaceAll("_", " "))}</strong><span>${esc(risk.description)}</span></div>`).join("")}</div>` : ""}
    <div class="section-label">TEST STRATEGY</div><div class="step-files">${(tests.proposed_tests || []).map(esc).join("<br>") || "No test strategy returned."}</div>`;
}

async function generatePlan() {
  const description = $("task").value.trim();
  if (!description) { toast("Describe an engineering change to begin", true); return; }
  setStatus("Planning", true); $("generate").disabled = true; log(`Generating plan · ${description}`, "◌");
  try { const result = await api("/api/task/submit", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ description }) }); renderPlan(result); setStatus("Ready"); log(`Plan generated · ${result.plan.steps.length} steps`, "✓"); setView("tasks"); toast("Engineering plan ready"); }
  catch (error) { setStatus("Ready"); log(`Planning failed · ${error.message}`, "!"); toast(error.message, true); }
  finally { $("generate").disabled = false; }
}

function setDock(name) {
  document.querySelectorAll(".dock-tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.dock === name));
  document.querySelectorAll(".dock-content").forEach((content) => content.classList.toggle("active", content.id === `dock-${name}`));
  $("bottom-dock").classList.remove("collapsed");
}

async function runCommand() {
  const command = $("command").value.trim(); setDock("terminal"); setStatus("Running tests", true); $("run-command").disabled = true; log(`Running ${command}`, "▶");
  try {
    const result = await api("/api/command/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ command }) });
    $("terminal-output").textContent = result.output || "(no output)"; $("output-log").textContent = result.output || "(no output)";
    const match = (result.output || "").match(/(\d+) passed(?:, (\d+) skipped)?(?:, (\d+) failed)?/);
    const passed = match ? Number(match[1]) : 0; const skipped = match ? Number(match[2] || 0) : 0; const failed = result.exitCode === 0 ? 0 : Number(match?.[3] || 1);
    $("test-summary").innerHTML = `<div class="test-metric"><strong>${passed}</strong><span>passed</span></div><div class="test-metric"><strong>${skipped}</strong><span>skipped</span></div><div class="test-metric ${failed ? "failed" : ""}"><strong>${failed}</strong><span>failed</span></div><div class="test-command">${esc(command)}<br>exit code ${result.exitCode}</div>`;
    setStatus(result.exitCode === 0 ? "Ready" : "Test failure"); log(result.exitCode === 0 ? "Tests passed" : "Tests failed", result.exitCode === 0 ? "✓" : "!"); toast(result.exitCode === 0 ? "Tests passed" : "Tests failed", result.exitCode !== 0);
  } catch (error) { setStatus("Error"); $("terminal-output").textContent = error.message; log(`Command failed · ${error.message}`, "!"); toast(error.message, true); }
  finally { $("run-command").disabled = false; }
}

const commands = [
  ["Open File", "Ctrl P", () => quickOpen()], ["Search Repository", "Ctrl ⇧ F", () => setView("search")], ["Run Tests", "", () => runCommand()], ["Show Changes", "", () => setView("changes")], ["Start Forge Task", "", () => { setView("tasks"); $("task").focus(); }], ["Analyze Repository", "", () => loadAnalysis()], ["Toggle Terminal", "Ctrl `", () => $("bottom-dock").classList.toggle("collapsed")], ["Toggle Explorer", "Ctrl B", () => $("sidebar").classList.toggle("hidden")],
];

function palette(filter = "") {
  const items = commands.filter((item) => item[0].toLowerCase().includes(filter.toLowerCase()));
  $("palette-results").innerHTML = items.map((item, index) => `<button class="palette-command" data-command="${index}"><span>${esc(item[0])}</span><kbd>${item[1]}</kbd></button>`).join("") || '<div class="empty-side">No commands found.</div>';
  document.querySelectorAll("[data-command]").forEach((button) => button.addEventListener("click", () => { closePalette(); items[Number(button.dataset.command)][2](); }));
}
function openPalette() { $("modal-backdrop").classList.remove("hidden"); $("palette-title").textContent = "Command palette"; $("palette-input").placeholder = "Type a command…"; $("palette-input").value = ""; palette(); $("palette-input").focus(); }
function closePalette() { $("modal-backdrop").classList.add("hidden"); }
function renderQuickFiles(filter = "") { const files = state.files.filter((file) => file.path.toLowerCase().includes(filter.toLowerCase())).slice(0, 50); $("palette-results").innerHTML = files.map((file) => `<button class="palette-command" data-quick="${encodeURIComponent(file.path)}"><span>${esc(file.path)}</span><kbd>${fileIcon(file.path)}</kbd></button>`).join("") || '<div class="empty-side">No matching files.</div>'; document.querySelectorAll("[data-quick]").forEach((button) => button.addEventListener("click", () => { closePalette(); openFile(decodeURIComponent(button.dataset.quick)); })); }
function quickOpen() { $("modal-backdrop").classList.remove("hidden"); $("palette-title").textContent = "Quick open"; $("palette-input").placeholder = "Search files…"; $("palette-input").value = ""; renderQuickFiles(); $("palette-input").focus(); }

$("editor").addEventListener("input", markDirty);
$("editor").addEventListener("scroll", () => { $("line-numbers").scrollTop = $("editor").scrollTop; $("code-highlight").scrollTop = $("editor").scrollTop; $("code-highlight").scrollLeft = $("editor").scrollLeft; });
$("save").addEventListener("click", saveFile); $("generate").addEventListener("click", generatePlan); $("run-command").addEventListener("click", runCommand); $("refresh").addEventListener("click", loadAnalysis); $("quick-open").addEventListener("click", quickOpen); $("command-open").addEventListener("click", openPalette); $("palette-close").addEventListener("click", closePalette);
$("modal-backdrop").addEventListener("click", (event) => { if (event.target.id === "modal-backdrop") closePalette(); }); $("palette-input").addEventListener("input", (event) => { if ($("palette-title").textContent === "Quick open") renderQuickFiles(event.target.value); else palette(event.target.value); }); $("search-input").addEventListener("input", searchRepository); $("search-input").addEventListener("keydown", (event) => { if (event.key === "Enter") searchRepository(); }); $("task").addEventListener("keydown", (event) => { if ((event.ctrlKey || event.metaKey) && event.key === "Enter") generatePlan(); });
document.querySelectorAll(".rail-button[data-view]").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view))); document.querySelectorAll(".dock-tab").forEach((tab) => tab.addEventListener("click", () => setDock(tab.dataset.dock)));
$("dock-toggle").addEventListener("click", () => $("bottom-dock").classList.toggle("collapsed")); $("sidebar-close").addEventListener("click", () => $("sidebar").classList.add("hidden")); $("context-close").addEventListener("click", () => $("context-panel").classList.add("hidden")); $("home").addEventListener("click", () => { $("context-panel").classList.remove("hidden"); setView("explorer"); });
document.addEventListener("keydown", (event) => { const mod = event.ctrlKey || event.metaKey; if (mod && event.shiftKey && event.key.toLowerCase() === "p") { event.preventDefault(); openPalette(); return; } if (mod && event.key.toLowerCase() === "s") { event.preventDefault(); saveFile(); } if (mod && event.key.toLowerCase() === "p") { event.preventDefault(); quickOpen(); } if (mod && event.shiftKey && event.key.toLowerCase() === "f") { event.preventDefault(); setView("search"); $("search-input").focus(); } if (mod && event.key === "`") $("bottom-dock").classList.toggle("collapsed"); if (mod && event.key.toLowerCase() === "b") $("sidebar").classList.toggle("hidden"); if (event.key === "Escape") closePalette(); });

loadAnalysis();
