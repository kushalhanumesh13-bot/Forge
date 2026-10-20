import { spawn } from 'child_process';

async function test() {
  const edge = spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', [
    '--headless=new',
    '--remote-debugging-port=9232',
    'http://127.0.0.1:8000?themeaudit'
  ]);
  await new Promise(r => setTimeout(r, 1500));
  const list = await (await fetch('http://127.0.0.1:9232/json/list')).json();
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

  // Wait for tree rows to load
  for (let i = 0; i < 40; i++) {
    await new Promise(r => setTimeout(r, 200));
    const ready = await send('Runtime.evaluate', {
      expression: 'document.body.classList.contains("workspace-visible") && !!document.querySelector(".twisty")',
      returnByValue: true
    });
    if (ready && ready.result && ready.result.value) break;
  }

  // 1. Light Mode (settled)
  await send('Runtime.evaluate', { expression: 'ForgeTheme.set("light")' });
  await new Promise(r => setTimeout(r, 700)); // wait for 260ms transition to end
  let resLight = await send('Runtime.evaluate', {
    expression: `(() => {
      const el = document.querySelector('.twisty');
      return {
        theme: document.documentElement.dataset.theme,
        color: getComputedStyle(el).color,
        sidebarBg: getComputedStyle(document.getElementById('sidebar')).backgroundColor,
        audit: window.ForgeThemeAudit()
      };
    })()`,
    returnByValue: true
  });
  console.log('--- LIGHT MODE ---');
  console.log('theme:', resLight.result.value.theme);
  console.log('twisty color:', resLight.result.value.color);
  console.log('sidebar bg:', resLight.result.value.sidebarBg);
  console.log('audit bad count:', resLight.result.value.audit.length);
  if (resLight.result.value.audit.length) {
    console.log('bad items:', resLight.result.value.audit);
  }

  // 2. Dark Mode (settled)
  await send('Runtime.evaluate', { expression: 'ForgeTheme.set("dark")' });
  await new Promise(r => setTimeout(r, 700)); // wait for 260ms transition to end
  let resDark = await send('Runtime.evaluate', {
    expression: `(() => {
      const el = document.querySelector('.twisty');
      return {
        theme: document.documentElement.dataset.theme,
        color: getComputedStyle(el).color,
        sidebarBg: getComputedStyle(document.getElementById('sidebar')).backgroundColor,
        audit: window.ForgeThemeAudit()
      };
    })()`,
    returnByValue: true
  });
  console.log('\n--- DARK MODE ---');
  console.log('theme:', resDark.result.value.theme);
  console.log('twisty color:', resDark.result.value.color);
  console.log('sidebar bg:', resDark.result.value.sidebarBg);
  console.log('audit bad count:', resDark.result.value.audit.length);
  if (resDark.result.value.audit.length) {
    console.log('bad items:', resDark.result.value.audit);
  }

  ws.close();
  edge.kill();
}
test().catch(console.error);
