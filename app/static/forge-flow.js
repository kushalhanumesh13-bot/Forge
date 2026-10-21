/* forge-flow.js v2 — an icon flows like a river into a panel, and back. Needs forge-fx.js first. */
(function () {
  'use strict';
  if (window.ForgeFlow) return;
  const FX = window.ForgeFX;
  if (!FX) { console.error('[ForgeFlow] load forge-fx.js first'); return; }

  const clamp = FX.clamp;
  const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
  const f1 = (n) => n.toFixed(1);
  const SUP_PATH = !!(window.CSS && CSS.supports && CSS.supports('clip-path', 'path("M0 0 L1 1")'));
  let uid = 0;
  const registry = {};

  /* ---- colors ---- */
  function parseColor(s) {
    s = (s || '').trim(); let m;
    if ((m = /^#([0-9a-f]{3})$/i.exec(s))) { const h = m[1]; return [parseInt(h[0] + h[0], 16), parseInt(h[1] + h[1], 16), parseInt(h[2] + h[2], 16)]; }
    if ((m = /^#([0-9a-f]{6})/i.exec(s))) { const h = m[1]; return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]; }
    if ((m = /^rgba?\(([^)]+)\)/i.exec(s))) { const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(parseFloat); return [p[0], p[1], p[2]]; }
    return [212, 85, 47];
  }
  function solidBg(el) {
    while (el && el !== document.documentElement) {
      const m = /rgba?\(([^)]+)\)/.exec(getComputedStyle(el).backgroundColor);
      if (m) { const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(parseFloat); if (p.length < 4 || p[3] > 0.05) return [p[0], p[1], p[2]]; }
      el = el.parentElement;
    }
    return [255, 255, 255];
  }

  /* ---- outlines ---- */
  function outline(r, edgeN, cornerN) {
    const x = r.x, y = r.y, w = r.w, h = r.h, rad = Math.max(0, Math.min(r.r, w / 2, h / 2)), P = [];
    const edge = (x0, y0, x1, y1) => { for (let i = 0; i < edgeN; i++) { const t = i / edgeN; P.push(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t); } };
    const arc = (cx, cy, a0) => { for (let i = 0; i < cornerN; i++) { const a = (a0 + 90 * i / cornerN) * Math.PI / 180; P.push(cx + rad * Math.cos(a), cy + rad * Math.sin(a)); } };
    edge(x + rad, y, x + w - rad, y);         arc(x + w - rad, y + rad, -90);
    edge(x + w, y + rad, x + w, y + h - rad); arc(x + w - rad, y + h - rad, 0);
    edge(x + w - rad, y + h, x + rad, y + h); arc(x + rad, y + h - rad, 90);
    edge(x, y + h - rad, x, y + rad);         arc(x + rad, y + rad, 180);
    return new Float32Array(P);
  }
  function pathFrom(P, N, ox, oy) {
    const g = (i, c) => P[((i + N) % N) * 2 + c];
    let d = 'M' + f1(g(0, 0) - ox) + ' ' + f1(g(0, 1) - oy);
    for (let i = 0; i < N; i++) {
      const x0 = g(i - 1, 0), y0 = g(i - 1, 1), x1 = g(i, 0), y1 = g(i, 1), x2 = g(i + 1, 0), y2 = g(i + 1, 1), x3 = g(i + 2, 0), y3 = g(i + 2, 1);
      d += 'C' + f1(x1 + (x2 - x0) / 6 - ox) + ' ' + f1(y1 + (y2 - y0) / 6 - oy) + ' ' + f1(x2 - (x3 - x1) / 6 - ox) + ' ' + f1(y2 - (y3 - y1) / 6 - oy) + ' ' + f1(x2 - ox) + ' ' + f1(y2 - oy);
    }
    return d + 'Z';
  }
  function polyFrom(P, N, ox, oy) {
    const a = []; for (let i = 0; i < N; i++) a.push(f1(P[i * 2] - ox) + 'px ' + f1(P[i * 2 + 1] - oy) + 'px');
    return 'polygon(' + a.join(',') + ')';
  }
  function segHit(ax, ay, bx, by, cx, cy, dx, dy) {
    const d1 = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax), d2 = (bx - ax) * (dy - ay) - (by - ay) * (dx - ax);
    const d3 = (dx - cx) * (ay - cy) - (dy - cy) * (ax - cx), d4 = (dx - cx) * (by - cy) - (dy - cy) * (bx - cx);
    return ((d1 > 1e-6 && d2 < -1e-6) || (d1 < -1e-6 && d2 > 1e-6)) && ((d3 > 1e-6 && d4 < -1e-6) || (d3 < -1e-6 && d4 > 1e-6));
  }
  function isSimple(P, N) {
    for (let i = 0; i < N; i++) {
      const b = (i + 1) % N;
      for (let j = i + 2; j < N; j++) {
        if (i === 0 && j === N - 1) continue;
        const d = (j + 1) % N;
        if (segHit(P[2 * i], P[2 * i + 1], P[2 * b], P[2 * b + 1], P[2 * j], P[2 * j + 1], P[2 * d], P[2 * d + 1])) return false;
      }
    }
    return true;
  }

  class Flow {
    constructor(o) {
      this.name = o.name || 'panel'; this.trigger = o.trigger || null; this.panel = o.panel;
      this.knobs = Object.assign({
        lag: 0.32, curve: 0.10, stretch: 0.14, neck: 0.50, wobble: 0.035,
        edgeN: 12, cornerN: 8,
        accent: null, shadow: true, iconOnTop: true, landingBounce: true,
        maxMs: 900,          // hard limit: a flow ALWAYS ends within this many ms of the last click
        open: [0.52, 0.80],  // [response seconds, damping fraction]
        close: [0.38, 0.92]
      }, o.knobs || {});
      this.onSettle = o.onSettle || null;   // (state) => {}   state is 'open' or 'closed'
      this.onProgress = o.onProgress || null;
      this.p = new FX.Spring1D(0, 0.002);
      this.live = false; this.running = false; this.counted = false; this.waiters = [];
      this.kids = []; this.lastCa = -1; this.t0 = 0; this.wd = 0;
      this.lastRect = null;
      this.lastTriggerRect = null;
      if (this.panel && this.panel.offsetWidth > 0 && this.panel.offsetHeight > 0) {
        this.lastRect = this.panel.getBoundingClientRect();
      }
      if (this.trigger && this.trigger.offsetWidth > 0) {
        this.lastTriggerRect = this.trigger.getBoundingClientRect();
      }
      window.addEventListener('resize', () => { this.lastRect = null; this.lastTriggerRect = null; }, { passive: true });
    }
    setTrigger(el) {
      if (!this.live) {
        this.trigger = el;
        if (el && el.offsetWidth > 0) this.lastTriggerRect = el.getBoundingClientRect();
      }
    }
    armWatchdog() { // even if animation frames stop, the flow is forced to finish
      clearTimeout(this.wd);
      this.wd = setTimeout(() => {
        if (!this.live) return;
        this.p.value = this.p.target; this.p.velocity = 0;
        try { this.draw(this.p.value, 0); } catch (e) {}
        this.settle();
      }, this.knobs.maxMs + 400);
    }
    ensureSvg() {
      if (this.svg) return;
      const id = 'ff-sh-' + (++uid);
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('aria-hidden', 'true');
      svg.style.cssText = 'position:fixed;left:0;top:0;width:100vw;height:100vh;pointer-events:none;z-index:40;overflow:visible;display:none;';
      svg.innerHTML = '<defs><filter id="' + id + '" x="-50%" y="-50%" width="200%" height="200%" color-interpolation-filters="sRGB"><feDropShadow dx="0" dy="10" stdDeviation="12" flood-color="#2a1a0a" flood-opacity="0.2"/></filter></defs><path d="" fill="#d4552f"' + (this.knobs.shadow ? ' filter="url(#' + id + ')"' : '') + '/>';
      document.body.appendChild(svg);
      this.svg = svg; this.pathEl = svg.querySelector('path'); this.shEl = svg.querySelector('feDropShadow');
    }
    ensureStatic() {
      if (!this.surface) this.surface = this.knobs.surface ? parseColor(this.knobs.surface) : solidBg(this.panel);
      if (!this.accent) {
        const cv = this.trigger ? getComputedStyle(this.trigger).getPropertyValue('--flow-accent') : '';
        this.accent = parseColor(this.knobs.accent || cv || '#d4552f');
      }
      if (this.tr == null && this.trigger) this.tr = parseFloat(getComputedStyle(this.trigger).borderTopLeftRadius) || 0;
      if (this.pr == null) this.pr = parseFloat(getComputedStyle(this.panel).borderTopLeftRadius) || 0;
    }
    begin(tgRect) {
      const k = this.knobs, pn = this.panel, tg = this.trigger;
      this.ensureSvg();
      this.ensureStatic();
      this.saved = { tg: tg, pPos: pn.style.position, pZ: pn.style.zIndex, tPos: tg.style.position, tZ: tg.style.zIndex };
      if (getComputedStyle(pn).position === 'static') pn.style.position = 'relative';
      pn.style.zIndex = '41';
      if (k.iconOnTop && tg) { if (getComputedStyle(tg).position === 'static') tg.style.position = 'relative'; tg.style.zIndex = '42'; }
      this.kids = Array.from(pn.children).filter((c) => !c.hasAttribute('data-ff-keep'));
      this.lastCa = -1;
      pn.classList.add('ff-active');
      this.measure(tgRect);
      this.svg.style.display = 'block';
      this.live = true;
      if (!this.counted) { this.counted = true; FX.busyDelta(1); }
    }
    measure(tgRect) { // read positions ONCE per open/close (never inside the animation frame)
      /* PATCH: finish any old CSS animation/transition on the panel or its parents, so we measure where the panel REALLY ends up */
      const pn0 = this.panel;
      document.getAnimations().forEach((a) => {
        const el = a.effect && a.effect.target;
        if (el && el.contains && el.contains(pn0) && a.effect.getComputedTiming().iterations !== Infinity) { try { a.finish(); } catch (e) {} }
      });
      const k = this.knobs, t = tgRect || (this.trigger ? this.trigger.getBoundingClientRect() : { left: 0, top: 0, width: 44, height: 49 }), r = pn0.getBoundingClientRect();
      const tr = this.tr ?? 0;
      const pr = this.pr ?? 0;
      this.S = outline({ x: t.left, y: t.top, w: t.width, h: t.height, r: Math.max(tr, Math.min(t.width, t.height) * 0.5) }, k.edgeN, k.cornerN);
      this.E = outline({ x: r.left, y: r.top, w: r.width, h: r.height, r: Math.max(pr, 4) }, k.edgeN, k.cornerN);
      const N = (this.N = this.S.length / 2);
      this.out = new Float32Array(this.S.length);
      this.box = r;
      this.sc = { x: t.left + t.width / 2, y: t.top + t.height / 2 };
      this.ec = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
      let dx = this.ec.x - this.sc.x, dy = this.ec.y - this.sc.y, D = Math.hypot(dx, dy);
      if (D < 1) { dx = 0; dy = -1; D = 1; }
      this.D = D; this.dir = { x: dx / D, y: dy / D };
      let nx = -this.dir.y, ny = this.dir.x;
      const mx = (this.sc.x + this.ec.x) / 2, my = (this.sc.y + this.ec.y) / 2;
      if ((innerWidth / 2 - mx) * nx + (innerHeight / 2 - my) * ny < 0) { nx = -nx; ny = -ny; }
      this.n = { x: nx, y: ny };
      this.w = new Float32Array(N); this.tw = new Float32Array(N); this.theta = new Float32Array(N);
      for (let i = 0; i < N; i++) {
        const ax = this.S[2 * i] - this.sc.x, ay = this.S[2 * i + 1] - this.sc.y, len = Math.hypot(ax, ay) || 1;
        this.w[i] = 0.5 + 0.5 * ((ax / len) * this.dir.x + (ay / len) * this.dir.y);
        this.tw[i] = clamp((0.5 - this.w[i]) / 0.5, 0, 1);
        this.theta[i] = (i / N) * Math.PI * 2;
      }
      this.size0 = Math.min(t.width, t.height); this.size1 = Math.min(r.width, r.height);
    }
    draw(p, v) {
      const k = this.knobs, N = this.N, S = this.S, E = this.E, O = this.out, dir = this.dir, n = this.n, D = this.D;
      const pc = clamp(p, 0, 1), over = Math.max(0, p - 1);
      const st = k.stretch * clamp(Math.abs(v) / 4, 0, 1);
      const bump = Math.sin(Math.PI * pc);
      const neckWin = Math.sin(Math.PI * clamp((pc - 0.08) / 0.5, 0, 1));
      const arcC = k.curve * D * bump;
      const cx = this.sc.x + (this.ec.x - this.sc.x) * pc + n.x * arcC;
      const cy = this.sc.y + (this.ec.y - this.sc.y) * pc + n.y * arcC;
      const size = this.size0 + (this.size1 - this.size0) * pc;
      const den = 1 - k.lag;
      for (let i = 0; i < N; i++) {
        const i2 = i * 2;
        let q = (p - k.lag * (1 - this.w[i])) / den; q = q < 0 ? 0 : q > 1 ? 1 : q;
        const qq = q + over;
        let x = S[i2] + (E[i2] - S[i2]) * qq, y = S[i2 + 1] + (E[i2 + 1] - S[i2 + 1]) * qq;
        const arc = k.curve * D * Math.sin(Math.PI * q);
        x += n.x * arc; y += n.y * arc;
        const ox = x - cx, oy = y - cy, along = ox * dir.x + oy * dir.y, px = ox - along * dir.x, py = oy - along * dir.y;
        x = cx + dir.x * along * (1 + st) + px * (1 - 0.6 * st);
        y = cy + dir.y * along * (1 + st) + py * (1 - 0.6 * st);
        const tw = this.tw[i];
        if (tw > 0 && neckWin > 0) { const m = k.neck * neckWin * tw; x += (S[i2] - x) * m; y += (S[i2 + 1] - y) * m; }
        if (k.wobble > 0) {
          const rx = x - cx, ry = y - cy, rl = Math.hypot(rx, ry) || 1;
          const wob = k.wobble * size * bump * (1 - pc * 0.5) * Math.sin(this.theta[i] * 3 + pc * 8);
          x += (rx / rl) * wob; y += (ry / rl) * wob;
        }
        if (p < 0.98) { x = x < 0 ? 0 : x > innerWidth ? innerWidth : x; y = y < 0 ? 0 : y > innerHeight ? innerHeight : y; }
        O[i2] = x; O[i2 + 1] = y;
      }
      const b = this.box;
      this.pathEl.setAttribute('d', pathFrom(O, N, 0, 0));
      this.panel.style.clipPath = (SUP_PATH && !window.__TEST_USE_POLY) ? 'path("' + pathFrom(O, N, b.left, b.top) + '")' : polyFrom(O, N, b.left, b.top);
      const cm = smooth(0.35, 0.8, pc), A = this.accent, B = this.surface;
      this.pathEl.setAttribute('fill', 'rgb(' + Math.round(A[0] + (B[0] - A[0]) * cm) + ',' + Math.round(A[1] + (B[1] - A[1]) * cm) + ',' + Math.round(A[2] + (B[2] - A[2]) * cm) + ')');
      this.pathEl.setAttribute('opacity', smooth(0, 0.1, pc).toFixed(3));
      if (this.shEl) this.shEl.setAttribute('flood-opacity', (0.22 * Math.pow(bump, 0.7)).toFixed(3));
      // content fade: set directly on the few direct children (cheap), and only when the value changes
      const ca = +smooth(0.5, 0.85, pc).toFixed(3);
      if (ca !== this.lastCa) {
        this.lastCa = ca;
        for (let i = 0; i < this.kids.length; i++) { const s = this.kids[i].style; s.opacity = ca; s.translate = '0 ' + ((1 - ca) * 6).toFixed(2) + 'px'; }
      }
      if (this.onProgress) this.onProgress(p, v);
    }
    to(target, trigger, tgRect) { // to(1) = open, to(0) = close. Safe to call at any moment.
      target = target ? 1 : 0;
      if (trigger && !this.live) this.trigger = trigger;
      if (!this.live && this.p.value === target) {
        if (this.onSettle) this.onSettle(target ? 'open' : 'closed');
        return Promise.resolve();
      }
      if (FX.reduced()) return this.jump(target);
      const wasLive = this.live, changed = this.p.target !== target;
      this.p.target = target;
      const t = this.knobs[target ? 'open' : 'close'];
      this.p.tune(t[0], t[1]);
      if (!wasLive) this.begin(tgRect); else if (changed) this.measure(tgRect);
      this.t0 = performance.now();
      this.armWatchdog();
      this.go();
      return new Promise((res) => this.waiters.push(res));
    }
    go() {
      if (this.running) return;
      this.running = true;
      this.draw(this.p.value, this.p.velocity); // first frame is drawn right now, before the browser paints
      FX.run((dt) => {
        if (!this.live) { this.running = false; return false; }
        try {
          let moving;
          if (performance.now() - this.t0 > this.knobs.maxMs) { this.p.value = this.p.target; this.p.velocity = 0; moving = false; }
          else moving = this.p.step(dt);
          this.draw(this.p.value, this.p.velocity);
          if (moving) return true;
        } catch (err) {
          console.error('[ForgeFlow] ' + this.name + ' crashed, forcing the end state:', err);
          this.p.value = this.p.target; this.p.velocity = 0;
        }
        this.settle(); return false;
      });
    }
    cleanup() {
      clearTimeout(this.wd);
      const pn = this.panel, s = this.saved || {};
      pn.style.clipPath = ''; pn.classList.remove('ff-active');
      for (let i = 0; i < this.kids.length; i++) { const st = this.kids[i].style; st.opacity = ''; st.translate = ''; }
      pn.style.position = s.pPos || ''; pn.style.zIndex = s.pZ || '';
      if (this.knobs.iconOnTop && s.tg) { s.tg.style.position = s.tPos || ''; s.tg.style.zIndex = s.tZ || ''; }
      if (this.svg) this.svg.style.display = 'none';
      this.live = false; this.running = false;
      if (this.counted) { this.counted = false; FX.busyDelta(-1); } // queued heavy work runs now
    }
    settle() {
      const open = this.p.target === 1, trig = this.trigger;
      this.cleanup();
      /* old code, disconnected by lag fix:
      if (open && this.panel && this.panel.offsetWidth > 0) {
        this.lastRect = this.panel.getBoundingClientRect();
      }
      */
      if (this.onSettle) this.onSettle(open ? 'open' : 'closed');
      if (!open && this.knobs.landingBounce && trig) FX.pulse(trig, 'strong');
      const w = this.waiters; this.waiters = []; w.forEach((r) => r());
    }
    jump(target) { // Reduce Motion: no flow, just a short fade
      if (this.live) this.cleanup();
      this.p.value = this.p.target = target; this.p.velocity = 0;
      if (target) this.panel.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 120, easing: 'ease-out' });
      if (this.onSettle) this.onSettle(target ? 'open' : 'closed');
      return Promise.resolve();
    }
  }

  /* ---- helpers for panels that are part of the layout ---- */
  function pullOut(panel) { // take the panel out of the layout but keep it visible at the same spot
    if (!panel || panel.__ffPulled) return;
    const r = panel.getBoundingClientRect(), s = panel.style;
    panel.__ffPulled = { position: s.position, left: s.left, top: s.top, width: s.width, height: s.height, margin: s.margin, boxSizing: s.boxSizing };
    s.position = 'fixed'; s.left = r.left + 'px'; s.top = r.top + 'px'; s.width = r.width + 'px'; s.height = r.height + 'px'; s.margin = '0'; s.boxSizing = 'border-box';
  }
  function restore(panel) { // put the panel's own inline styles back (call it AFTER hiding the panel)
    const o = panel && panel.__ffPulled; if (!o) return;
    const s = panel.style;
    s.position = o.position; s.left = o.left; s.top = o.top; s.width = o.width; s.height = o.height; s.margin = o.margin; s.boxSizing = o.boxSizing;
    panel.__ffPulled = null;
  }
  function soften(el, ms) { // brief fade that hides the one-frame jump when the layout changes
    if (!el || !el.animate || FX.reduced()) return;
    el.animate([{ opacity: 0.55 }, { opacity: 1 }], { duration: ms || 240, easing: 'ease-out' });
  }

  async function selfTest(name) {
    const fl = registry[name], wait = (ms) => new Promise((r) => setTimeout(r, ms));
    if (!fl) { console.error('[ForgeFlow] no flow named', name, 'known:', Object.keys(registry)); return false; }
    const rect = fl.panel.getBoundingClientRect();
    if (!rect.width || !rect.height) { console.warn('[ForgeFlow] OPEN the "' + name + '" panel first, then run again'); return false; }
    let ok = true;
    fl.begin();
    const bad = [];
    for (let i = 0; i <= 26; i++) for (const v of [0, 3]) { const p = i * 0.04; fl.draw(p, v); if (!isSimple(fl.out, fl.N)) bad.push(p.toFixed(2) + '/v' + v); }
    fl.cleanup();
    if (bad.length) { ok = false; console.error('FAIL shape crosses itself at p/v:', bad.join(', '), ' -> lower knobs.neck, then knobs.lag, then knobs.stretch'); }
    else console.log('PASS shape stays a clean outline at 54 sample points');
    for (let i = 0; i < 20; i++) { fl.to(i % 2 ? 1 : 0); await wait(18); }
    fl.to(1); await wait(1600);
    const clean = fl.panel.style.clipPath === '' && !fl.panel.classList.contains('ff-active') && !fl.live && fl.p.value === 1 && FX.busyCount === 0;
    console.log((clean ? 'PASS' : 'FAIL') + ' toggle storm ends clean, open, and not busy');
    return ok && clean;
  }

  window.ForgeFlow = {
    attach(o) { const fl = new Flow(o); registry[fl.name] = fl; return fl; },
    all: registry, selfTest, pullOut, restore, soften,
    scrub(name, p) { const fl = registry[name]; if (!fl) return; if (p == null) { fl.cleanup(); return; } if (!fl.live) fl.begin(); fl.draw(p, 0); }
  };
})();
