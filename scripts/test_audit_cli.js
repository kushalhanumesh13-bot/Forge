import { spawn } from 'child_process';

async function test() {
  const edge = spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', [
    '--headless=new',
    '--remote-debugging-port=9229',
    'http://127.0.0.1:8000?themeaudit'
  ]);
  await new Promise(r => setTimeout(r, 1500));
  const list = await (await fetch('http://127.0.0.1:9229/json/list')).json();
  const page = list.find(t => t.type === 'page' && t.url.includes('8000'));
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 1;
  const send = (m, p={}) => new Promise(res => {
    const cid = id++;
    const h = (e) => { const d = JSON.parse(e.data); if (d.id === cid) { ws.removeEventListener('message', h); res(d.result); } };
    ws.addEventListener('message', h);
    ws.send(JSON.stringify({ id: cid, method: m, params: p }));
  });
  await send('Page.enable');
  await send('Runtime.enable');
  // Wait for boot to fully complete and settle
  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 200));
    const settled = await send('Runtime.evaluate', {
      expression: 'document.body.classList.contains("workspace-visible") && !document.getElementById("boot-screen").classList.contains("is-ignited") && document.getElementById("boot-screen").style.display === "none"',
      returnByValue: true
    });
    if (settled && settled.result && settled.result.value === true) break;
  }
  await new Promise(r => setTimeout(r, 500));

  let audit = await send('Runtime.evaluate', {
    expression: 'ForgeTheme.set("light"); (window.ForgeThemeAudit ? window.ForgeThemeAudit() : [])',
    returnByValue: true
  });
  console.log('Light Audit:', audit && audit.result ? audit.result.value : 'none');

  let auditDark = await send('Runtime.evaluate', {
    expression: 'ForgeTheme.set("dark"); (window.ForgeThemeAudit ? window.ForgeThemeAudit() : [])',
    returnByValue: true
  });
  console.log('Dark Audit:', auditDark && auditDark.result ? auditDark.result.value : 'none');

  ws.close();
  edge.kill();
}
test().catch(console.error);
