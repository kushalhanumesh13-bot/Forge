/* forge-bench.js — scripted run of the main interactions. DEV tool: defines ForgeBench only. */
(function () {
  const S = window.ForgeSmooth; if (!S) return;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const tap = (sel) => { // real pointer events, so the press bounce is part of the measurement
    const el = document.querySelector(sel); if (!el) throw new Error('missing element: ' + sel);
    const r = el.getBoundingClientRect();
    const o = { bubbles: true, cancelable: true, pointerId: 9, pointerType: 'mouse', clientX: r.left + r.width / 2, clientY: r.top + r.height / 2, button: 0 };
    el.dispatchEvent(new PointerEvent('pointerdown', o));
    setTimeout(() => { el.dispatchEvent(new PointerEvent('pointerup', o)); el.click(); }, 60);
  };
  const openClose = (sel) => async () => {
    tap(sel);
    await wait(1100);
    const backdrop = document.getElementById('modal-backdrop');
    if (backdrop && !backdrop.hidden && (sel === '#quick-open' || sel === '#command-open')) {
      tap('#palette-close');
    } else {
      tap(sel);
    }
    await wait(900);
  };
  const storm = (sel, n) => async () => { for (let i = 0; i < n; i++) { tap(sel); await wait(70); } await wait(1300); };
  window.ForgeBench = {
    steps: [
      { name: 'Explore panel open+close', run: openClose('.rail-button[data-view="explorer"]') },
      { name: 'Search panel open+close', run: openClose('.rail-button[data-view="search"]') },
      { name: 'Review panel open+close', run: openClose('.rail-button[data-view="changes"]') },
      { name: 'Plan panel open+close', run: openClose('.rail-button[data-view="tasks"]') },
      { name: 'Settings open+close', run: openClose('.rail-button[data-view="settings"]') },
      { name: 'Keys open+close', run: openClose('#help') },
      { name: 'Verification open+close', run: openClose('#dock-toggle') },
      { name: 'Palette open+close', run: openClose('#quick-open') },
      { name: 'Explore tap storm x12', run: storm('.rail-button[data-view="explorer"]', 12) }
    ],
    run: () => S.bench(S.__steps || window.ForgeBench.steps),
    leak: (sel) => S.leakTest(async () => { tap(sel); await wait(1100); tap(sel); await wait(900); }, 100)
  };
})();
