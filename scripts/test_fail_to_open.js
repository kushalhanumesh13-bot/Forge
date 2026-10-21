import { spawn } from 'child_process';

async function main() {
  const edge = spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', [
    '--headless=new', '--remote-debugging-port=9229', '--user-data-dir=e:\\Projects\\001\\.edge-repro-profile-6', '--window-size=1280,800', 'about:blank'
  ]);
  await new Promise(r => setTimeout(r, 1200));
  const tRes = await fetch('http://127.0.0.1:9229/json/new?http://127.0.0.1:8000/?ghost', { method: 'PUT' });
  const tData = await tRes.json();
  const ws = new WebSocket(tData.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 1;
  const send = (method, params={}) => new Promise(res => {
    const curId = id++;
    const handler = evt => {
      const msg = JSON.parse(evt.data);
      if (msg.id === curId) { ws.removeEventListener('message', handler); res(msg.result); }
    };
    ws.addEventListener('message', handler);
    ws.send(JSON.stringify({ id: curId, method, params }));
  });
  await send('Runtime.enable');
  await new Promise(r => setTimeout(r, 2000));

  const runEval = async (code) => {
    const res = await send('Runtime.evaluate', {
      expression: code,
      returnByValue: true,
      awaitPromise: true
    });
    return res.result ? res.result.value : null;
  };

  const res = await runEval(`(async () => {
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));
    const expBtn = document.querySelector('.rail-button[data-view="explorer"]');
    const searchBtn = document.querySelector('.rail-button[data-view="search"]');
    const changesBtn = document.querySelector('.rail-button[data-view="changes"]');
    const tasksBtn = document.querySelector('.rail-button[data-view="tasks"]');
    const settingsBtn = document.querySelector('.rail-button[data-view="settings"]');
    const helpBtn = document.getElementById("help");
    const dockBtn = document.getElementById("dock-toggle");

    async function runSeq() {
      searchBtn.click(); await sleep(200);
      changesBtn.click(); await sleep(200);
      tasksBtn.click(); await sleep(200);
      expBtn.click(); await sleep(300);

      settingsBtn.click(); await sleep(300);
      document.getElementById("settings-close").click(); await sleep(300);

      helpBtn.click(); await sleep(300);
      document.getElementById("keys-close").click(); await sleep(300);

      dockBtn.click(); await sleep(300);
      dockBtn.click(); await sleep(300);

      // Rapid toggles
      for (let i = 0; i < 5; i++) {
        expBtn.click();
        await sleep(60);
      }
      await sleep(3000);
    }

    console.log("Run 1");
    await runSeq();

    console.log("Run 2");
    await runSeq();

    // Now test opening
    const sb = document.getElementById("sidebar");
    const stateBefore = {
      classes: sb.className,
      style: sb.getAttribute("style"),
      pulled: sb.__ffPulled,
      isSidebarVisible: isSidebarVisible(),
      sideFlowTarget: window.__sideFlow.p.target,
      sideFlowValue: window.__sideFlow.p.value,
      sideFlowLive: window.__sideFlow.live,
      sideFlowRunning: window.__sideFlow.running
    };

    expBtn.click();
    await sleep(400);

    const stateAfter1 = {
      classes: sb.className,
      style: sb.getAttribute("style"),
      pulled: sb.__ffPulled,
      isSidebarVisible: isSidebarVisible(),
      sideFlowTarget: window.__sideFlow.p.target,
      sideFlowValue: window.__sideFlow.p.value,
      sideFlowLive: window.__sideFlow.live,
      sideFlowRunning: window.__sideFlow.running
    };

    // Try clicking again
    expBtn.click();
    await sleep(400);

    const stateAfter2 = {
      classes: sb.className,
      style: sb.getAttribute("style"),
      pulled: sb.__ffPulled,
      isSidebarVisible: isSidebarVisible(),
      sideFlowTarget: window.__sideFlow.p.target,
      sideFlowValue: window.__sideFlow.p.value,
      sideFlowLive: window.__sideFlow.live,
      sideFlowRunning: window.__sideFlow.running
    };

    return { stateBefore, stateAfter1, stateAfter2 };
  })()`);

  console.log("Result:", JSON.stringify(res, null, 2));
  edge.kill();
  process.exit(0);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
