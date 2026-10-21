import { spawn } from 'child_process';

async function main() {
  const edge = spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', [
    '--headless=new', '--remote-debugging-port=9228', '--user-data-dir=e:\\Projects\\001\\.edge-repro-profile-5', 'about:blank'
  ]);
  await new Promise(r => setTimeout(r, 1200));
  const tRes = await fetch('http://127.0.0.1:9228/json/new?http://127.0.0.1:8000/?ghost', { method: 'PUT' });
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
  const r = await send('Runtime.evaluate', {
    expression: `(() => {
      const bs = document.getElementById('boot-screen');
      const expBtn = document.querySelector('.rail-button[data-view="explorer"]');
      const r = expBtn.getBoundingClientRect();
      const hit = document.elementFromPoint(r.left + r.width/2, r.top + r.height/2);
      return {
        hit: hit ? (hit.tagName + '.' + hit.className + '#' + hit.id) : null,
        bsHidden: bs.hidden,
        bsDisplay: getComputedStyle(bs).display,
        bsPointerEvents: getComputedStyle(bs).pointerEvents,
        bsOpacity: getComputedStyle(bs).opacity,
        bsZIndex: getComputedStyle(bs).zIndex
      };
    })()`,
    returnByValue: true
  });
  console.log(JSON.stringify(r.result.value, null, 2));
  edge.kill();
  process.exit(0);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
