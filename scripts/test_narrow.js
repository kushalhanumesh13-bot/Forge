import { spawn } from 'child_process';

async function main() {
  const edge = spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', [
    '--headless=new', '--remote-debugging-port=9230', '--user-data-dir=e:\\Projects\\001\\.edge-repro-profile-7', '--window-size=800,700', 'about:blank'
  ]);
  await new Promise(r => setTimeout(r, 1200));
  const tRes = await fetch('http://127.0.0.1:9230/json/new?http://127.0.0.1:8000/?ghost', { method: 'PUT' });
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

    await runSeq();
    await runSeq();

    // Now check all elements at the pointer position of expBtn or whatever panel trigger
    const expRect = expBtn.getBoundingClientRect();
    const hitEl = document.elementFromPoint(expRect.left + expRect.width/2, expRect.top + expRect.height/2);
    
    // Attempt final open
    console.log("Attempting final open by clicking expBtn...");
    expBtn.click();
    await sleep(600);

    const sb = document.getElementById("sidebar");
    const cs = getComputedStyle(sb);
    return {
      hitElement: hitEl ? (hitEl.tagName + '.' + hitEl.className) : null,
      sidebarClasses: sb.className,
      sidebarDisplay: cs.display,
      sidebarVisibility: cs.visibility,
      sidebarOpacity: cs.opacity,
      sidebarTransform: cs.transform,
      sidebarClipPath: cs.clipPath,
      sidebarRect: sb.getBoundingClientRect(),
      isSidebarVisible: isSidebarVisible(),
      sideFlow: {
        live: window.__sideFlow.live,
        running: window.__sideFlow.running,
        target: window.__sideFlow.p.target,
        value: window.__sideFlow.p.value
      },
      scrimHidden: document.getElementById("sidebar-scrim").hidden,
      scrimDisplay: getComputedStyle(document.getElementById("sidebar-scrim")).display,
      scrimPointerEvents: getComputedStyle(document.getElementById("sidebar-scrim")).pointerEvents
    };
  })()`);

  console.log("Narrow viewport test result:", JSON.stringify(res, null, 2));
  edge.kill();
  process.exit(0);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
