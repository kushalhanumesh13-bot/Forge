import { spawn } from 'child_process';

async function test() {
  const edge = spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', [
    '--headless=new',
    '--remote-debugging-port=9231',
    'http://127.0.0.1:8000?themeaudit'
  ]);
  await new Promise(r => setTimeout(r, 1500));
  const list = await (await fetch('http://127.0.0.1:9231/json/list')).json();
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

  for (let i = 0; i < 40; i++) {
    await new Promise(r => setTimeout(r, 200));
    const ready = await send('Runtime.evaluate', {
      expression: 'document.body.classList.contains("workspace-visible") && !!document.querySelector(".twisty")',
      returnByValue: true
    });
    if (ready && ready.result && ready.result.value) break;
  }

  console.log('1. Testing Light Mode Audit after waiting for transition:');
  await send('Runtime.evaluate', { expression: 'ForgeTheme.set("light")' });
  await new Promise(r => setTimeout(r, 400));
  let a1 = await send('Runtime.evaluate', { expression: 'window.ForgeThemeAudit()', returnByValue: true });
  console.log('Light count:', a1.result.value.length);
  if (a1.result.value.length) console.log(a1.result.value.slice(0, 5));

  console.log('2. Testing Dark Mode Audit after waiting for transition:');
  await send('Runtime.evaluate', { expression: 'ForgeTheme.set("dark")' });
  await new Promise(r => setTimeout(r, 400));
  let a2 = await send('Runtime.evaluate', { expression: 'window.ForgeThemeAudit()', returnByValue: true });
  console.log('Dark count:', a2.result.value.length);
  if (a2.result.value.length) console.log(a2.result.value.slice(0, 5));

  ws.close();
  edge.kill();
}
test().catch(console.error);
