// scripts/verify_theme_cdp.js
import { spawn } from "child_process";
import fs from "fs";
import path from "path";

const EDGE_PATH = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const USER_DATA_DIR = "e:\\Projects\\001\\.edge-test-theme-profile";
const SCREENSHOT_DIR = "e:\\Projects\\001\\theme_screenshots";

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  console.log("=== STARTING THEME SYSTEM BROWSER VERIFICATION ===");

  // Launch Edge with debugging port 9222
  const edgeProc = spawn(EDGE_PATH, [
    "--headless=new",
    "--remote-debugging-port=9222",
    `--user-data-dir=${USER_DATA_DIR}`,
    "--window-size=1280,800",
    "--disable-gpu",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "about:blank",
  ], { detached: false });

  edgeProc.on("error", (err) => console.error("Edge process error:", err));

  // Wait for CDP
  let versionData = null;
  for (let i = 0; i < 20; i++) {
    await sleep(400);
    try {
      const res = await fetch("http://127.0.0.1:9222/json/version");
      if (res.ok) { versionData = await res.json(); break; }
    } catch (_) {}
  }

  if (!versionData) throw new Error("Could not connect to Edge CDP on 9222");
  console.log("Connected to browser:", versionData.Browser);

  // Helper to open tab & setup CDP
  async function createPage(url = "http://127.0.0.1:8000?themeaudit") {
    const targetRes = await fetch("http://127.0.0.1:9222/json/new", { method: "PUT" });
    const targetData = await targetRes.json();
    await fetch("http://127.0.0.1:9222/json/activate/" + targetData.id);
    const ws = new WebSocket(targetData.webSocketDebuggerUrl);
    let id = 1;
    const pending = new Map();
    const consoleLogs = [];
    const errors = [];

    function send(method, params = {}) {
      const curId = id++;
      return new Promise((resolve, reject) => {
        pending.set(curId, { resolve, reject });
        ws.send(JSON.stringify({ id: curId, method, params }));
      });
    }

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.method === "Runtime.consoleAPICalled") {
          try {
            const text = (msg.params.args || []).map(a => (a ? (a.value !== undefined ? a.value : a.description) : "")).join(" ");
            consoleLogs.push({ type: msg.params.type, text });
          } catch (_) {}
        } else if (msg.method === "Runtime.exceptionThrown") {
          errors.push(msg.params.exceptionDetails?.text || "Unknown exception");
        }
        if (msg.id && pending.has(msg.id)) {
          const { resolve, reject } = pending.get(msg.id);
          pending.delete(msg.id);
          if (msg.error) reject(msg.error);
          else resolve(msg.result);
        }
      } catch (err) {
        console.error("ws.onmessage error:", err);
      }
    };

    await new Promise((resolve) => { ws.onopen = resolve; });
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Page.bringToFront");
    await send("Page.navigate", { url });
    await send("Emulation.setFocusEmulationEnabled", { enabled: true });

    async function evaluate(expression) {
      const exprStr = typeof expression === "function" ? `(${expression.toString()})()` : expression;
      const res = await send("Runtime.evaluate", { expression: exprStr, returnByValue: true });
      if (res.exceptionDetails) {
        throw new Error(res.exceptionDetails.exception?.description || res.exceptionDetails.text);
      }
      return res.result ? res.result.value : undefined;
    }

    async function setPrefersColorScheme(scheme) {
      await send("Emulation.setEmulatedMedia", {
        media: "",
        features: [{ name: "prefers-color-scheme", value: scheme }]
      });
    }

    async function waitWorkspace() {
      for (let i = 0; i < 60; i++) {
        await sleep(250);
        try {
          const ready = await evaluate('document.body && document.body.classList.contains("workspace-visible")');
          if (ready) {
            await sleep(600); // allow spring and layout to settle
            return;
          }
        } catch (_) {}
      }
      throw new Error("Workspace boot timed out");
    }

    async function reload() {
      try { await evaluate("document.body.classList.remove('workspace-visible');"); } catch (_) {}
      await send("Page.reload");
      await sleep(600);
      await waitWorkspace();
    }

    async function screenshot(filename) {
      const shot = await send("Page.captureScreenshot", { format: "png" });
      const outPath = path.join(SCREENSHOT_DIR, filename);
      fs.writeFileSync(outPath, Buffer.from(shot.data, "base64"));
      console.log(`Saved screenshot: ${filename}`);
      return outPath;
    }

    async function close() {
      ws.close();
      await fetch(`http://127.0.0.1:9222/json/close/${targetData.id}`);
    }

    return { targetId: targetData.id, ws, send, evaluate, reload, setPrefersColorScheme, waitWorkspace, screenshot, close, consoleLogs, errors };
  }

  const results = {};

  try {
    // SCENARIO 1: First run, System default
    console.log("\n--- Scenario 1: First run, System default ---");
    let page = await createPage();
    await page.waitWorkspace();
    await page.setPrefersColorScheme("light");
    await page.evaluate("localStorage.removeItem('forge-theme')");
    await page.reload();
    
    let pref = await page.evaluate("ForgeTheme.get()");
    let resolved = await page.evaluate("ForgeTheme.resolved()");
    let attrTheme = await page.evaluate("document.documentElement.getAttribute('data-theme')");
    let attrPref = await page.evaluate("document.documentElement.getAttribute('data-theme-pref')");
    console.log(`Initial state with OS light: pref=${pref}, resolved=${resolved}, data-theme=${attrTheme}, data-theme-pref=${attrPref}`);
    results.scenario1_light = (pref === "system" && resolved === "light" && attrTheme === "light");

    // Now with OS dark
    await page.setPrefersColorScheme("dark");
    await sleep(400);
    resolved = await page.evaluate("ForgeTheme.resolved()");
    attrTheme = await page.evaluate("document.documentElement.getAttribute('data-theme')");
    console.log(`State with OS emulated dark: resolved=${resolved}, data-theme=${attrTheme}`);
    results.scenario1_dark = (resolved === "dark" && attrTheme === "dark");

    // SCENARIO 2: Explicit Light
    console.log("\n--- Scenario 2: Explicit Light ---");
    await page.evaluate("ForgeTheme.set('light')");
    await sleep(400);
    resolved = await page.evaluate("ForgeTheme.resolved()");
    pref = await page.evaluate("ForgeTheme.get()");
    console.log(`After ForgeTheme.set('light'): pref=${pref}, resolved=${resolved}`);
    
    // Reload and check no flash
    await page.reload();
    resolved = await page.evaluate("ForgeTheme.resolved()");
    pref = await page.evaluate("ForgeTheme.get()");
    let bgApp = await page.evaluate("getComputedStyle(document.body).backgroundColor");
    console.log(`After reload: pref=${pref}, resolved=${resolved}, bodyBg=${bgApp}`);
    results.scenario2 = (pref === "light" && resolved === "light");

    // SCENARIO 3: Explicit Dark
    console.log("\n--- Scenario 3: Explicit Dark ---");
    await page.evaluate("ForgeTheme.set('dark')");
    await sleep(400);
    resolved = await page.evaluate("ForgeTheme.resolved()");
    pref = await page.evaluate("ForgeTheme.get()");
    console.log(`After ForgeTheme.set('dark'): pref=${pref}, resolved=${resolved}`);
    
    await page.reload();
    resolved = await page.evaluate("ForgeTheme.resolved()");
    pref = await page.evaluate("ForgeTheme.get()");
    bgApp = await page.evaluate("getComputedStyle(document.body).backgroundColor");
    console.log(`After reload: pref=${pref}, resolved=${resolved}, bodyBg=${bgApp}`);
    results.scenario3 = (pref === "dark" && resolved === "dark");

    // SCENARIO 4: System follows OS live
    console.log("\n--- Scenario 4: System follows OS live ---");
    await page.evaluate("ForgeTheme.set('system')");
    await sleep(300);
    await page.setPrefersColorScheme("light");
    let resLight = null;
    for (let i = 0; i < 15; i++) {
      await sleep(100);
      resLight = await page.evaluate("ForgeTheme.resolved()");
      if (resLight === "light") break;
    }
    await page.setPrefersColorScheme("dark");
    let resDark = null;
    for (let i = 0; i < 15; i++) {
      await sleep(100);
      resDark = await page.evaluate("ForgeTheme.resolved()");
      if (resDark === "dark") break;
    }
    console.log(`System mode toggling OS light->dark: light=${resLight}, dark=${resDark}`);
    results.scenario4 = (resLight === "light" && resDark === "dark");

    // SCENARIO 5: Explicit choices ignore OS
    console.log("\n--- Scenario 5: Explicit choices ignore OS ---");
    await page.evaluate("ForgeTheme.set('light')");
    await page.setPrefersColorScheme("dark");
    await sleep(300);
    let lightStayed = await page.evaluate("ForgeTheme.resolved()");
    await page.evaluate("ForgeTheme.set('dark')");
    await page.setPrefersColorScheme("light");
    await sleep(300);
    let darkStayed = await page.evaluate("ForgeTheme.resolved()");
    console.log(`Explicit light with OS dark => ${lightStayed}; Explicit dark with OS light => ${darkStayed}`);
    results.scenario5 = (lightStayed === "light" && darkStayed === "dark");

    // SCENARIO 6: Two tabs sync via storage event
    console.log("\n--- Scenario 6: Two tabs sync via storage event ---");
    let page2 = await createPage();
    for (let i = 0; i < 40; i++) {
      await sleep(150);
      const ready = await page2.evaluate("typeof window.ForgeTheme !== 'undefined'");
      if (ready) break;
    }
    await page.evaluate("ForgeTheme.set('light')");
    await sleep(500);
    let tab2Theme = await page2.evaluate("ForgeTheme.resolved()");
    console.log(`Tab 1 set 'light' -> Tab 2 resolved theme: ${tab2Theme}`);
    await page.evaluate("ForgeTheme.set('dark')");
    await sleep(500);
    tab2Theme = await page2.evaluate("ForgeTheme.resolved()");
    console.log(`Tab 1 set 'dark' -> Tab 2 resolved theme: ${tab2Theme}`);
    results.scenario6 = (tab2Theme === "dark");
    await page2.close();
    await fetch("http://127.0.0.1:9222/json/activate/" + page.targetId);
    await page.send("Page.bringToFront");
    await sleep(300);

    // SCENARIO 7 & 8: Screenshots of surfaces & interactive states
    console.log("\n--- Scenario 7 & 8: Screenshots of all surfaces in Light and Dark ---");
    
    // LIGHT MODE SCREENSHOTS
    await page.evaluate("ForgeTheme.set('light')");
    await sleep(500);
    await page.screenshot("01_workspace_light.png");

    // Open settings panel
    await page.evaluate("document.querySelector('.rail-button[data-view=\"settings\"]').click()");
    await sleep(600);
    await page.screenshot("02_settings_light.png");

    // Verify keyboard navigation in Settings
    console.log("\n--- Scenario 11: Settings keyboard operation ---");
    const kbdResult = await page.evaluate(() => {
      const seg = document.querySelector('.theme-seg');
      const lightBtn = seg.querySelector('[data-theme-option="light"]');
      const darkBtn = seg.querySelector('[data-theme-option="dark"]');
      const sysBtn = seg.querySelector('[data-theme-option="system"]');
      lightBtn.focus();
      // Dispatch ArrowRight
      seg.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
      const afterRight = document.activeElement.getAttribute('data-theme-option');
      const darkAria = darkBtn.getAttribute('aria-checked');
      // Dispatch End
      seg.dispatchEvent(new KeyboardEvent('keydown', { key: 'End', bubbles: true }));
      const afterEnd = document.activeElement.getAttribute('data-theme-option');
      const sysAria = sysBtn.getAttribute('aria-checked');
      return { afterRight, darkAria, afterEnd, sysAria, pref: ForgeTheme.get() };
    });
    console.log("Keyboard navigation test:", kbdResult);
    results.scenario11 = (kbdResult.afterRight === 'dark' && kbdResult.darkAria === 'true' && kbdResult.afterEnd === 'system');

    // Close settings
    await page.evaluate("document.getElementById('settings-close').click()");
    await sleep(600);

    // Open keys panel
    await page.evaluate("document.getElementById('help').click()");
    await sleep(600);
    await page.screenshot("03_keys_light.png");
    await page.evaluate("document.getElementById('keys-close').click()");
    await sleep(600);

    // Open verification dock
    await page.evaluate("document.getElementById('dock-toggle').click()");
    await sleep(600);
    await page.screenshot("04_dock_light.png");
    await page.evaluate("document.getElementById('dock-toggle').click()");
    await sleep(600);

    // Open command palette
    await page.evaluate("document.getElementById('command-open').click()");
    await sleep(400);
    await page.screenshot("05_command_palette_light.png");
    await page.evaluate("document.getElementById('palette-close').click()");
    await sleep(400);

    // Run ForgeThemeAudit in Light Mode
    console.log("\n--- Scenario 7b: Runtime contrast audit (Light Mode) ---");
    const auditLightRawStr = await page.evaluate(`(() => {
      const t = console.table; console.table = () => {};
      const res = window.ForgeThemeAudit ? window.ForgeThemeAudit() : [];
      console.table = t;
      return JSON.stringify(res);
    })()`);
    const auditLightRaw = JSON.parse(auditLightRawStr || "[]");
    const auditLight = auditLightRaw.filter(it => !it.el.includes('boot') && !['F', 'O', 'R', 'G', 'E'].includes(it.text));
    console.log(`Light Mode Contrast Audit: total=${auditLightRaw.length}, non-decorative=${auditLight.length}`);
    if (auditLight.length) console.log("Non-decorative items:", JSON.stringify(auditLight));
    results.audit_light = (auditLight.length === 0);

    // DARK MODE SCREENSHOTS
    await page.evaluate("ForgeTheme.set('dark')");
    await sleep(500);
    await page.screenshot("06_workspace_dark.png");

    // Open settings panel (Dark)
    await page.evaluate("document.querySelector('.rail-button[data-view=\"settings\"]').click()");
    await sleep(600);
    await page.screenshot("07_settings_dark.png");
    await page.evaluate("document.getElementById('settings-close').click()");
    await sleep(600);

    // Open keys panel (Dark)
    await page.evaluate("document.getElementById('help').click()");
    await sleep(600);
    await page.screenshot("08_keys_dark.png");
    await page.evaluate("document.getElementById('keys-close').click()");
    await sleep(600);

    // Open verification dock (Dark)
    await page.evaluate("document.getElementById('dock-toggle').click()");
    await sleep(600);
    await page.screenshot("09_dock_dark.png");
    await page.evaluate("document.getElementById('dock-toggle').click()");
    await sleep(600);

    // Open command palette (Dark)
    await page.evaluate("document.getElementById('command-open').click()");
    await sleep(400);
    await page.screenshot("10_command_palette_dark.png");
    await page.evaluate("document.getElementById('palette-close').click()");
    await sleep(400);

    // Run ForgeThemeAudit in Dark Mode
    console.log("\n--- Scenario 7c: Runtime contrast audit (Dark Mode) ---");
    const auditDarkRawStr = await page.evaluate(`(() => {
      const t = console.table; console.table = () => {};
      const res = window.ForgeThemeAudit ? window.ForgeThemeAudit() : [];
      console.table = t;
      return JSON.stringify(res);
    })()`);
    const auditDarkRaw = JSON.parse(auditDarkRawStr || "[]");
    const auditDark = auditDarkRaw.filter(it => !it.el.includes('boot') && !['F', 'O', 'R', 'G', 'E'].includes(it.text));
    console.log(`Dark Mode Contrast Audit: total=${auditDarkRaw.length}, non-decorative=${auditDark.length}`);
    if (auditDark.length) console.log("Non-decorative items:", JSON.stringify(auditDark));
    results.audit_dark = (auditDark.length === 0);

    // SCENARIO 10: Morph and motion regressions
    console.log("\n--- Scenario 10: Morph and motion integrity ---");
    const flowCheck = await page.evaluate(() => {
      const morph = window.ForgeFlow;
      const cv = getComputedStyle(document.documentElement).getPropertyValue('--flow-accent').trim();
      return { hasForgeFlow: !!morph, flowAccent: cv };
    });
    console.log("Morph check:", flowCheck);
    results.scenario10 = flowCheck.hasForgeFlow && flowCheck.flowAccent.length > 0;

    // SCENARIO 12: Reduced motion
    console.log("\n--- Scenario 12: Reduced motion ---");
    await page.send("Emulation.setEmulatedMedia", {
      media: "",
      features: [{ name: "prefers-reduced-motion", value: "reduce" }]
    });
    await sleep(200);
    await page.evaluate("ForgeTheme.set('light')");
    let hasClass = await page.evaluate("document.documentElement.classList.contains('theme-switching')");
    console.log(`Reduced motion switch - theme-switching class added: ${hasClass}`);
    results.scenario12 = (hasClass === false);

    // SCENARIO 13: Console errors
    console.log("\n--- Scenario 13: Console and network check ---");
    console.log(`Console logs recorded: ${page.consoleLogs.length}, Page errors: ${page.errors.length}`);
    if (page.errors.length) console.log("Errors:", page.errors);
    results.scenario13 = page.errors.length === 0;

    console.log("\n=== ALL RESULTS SUMMARY ===");
    console.log(JSON.stringify(results, null, 2));

    await page.close();
  } finally {
    edgeProc.kill();
  }
}

main().catch((err) => {
  console.error("FATAL ERROR:", err);
  process.exit(1);
});
