import { spawn } from 'child_process';

async function main() {
  const edge = spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', [
    '--headless=new', '--remote-debugging-port=9239', '--user-data-dir=C:\\Users\\kusha\\AppData\\Local\\Temp\\edge-test-profile-6', '--window-size=1280,800', 'about:blank'
  ]);
  await new Promise(r => setTimeout(r, 1200));
  const tRes = await fetch('http://127.0.0.1:9239/json/new?http://127.0.0.1:8000/?ghost', { method: 'PUT' });
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
  console.log('Waiting 12 seconds for boot to finish...');
  await new Promise(r => setTimeout(r, 12000));

  const r = await send('Runtime.evaluate', {
    expression: `(() => {
      const bs = document.getElementById("boot-screen");
      return {
        workspaceVisible: document.body.classList.contains("workspace-visible"),
        bsHidden: bs.hidden,
        bsDisplay: getComputedStyle(bs).display,
        statusText: document.getElementById("status").textContent
      };
    })()`,
    returnByValue: true
  });
  console.log('Boot status:', JSON.stringify(r.result.value, null, 2));

  edge.kill();
  process.exit(0);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
