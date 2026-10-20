/* forge-smooth.js — smoothness toolkit. Needs forge-fx.js (with the lag-fix patches).

   It never changes forge-flow.js, the press feel, or any morph number. */

(function () {

  'use strict';

  if (window.ForgeSmooth) return;

  const FX = window.ForgeFX;

  if (!FX || !FX.afterIdle) { console.error('[ForgeSmooth] needs forge-fx.js with the lag-fix patches (ForgeFX.afterIdle)'); return; }

  const S = {};

  const reduced = () => FX.reduced();

  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  const OUT = 'cubic-bezier(.22,1,.36,1)', IN = 'cubic-bezier(.4,0,1,1)';

  const pct = (a, p) => { if (!a.length) return 0; const s = a.slice().sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * s.length))]; };



  /* ---------- 1. never block input: yield, chunk, idle, latest ---------- */

  S.yieldToMain = () => (window.scheduler && typeof scheduler.yield === 'function' ? scheduler.yield() : new Promise((r) => setTimeout(r, 0)));

  S.chunk = async function (items, fn, budgetMs) { // process a big array without blocking input

    budgetMs = budgetMs || 8; let t = performance.now();

    for (let i = 0; i < items.length; i++) {

      fn(items[i], i);

      if (performance.now() - t > budgetMs) { await S.yieldToMain(); t = performance.now(); }

    }

  };

  S.idle = (fn, timeout) => (window.requestIdleCallback ? requestIdleCallback(fn, { timeout: timeout || 600 }) : setTimeout(fn, 50));

  S.whenCalm = (fn) => FX.afterIdle(() => S.idle(fn)); // after any panel morph AND when the browser is idle

  S.latest = (fn) => { let id = 0; return async (...a) => { const my = ++id; const r = await fn(...a); return my === id ? r : undefined; }; }; // ignore out-of-order answers



  /* ---------- 2. one shared sliding indicator (underline / highlight block) ---------- */

  S.indicator = function (o) {

    const box = o.container;

    const ind = o.indicator || (function () { const d = document.createElement('span'); d.className = 'fs-ind'; box.appendChild(d); return d; })();

    if (getComputedStyle(box).position === 'static') box.style.position = 'relative';

    ind.style.position = 'absolute'; ind.style.left = '0'; ind.style.top = '0'; ind.style.pointerEvents = 'none'; ind.style.transformOrigin = '0 0';

    const x = new FX.Spring1D(0, 0.05), y = new FX.Spring1D(0, 0.05), w = new FX.Spring1D(0, 0.05), h = new FX.Spring1D(0, 0.05);

    const R = o.response || [0.30, 0.86], RS = o.sizeResponse || [0.36, 0.90]; // size lags a little = natural stretch

    let running = false, ready = false;

    const apply = () => { ind.style.transform = 'translate(' + x.value.toFixed(2) + 'px,' + y.value.toFixed(2) + 'px)'; ind.style.width = Math.max(0, w.value).toFixed(2) + 'px'; ind.style.height = Math.max(0, h.value).toFixed(2) + 'px'; };

    const wake = () => {

      if (running) return; running = true;

      FX.run((dt) => { const m = [x, y, w, h].map((s) => s.step(dt)).some(Boolean); apply(); if (!m) running = false; return m; });

    };

    const rectOf = (el) => { const b = box.getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - b.left + box.scrollLeft, y: r.top - b.top + box.scrollTop, w: r.width, h: r.height }; };

    function go(el, snap) {

      if (!el) return;

      const r = (o.map || ((q) => q))(rectOf(el));

      x.target = r.x; y.target = r.y; w.target = r.w; h.target = r.h;

      if (snap || !ready || reduced()) {

        x.value = r.x; y.value = r.y; w.value = r.w; h.value = r.h; x.velocity = y.velocity = w.velocity = h.velocity = 0;

        ready = true; apply(); return;

      }

      x.tune(R[0], R[1]); y.tune(R[0], R[1]); w.tune(RS[0], RS[1]); h.tune(RS[0], RS[1]);

      wake();

    }

    return { move: (el) => go(el, false), snap: (el) => go(el, true), el: ind };

  };



  /* ---------- 3. lists, tabs, enter/exit, number roll ---------- */

  S.flip = function (els, mutate, opts) { // FLIP: neighbours glide to their new place after you change the DOM

    opts = opts || {}; els = Array.from(els);

    const first = new Map(els.map((e) => [e, e.getBoundingClientRect()]));

    mutate();

    if (reduced()) return;

    els.forEach((e) => {

      if (!e.isConnected || !e.animate) return;

      const a = first.get(e), b = e.getBoundingClientRect(), dx = a.left - b.left, dy = a.top - b.top;

      if (!dx && !dy) return;

      e.animate([{ translate: dx + 'px ' + dy + 'px' }, { translate: '0 0' }], { duration: opts.duration || 340, easing: opts.easing || OUT });

    });

  };

  S.enter = function (el, o) {

    o = o || {}; if (reduced() || !el.animate) return;

    el.animate([{ opacity: 0, translate: '0 ' + (o.y == null ? 6 : o.y) + 'px', scale: String(o.scale || 0.98) }, { opacity: 1, translate: '0 0', scale: '1' }], { duration: o.ms || 240, easing: OUT });

  };

  S.ghostOut = function (el, o) { // fade a copy out where the element WAS; call BEFORE removing the real element

    o = o || {}; if (reduced() || !el.animate) return Promise.resolve();

    const r = el.getBoundingClientRect(), g = el.cloneNode(true);

    g.setAttribute('aria-hidden', 'true'); g.inert = true;

    g.style.cssText += ';position:fixed;left:' + r.left + 'px;top:' + r.top + 'px;width:' + r.width + 'px;height:' + r.height + 'px;margin:0;pointer-events:none;z-index:50;';

    document.body.appendChild(g);

    return g.animate([{ opacity: 1, translate: '0 0', scale: '1' }, { opacity: 0, translate: '0 ' + (o.y == null ? 4 : o.y) + 'px', scale: String(o.scale || 0.96) }], { duration: o.ms || 160, easing: IN, fill: 'forwards' }).finished.catch(() => {}).then(() => g.remove());

  };

  S.rows = function (wrap, open) { // folder rows: toggles the .fs-rows grid animation (see forge-smooth.css)

    wrap.classList.toggle('fs-open', !!open);

    const inner = wrap.firstElementChild; if (inner) inner.inert = !open;

  };

  S.roll = function (el, text) { // number/text change: new value rises in

    text = String(text);

    if (el.__rollText === text) return;

    const old = el.__rollText == null ? el.textContent : el.__rollText;

    el.__rollText = text; el.textContent = text;

    if (reduced() || old === text || !el.animate) return;

    if (getComputedStyle(el).display === 'inline') el.style.display = 'inline-block';

    const dir = (parseFloat(text) || 0) >= (parseFloat(old) || 0) ? 1 : -1;

    el.animate([{ opacity: 0, translate: '0 ' + (dir * 45) + '%' }, { opacity: 1, translate: '0 0' }], { duration: 200, easing: OUT });

  };



  /* ---------- 4. data: cache, intent prefetch, invalidate ---------- */

  const cache = new Map();

  S.fetchJSON = function (url, o) {

    o = o || {}; const ttl = o.ttl == null ? 15000 : o.ttl, hit = cache.get(url);

    if (hit && performance.now() - hit.t < ttl) return hit.p;

    const p = fetch(url, o.init).then((r) => { if (!r.ok) throw new Error(r.status + ' ' + url); return r.json(); });

    cache.set(url, { t: performance.now(), p: p }); p.catch(() => cache.delete(url)); return p;

  };

  S.invalidate = function (prefix) { for (const k of Array.from(cache.keys())) if (!prefix || k.indexOf(prefix) === 0) cache.delete(k); };

  S.prefetchOnIntent = function (selector, urlOf) { // start loading when the pointer rests on / presses an item, before the click

    const seen = new WeakMap(); let timer = 0;

    const go = (e) => {

      const el = e.target && e.target.closest && e.target.closest(selector); if (!el) return;

      const url = urlOf(el); if (!url) return;

      if (performance.now() - (seen.get(el) || -1e9) < 5000) return;

      seen.set(el, performance.now()); S.fetchJSON(url).catch(() => {});

    };

    document.addEventListener('pointerover', (e) => { if (e.pointerType !== 'mouse') return; clearTimeout(timer); timer = setTimeout(() => go(e), 65); }, { passive: true });

    document.addEventListener('pointerdown', go, { capture: true, passive: true });

  };



  /* ---------- 5. measuring: record, bench, HUD, reports ---------- */

  S.budgets = { p95: 17.5, p99: 26, over50: 0, loaf: 2, evP95: 100 };

  S.record = function (label) {

    const R = { frames: [], loaf: [], longtask: 0, ev: [] }, t0 = performance.now(), obs = [];

    let raf = 0, last = 0, alive = true;

    const tick = (ts) => { if (!alive) return; if (last) R.frames.push(ts - last); last = ts; raf = requestAnimationFrame(tick); };

    raf = requestAnimationFrame(tick);

    const watch = (type, cb, extra) => { try { const o = new PerformanceObserver((l) => l.getEntries().forEach(cb)); o.observe(Object.assign({ type: type }, extra || {})); obs.push(o); } catch (e) {} };

    watch('long-animation-frame', (e) => R.loaf.push({ ms: Math.round(e.duration), scripts: (e.scripts || []).slice().sort((a, b) => b.duration - a.duration).slice(0, 2).map((s) => Math.round(s.duration) + 'ms ' + (s.sourceFunctionName || s.invoker || '?') + '@' + String(s.sourceURL || '').split('/').pop()) }));

    watch('longtask', () => { R.longtask++; });

    watch('event', (e) => { if (e.interactionId) R.ev.push(e.duration); }, { durationThreshold: 16 });

    return function stop() {

      alive = false; cancelAnimationFrame(raf); obs.forEach((o) => o.disconnect());

      const f = R.frames;

      return { label: label, ms: Math.round(performance.now() - t0), frames: f.length, p50: +pct(f, 0.5).toFixed(1), p95: +pct(f, 0.95).toFixed(1), p99: +pct(f, 0.99).toFixed(1),

        max: +Math.max(0, ...f).toFixed(1), over25: f.filter((x) => x > 25).length, over50: f.filter((x) => x > 50).length, loaf: R.loaf.length, longtask: R.longtask,

        evP95: +pct(R.ev, 0.95).toFixed(0), evMax: +Math.max(0, ...R.ev).toFixed(0), worstLoaf: R.loaf.slice().sort((a, b) => b.ms - a.ms)[0] || null };

    };

  };

  S.bench = async function (steps, budgets) {

    const B = Object.assign({}, S.budgets, budgets || {}), out = [];

    for (const step of steps) {

      const stop = S.record(step.name);

      try { await step.run(); } catch (e) { console.error('[bench] step failed:', step.name, e); }

      await wait(step.settleMs || 200);

      const r = stop();

      r.pass = r.p95 <= B.p95 && r.p99 <= B.p99 && r.over50 <= B.over50 && r.loaf <= B.loaf && r.evP95 <= B.evP95;

      out.push(r);

    }

    console.table(out.map((r) => ({ step: r.label, frames: r.frames, p50: r.p50, p95: r.p95, p99: r.p99, max: r.max, '>25ms': r.over25, '>50ms': r.over50, LoAF: r.loaf, evP95: r.evP95, result: r.pass ? 'PASS' : 'FAIL' })));

    out.filter((r) => !r.pass && r.worstLoaf).forEach((r) => console.warn('worst long frame in "' + r.label + '": ' + r.worstLoaf.ms + 'ms ' + r.worstLoaf.scripts.join(' | ')));

    console.log(out.every((r) => r.pass) ? 'ALL STEPS PASS' : 'SOME STEPS FAIL');

    return out;

  };

  S.hud = function (on) { // live fps / worst frame / long frames. Ctrl+Alt+P

    if (on === undefined) on = !S._hud;

    if (!on) { if (S._hud) { S._hud.stop(); S._hud = null; } return; }

    const el = document.createElement('div');

    el.style.cssText = 'position:fixed;right:8px;bottom:8px;z-index:2147483647;font:11px/1.35 ui-monospace,Consolas,monospace;color:var(--success);background:var(--bg-overlay);padding:6px 8px;border-radius:6px;pointer-events:none;white-space:pre;';

    document.body.appendChild(el);

    let raf = 0, last = 0, win = [], loaf = 0, shown = 0, alive = true, o = null;

    try { o = new PerformanceObserver((l) => { loaf += l.getEntries().length; }); o.observe({ type: 'long-animation-frame' }); } catch (e) {}

    const tick = (ts) => {

      if (!alive) return;

      if (last) { win.push(ts - last); if (win.length > 120) win.shift(); }

      last = ts;

      if (ts - shown > 500 && win.length) { shown = ts; const mx = Math.max(...win), avg = win.reduce((a, b) => a + b, 0) / win.length; el.textContent = 'fps ' + (1000 / avg).toFixed(0) + '\nworst ' + mx.toFixed(1) + 'ms\nLoAF ' + loaf; el.style.color = mx > 50 ? 'var(--error)' : mx > 25 ? 'var(--warn)' : 'var(--success)'; }

      raf = requestAnimationFrame(tick);

    };

    raf = requestAnimationFrame(tick);

    S._hud = { stop: () => { alive = false; cancelAnimationFrame(raf); if (o) o.disconnect(); el.remove(); } };

  };

  S.idleReport = function () { // what is still moving on an idle page?

    const anims = document.getAnimations().filter((a) => a.playState === 'running').map((a) => { const t = a.effect && a.effect.target; return { target: t ? (t.id || (typeof t.className === 'string' && t.className) || t.tagName) : '?', name: a.animationName || a.transitionProperty || 'waapi', infinite: !!(a.effect && a.effect.getComputedTiming().iterations === Infinity) }; });

    console.log('running animations on an idle page: ' + anims.length); if (anims.length) console.table(anims);

    return anims;

  };

  S.domReport = function () {

    const total = document.getElementsByTagName('*').length;

    const top = Array.from(document.body.querySelectorAll('*')).map((el) => [el, el.getElementsByTagName('*').length]).sort((a, b) => b[1] - a[1]).slice(0, 8)

      .map((p) => ({ el: p[0].tagName.toLowerCase() + (p[0].id ? '#' + p[0].id : '') + (typeof p[0].className === 'string' && p[0].className.trim() ? '.' + p[0].className.trim().split(/\s+/)[0] : ''), descendants: p[1] }));

    console.log('DOM nodes: ' + total); console.table(top); return { total: total, top: top };

  };

  S.leakTest = async function (fn, n) {

    n = n || 100;

    const nodes0 = document.getElementsByTagName('*').length, h0 = performance.memory ? performance.memory.usedJSHeapSize : 0;

    for (let i = 0; i < n; i++) { await fn(i); await wait(30); }

    await wait(1000);

    const nodes1 = document.getElementsByTagName('*').length, h1 = performance.memory ? performance.memory.usedJSHeapSize : 0;

    const r = { cycles: n, nodesDelta: nodes1 - nodes0, heapDeltaKB: Math.round((h1 - h0) / 1024) };

    console.log((r.nodesDelta === 0 && r.heapDeltaKB < 3072 ? 'PASS' : 'FAIL') + ' leak test', r); return r;

  };



  /* ---------- 6. the freeze guard ---------- */

  S.dumpMotion = function () {

    const flows = {}, all = (window.ForgeFlow && ForgeFlow.all) || {};

    Object.keys(all).forEach((k) => { flows[k] = all[k].knobs; });

    return JSON.stringify({ levels: FX.LEVELS, flows: flows }, null, 1);

  };

  S.verifyMotion = function (baselineJson) {

    const ok = S.dumpMotion() === (typeof baselineJson === 'string' ? baselineJson : JSON.stringify(baselineJson, null, 1));

    console.log((ok ? 'PASS' : 'FAIL') + ' morph + press numbers ' + (ok ? 'are unchanged' : 'HAVE CHANGED — revert the last change'));

    return ok;

  };



  window.addEventListener('keydown', (e) => { if (e.ctrlKey && e.altKey && (e.key === 'p' || e.key === 'P')) S.hud(); });

  window.ForgeSmooth = S;

})();