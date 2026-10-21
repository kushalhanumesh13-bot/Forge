import { spawn } from "child_process";

const EDGE_PATH = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";

async function main() {
  const tmpProfile = `C:\\Users\\kusha\\AppData\\Local\\Temp\\edge-repro-${Date.now()}`;
  const edgeProc = spawn(EDGE_PATH, [
    "--headless=new",
    "--remote-debugging-port=9240",
    `--user-data-dir=${tmpProfile}`,
    "--window-size=1280,800",
    "--disable-gpu",
    "about:blank",
  ]);

  await new Promise(r => setTimeout(r, 1500));

  const targetRes = await fetch("http://127.0.0.1:9240/json/new?http://127.0.0.1:8000/?ghost", { method: "PUT" });
  const targetData = await targetRes.json();
  const ws = new WebSocket(targetData.webSocketDebuggerUrl);

  let id = 1;
  const pending = new Map();
  function send(method, params = {}) {
    const curId = id++;
    return new Promise((resolve, reject) => {
      pending.set(curId, { resolve, reject });
      ws.send(JSON.stringify({ id: curId, method, params }));
    });
  }

  const consoleLogs = [];
  ws.onmessage = (evt) => {
    const msg = JSON.parse(evt.data);
    if (msg.method === "Runtime.consoleAPICalled") {
      const type = msg.params.type;
      const args = msg.params.args.map(a => a.value !== undefined ? a.value : (a.preview ? JSON.stringify(a.preview) : a.description || ""));
      consoleLogs.push(`[${type}] ${args.join(" ")}`);
    }
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(msg.error);
      else resolve(msg.result);
    }
  };

  await new Promise(r => ws.onopen = r);
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Network.enable");
  await send("Network.setCacheDisabled", { cacheDisabled: true });

  // Wait for workspace boot
  console.log("Waiting for workspace to boot...");
  for (let i = 0; i < 40; i++) {
    await new Promise(r => setTimeout(r, 500));
    const evalRes = await send("Runtime.evaluate", {
      expression: 'document.body.classList.contains("workspace-visible") && document.getElementById("boot-screen").hidden',
      returnByValue: true,
    });
    if (evalRes.result && evalRes.result.value === true) {
      console.log(`Workspace ready after ${i * 500}ms!`);
      break;
    }
  }

  const runEval = async (code) => {
    const res = await send("Runtime.evaluate", {
      expression: code,
      returnByValue: true,
      awaitPromise: true,
    });
    if (res.exceptionDetails) {
      console.error("Eval Exception:", res.exceptionDetails.exception ? (res.exceptionDetails.exception.description || res.exceptionDetails.exception.value) : res.exceptionDetails.text);
    }
    return res.result ? res.result.value : null;
  };

  console.log("Starting reproduction sequence...");
  await runEval(`(async () => {
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));
    
    // (a) Switch between 3 different menus in the SAME open pane
    document.querySelector('.rail-button[data-view="search"]').click();
    await sleep(200);
    document.querySelector('.rail-button[data-view="changes"]').click();
    await sleep(200);
    document.querySelector('.rail-button[data-view="tasks"]').click();
    await sleep(200);
    document.querySelector('.rail-button[data-view="explorer"]').click();
    await sleep(400);

    // (b) Open and close Settings popup
    document.querySelector('.rail-button[data-view="settings"]').click();
    await sleep(400);
    document.getElementById("settings-close").click();
    await sleep(400);

    // (c) Open and close Keys popup
    document.getElementById("help").click();
    await sleep(400);
    document.getElementById("keys-close").click();
    await sleep(400);

    // (d) Open and close bottom panel
    document.getElementById("dock-toggle").click();
    await sleep(400);
    document.getElementById("dock-toggle").click();
    await sleep(400);

    // (e) Open and close left panel 5 times fast
    const expBtn = document.querySelector('.rail-button[data-view="explorer"]');
    for (let i = 0; i < 5; i++) {
      expBtn.click();
      await sleep(100);
    }

    // (f) Wait 3 seconds without touching anything
    await sleep(3000);
  })()`);

  const ghostReport = await runEval(`(() => {
    return window.ForgeGhost ? window.ForgeGhost.report() : -1;
  })()`);
  console.log("ForgeGhost report warnings count:", ghostReport);

  const ghostCheck = await runEval(`(() => {
    return window.ForgeGhost ? window.ForgeGhost.check() : null;
  })()`);
  console.log("ForgeGhost check rows:", JSON.stringify(ghostCheck, null, 2));

  // Run Self Tests for each flow
  console.log("Running selfTests...");
  const selfTestResults = await runEval(`(async () => {
    const results = {};
    // Ensure panels are open for selfTest
    setSidebarOpen(true);
    await new Promise(r => setTimeout(r, 600));
    results.side = await ForgeFlow.selfTest('side');

    window.openSettings();
    await new Promise(r => setTimeout(r, 600));
    results.settings = await ForgeFlow.selfTest('settings');
    window.closeSettings();
    await new Promise(r => setTimeout(r, 400));

    window.openKeys();
    await new Promise(r => setTimeout(r, 600));
    results.keys = await ForgeFlow.selfTest('keys');
    window.closeKeys();
    await new Promise(r => setTimeout(r, 400));

    ForgePane.set(window.__dockFlow, true);
    await new Promise(r => setTimeout(r, 600));
    results.dock = await ForgeFlow.selfTest('dock');
    ForgePane.set(window.__dockFlow, false);

    return results;
  })()`);
  console.log("SelfTest results:", JSON.stringify(selfTestResults, null, 2));

  // Test final opening reliability
  console.log("Testing final opening reliability...");
  const finalOpen = await runEval(`(async () => {
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));
    const expBtn = document.querySelector('.rail-button[data-view="explorer"]');
    const sb = document.getElementById("sidebar");

    // Close panel
    setSidebarOpen(false);
    await sleep(500);

    // Attempt open 1
    expBtn.click();
    await sleep(500);
    const open1 = isSidebarVisible() && sb.classList.contains("is-open") && !sb.classList.contains("is-collapsed");

    // Attempt close
    expBtn.click();
    await sleep(500);
    const close1 = !isSidebarVisible() && sb.classList.contains("is-collapsed");

    // Attempt open 2
    expBtn.click();
    await sleep(500);
    const open2 = isSidebarVisible() && sb.classList.contains("is-open") && !sb.classList.contains("is-collapsed");

    // Attempt open 3 (switch to search)
    document.querySelector('.rail-button[data-view="search"]').click();
    await sleep(400);
    const appState = window.getAppState ? window.getAppState() : {};
    const open3 = isSidebarVisible() && appState.activeView === "search";

    return { open1, close1, open2, open3 };
  })()`);
  console.log("Final opening verification:", JSON.stringify(finalOpen, null, 2));

  const allGhostLogs = await runEval(`(() => {
    return window.ForgeGhost && window.ForgeGhost.getLog ? window.ForgeGhost.getLog() : [];
  })()`);
  console.log("=== FORGE GHOST WARN/BEGIN ENTRIES ===");
  if (Array.isArray(allGhostLogs)) {
    for (const entry of allGhostLogs) {
      if (entry.kind === "WARN" || entry.msg.includes("begin:")) {
        console.log(`[${entry.kind}] (${entry.ms}ms) ${entry.msg}`);
      }
    }
  }

  console.log("=== CONSOLE WARN / ERROR LOGS ===");
  for (const log of consoleLogs) {
    if (log.includes("[warning]") || log.includes("[error]")) {
      console.log(log);
    }
  }

  edgeProc.kill();
  process.exit(0);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
