import { spawn } from "child_process";

const EDGE_PATH = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";

async function main() {
  const edgeProc = spawn(EDGE_PATH, [
    "--headless=new",
    "--remote-debugging-port=9241",
    "--user-data-dir=C:\\Users\\kusha\\AppData\\Local\\Temp\\edge-debug-rect-1",
    "--window-size=1280,800",
    "--disable-gpu",
    "about:blank",
  ]);

  await new Promise(r => setTimeout(r, 1500));

  const targetRes = await fetch("http://127.0.0.1:9241/json/new?http://127.0.0.1:8000/?ghost", { method: "PUT" });
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

  // Wait for workspace boot
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
      console.error("Eval Exception:", res.exceptionDetails);
    }
    return res.result ? res.result.value : null;
  };

  const info = await runEval(`(() => {
    const sb = document.getElementById("sidebar");
    const r = sb.getBoundingClientRect();
    const computed = window.getComputedStyle(sb);
    return {
      rect: { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height },
      viewport: { innerWidth: window.innerWidth, innerHeight: window.innerHeight },
      position: computed.position,
      transform: computed.transform,
      transition: computed.transition,
      classes: sb.className,
      ghostLog: window.ForgeGhost ? window.ForgeGhost.report() : null
    };
  })()`);

  console.log("Initial state:", JSON.stringify(info, null, 2));

  // Now trigger explorer toggle and see what happens
  const toggleInfo = await runEval(`(async () => {
    const expBtn = document.querySelector('.rail-button[data-view="explorer"]');
    const sb = document.getElementById("sidebar");
    
    // Toggle close
    expBtn.click();
    await new Promise(r => setTimeout(r, 50));
    const rDuringClose = sb.getBoundingClientRect();
    await new Promise(r => setTimeout(r, 600));
    
    // Toggle open
    expBtn.click();
    await new Promise(r => setTimeout(r, 50));
    const rDuringOpen = sb.getBoundingClientRect();
    await new Promise(r => setTimeout(r, 600));
    
    return {
      rDuringClose: { left: rDuringClose.left, top: rDuringClose.top, right: rDuringClose.right, bottom: rDuringClose.bottom },
      rDuringOpen: { left: rDuringOpen.left, top: rDuringOpen.top, right: rDuringOpen.right, bottom: rDuringOpen.bottom },
      finalRect: sb.getBoundingClientRect()
    };
  })()`);

  console.log("Toggle info:", JSON.stringify(toggleInfo, null, 2));

  const allLogs = await runEval(`(() => {
    // Read the internal LOG from ForgeGhost
    // In forge-ghost.js LOG is local, but console logs or check
    return window.ForgeGhost.check();
  })()`);
  console.log("Ghost check:", JSON.stringify(allLogs, null, 2));

  edgeProc.kill();
  process.exit(0);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
