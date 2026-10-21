import { spawn } from "child_process";

const EDGE_PATH = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";

async function main() {
  const tmpProfile = `C:\\Users\\kusha\\AppData\\Local\\Temp\\edge-trace-${Date.now()}`;
  const edgeProc = spawn(EDGE_PATH, [
    "--headless=new",
    "--remote-debugging-port=9242",
    `--user-data-dir=${tmpProfile}`,
    "--window-size=1280,800",
    "--disable-gpu",
    "about:blank",
  ]);

  await new Promise(r => setTimeout(r, 1500));

  const targetRes = await fetch("http://127.0.0.1:9242/json/new?http://127.0.0.1:8000/?ghost", { method: "PUT" });
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

  await new Promise(r => ws.onopen = r);
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Network.enable");
  await send("Network.setCacheDisabled", { cacheDisabled: true });

  // Wait for boot
  for (let i = 0; i < 40; i++) {
    await new Promise(r => setTimeout(r, 500));
    const evalRes = await send("Runtime.evaluate", {
      expression: 'document.body.classList.contains("workspace-visible") && document.getElementById("boot-screen").hidden',
      returnByValue: true,
    });
    if (evalRes.result && evalRes.result.value === true) break;
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

  const traceResult = await runEval(`(async () => {
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));
    const log = [];
    function snap(tag) {
      const sb = document.getElementById("sidebar");
      const wb = document.getElementById("workbench");
      const r = sb.getBoundingClientRect();
      const cs = getComputedStyle(sb);
      log.push({
        tag,
        rect: Math.round(r.left) + "," + Math.round(r.top) + " " + Math.round(r.width) + "x" + Math.round(r.height),
        classes: sb.className,
        wbClasses: wb ? wb.className : "",
        pos: cs.position,
        left: cs.left,
        transform: cs.transform
      });
    }

    snap("boot");

    // (a) Switch between 3 different menus
    document.querySelector('.rail-button[data-view="search"]').click();
    await sleep(200);
    snap("after-search");
    document.querySelector('.rail-button[data-view="changes"]').click();
    await sleep(200);
    snap("after-changes");
    document.querySelector('.rail-button[data-view="tasks"]').click();
    await sleep(200);
    snap("after-tasks");
    document.querySelector('.rail-button[data-view="explorer"]').click();
    await sleep(400);
    snap("after-explorer");

    // (b) Settings
    document.querySelector('.rail-button[data-view="settings"]').click();
    await sleep(400);
    document.getElementById("settings-close").click();
    await sleep(400);
    snap("after-settings");

    // (c) Keys
    document.getElementById("help").click();
    await sleep(400);
    document.getElementById("keys-close").click();
    await sleep(400);
    snap("after-keys");

    // (d) Dock
    document.getElementById("dock-toggle").click();
    await sleep(400);
    snap("dock-opened");
    document.getElementById("dock-toggle").click();
    await sleep(400);
    snap("dock-closed");

    // (e) First click of rapid sidebar toggle
    const expBtn = document.querySelector('.rail-button[data-view="explorer"]');
    snap("before-e-click-0");
    expBtn.click();
    snap("immediately-after-e-click-0");

    return log;
  })()`);

  console.log("Trace log:", JSON.stringify(traceResult, null, 2));

  edgeProc.kill();
  process.exit(0);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
