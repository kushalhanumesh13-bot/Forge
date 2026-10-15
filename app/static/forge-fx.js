/* forge-fx.js — spring engine + press/tap feedback. Self-contained. Exposes window.ForgeFX */
(function () {
  'use strict';
  if (window.ForgeFX) return;

  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const reduced = () => !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const FX = { timeScale: 1, amp: 1, enabled: true, map: [] };

  /* ---- Apple-style spring: response (seconds) + dampingFraction (1 = no bounce, 0.4 = very bouncy) ---- */
  function springParams(response, damping) {
    return { k: Math.pow((2 * Math.PI) / response, 2), c: (4 * Math.PI * damping) / response };
  }
  class Spring1D {
    constructor(value, precision) {
      this.value = value || 0; this.velocity = 0; this.target = this.value;
      this.k = 200; this.c = 20; this.precision = precision || 0.001;
    }
    tune(response, damping) { const p = springParams(response, damping); this.k = p.k; this.c = p.c; }
    step(dt) { // returns true while still moving
      const n = Math.max(1, Math.ceil(dt / (1 / 240))), h = dt / n;
      for (let i = 0; i < n; i++) {
        const a = -this.k * (this.value - this.target) - this.c * this.velocity;
        this.velocity += a * h; this.value += this.velocity * h;
      }
      if (Math.abs(this.velocity) < this.precision && Math.abs(this.value - this.target) < this.precision) {
        this.value = this.target; this.velocity = 0; return false;
      }
      return true;
    }
  }
  const tune = (list, pair) => list.forEach((s) => s.tune(pair[0], pair[1]));

  /* ---- one shared animation loop for everything ---- */
  let jobs = [], raf = 0, last = 0;
  function frame(now) {
    const dt = Math.min((now - last) / 1000, 1 / 30) * FX.timeScale;
    last = now;
    const current = jobs; jobs = [];
    for (let i = 0; i < current.length; i++) if (current[i](dt)) jobs.push(current[i]);
    raf = jobs.length ? requestAnimationFrame(frame) : 0;
  }
  function run(job) { jobs.push(job); if (!raf) { last = performance.now(); raf = requestAnimationFrame(frame); } }

  /* ---- feedback strengths ---- */
  const LEVELS = {
    strong: { down: 0.86,  squash: 0.035, tilt: 3.5, rot: 5,   pop: 1.13, popY: 1.07,  hover: 1.05,  magnet: 2.5, glyph: 1.25 },
    medium: { down: 0.92,  squash: 0.02,  tilt: 2,   rot: 2.5, pop: 1.07, popY: 1.04,  hover: 1.025, magnet: 1.2, glyph: 1.12 },
    soft:   { down: 0.975, squash: 0.005, tilt: 0,   rot: 0,   pop: 1.02, popY: 1.012, hover: 1,     magnet: 0,   glyph: 1 }
  };
  /* spring settings: [response seconds, damping fraction] */
  const SP = {
    down: [0.13, 0.85], pop: [0.17, 0.60], settleX: [0.40, 0.42], settleY: [0.46, 0.38],
    move: [0.12, 0.90], hover: [0.26, 0.80], rest: [0.32, 0.55]
  };

  class Item {
    constructor(el, level) {
      this.el = el; this.cfg = LEVELS[level] || LEVELS.medium;
      this.sx = new Spring1D(1, 0.0008); this.sy = new Spring1D(1, 0.0008);
      this.tx = new Spring1D(0, 0.02); this.ty = new Spring1D(0, 0.02);
      this.rot = new Spring1D(0, 0.02); this.gs = new Spring1D(1, 0.0008);
      this.all = [this.sx, this.sy, this.tx, this.ty, this.rot, this.gs];
      const g = el.querySelector('svg, img, i, .icon');
      this.glyph = g && g !== el ? g : null;
      this.pressed = false; this.hovered = false; this.running = false; this.timers = [];
    }
    later(ms, fn) { this.timers.push(setTimeout(fn, ms)); }
    clearTimers() { this.timers.forEach(clearTimeout); this.timers = []; }
    restScale() { return this.hovered ? 1 + (this.cfg.hover - 1) * FX.amp : 1; }
    apply() {
      const st = this.el.style;
      st.scale = this.sx.value.toFixed(4) + ' ' + this.sy.value.toFixed(4);
      st.translate = this.tx.value.toFixed(2) + 'px ' + this.ty.value.toFixed(2) + 'px';
      st.rotate = this.rot.value.toFixed(2) + 'deg';
      if (this.glyph) this.glyph.style.scale = this.gs.value.toFixed(4);
    }
    clear() {
      const st = this.el.style;
      st.scale = ''; st.translate = ''; st.rotate = ''; st.willChange = '';
      if (this.glyph) this.glyph.style.scale = '';
    }
    wake() {
      if (this.running) return;
      this.running = true;
      this.el.style.willChange = 'scale, translate, rotate';
      run((dt) => {
        let moving = false;
        for (const s of this.all) if (s.step(dt)) moving = true;
        this.apply();
        if (moving) return true;
        this.running = false;
        if (!this.pressed && !this.hovered) this.clear(); else this.el.style.willChange = '';
        return false;
      });
    }
    aim(nx, ny) { // lean toward the pointer while pressed
      const c = this.cfg, a = FX.amp;
      nx = clamp(nx, -1.2, 1.2); ny = clamp(ny, -1.2, 1.2);
      this.tx.target = nx * c.tilt * a;
      this.ty.target = (ny * c.tilt + (c.tilt ? 0.8 : 0)) * a;
      this.rot.target = nx * c.rot * a;
      this.wake();
    }
    hold(nx, ny) { // pointer/finger DOWN: squash
      const c = this.cfg, a = FX.amp;
      this.pressed = true; this.clearTimers();
      tune([this.sx, this.sy, this.gs], SP.down);
      tune([this.tx, this.ty, this.rot], SP.move);
      this.sx.target = 1 - (1 - c.down) * a;
      this.sy.target = 1 - (1 - c.down + c.squash) * a;
      this.gs.target = c.glyph > 1 ? 1 - 0.06 * a : 1;
      this.aim(nx, ny);
    }
    letGo(cancelled) { // pointer/finger UP: pop, then springy settle
      if (!this.pressed) return;
      this.pressed = false; this.clearTimers();
      const c = this.cfg, a = FX.amp;
      tune([this.tx, this.ty, this.rot], SP.rest);
      this.tx.target = 0; this.ty.target = 0; this.rot.target = 0;
      if (cancelled) {
        tune([this.sx, this.sy, this.gs], SP.rest);
        this.sx.target = this.sy.target = this.restScale(); this.gs.target = 1;
        this.wake(); return;
      }
      tune([this.sx, this.sy], SP.pop);
      this.sx.target = 1 + (c.pop - 1) * a;
      this.sy.target = 1 + (c.popY - 1) * a;
      this.later(40, () => { tune([this.gs], SP.pop); this.gs.target = 1 + (c.glyph - 1) * a; this.wake(); });
      this.later(95, () => {
        tune([this.sx], SP.settleX); tune([this.sy], SP.settleY); tune([this.gs], SP.settleX);
        this.sx.target = this.sy.target = this.restScale(); this.gs.target = 1; this.wake();
      });
      this.wake();
    }
    hoverIn() {
      this.hovered = true;
      if (this.pressed || this.cfg.hover === 1) return;
      tune([this.sx, this.sy], SP.hover);
      this.sx.target = this.sy.target = this.restScale(); this.wake();
    }
    hoverMove(nx, ny) {
      if (this.pressed || !this.cfg.magnet) return;
      tune([this.tx, this.ty], SP.hover);
      this.tx.target = clamp(nx, -1, 1) * this.cfg.magnet * FX.amp;
      this.ty.target = clamp(ny, -1, 1) * this.cfg.magnet * FX.amp; this.wake();
    }
    hoverOut() {
      this.hovered = false;
      if (this.pressed) return;
      tune([this.sx, this.sy, this.tx, this.ty, this.rot], SP.rest);
      this.sx.target = this.sy.target = 1; this.tx.target = this.ty.target = this.rot.target = 0; this.wake();
    }
  }

  /* ---- which elements get feedback ---- */
  const BASE = '[data-fx], button, [role="button"], [role="tab"], summary, .btn';
  let fullSel = BASE;
  FX.add = function (selector, level) { // level: 'strong' | 'medium' | 'soft' | 'none'
    FX.map.push([selector, level]);
    fullSel = BASE + ',' + FX.map.map((m) => m[0]).join(',');
  };
  const levelOf = (el) => {
    const a = el.getAttribute('data-fx'); if (a) return a;
    for (let i = FX.map.length - 1; i >= 0; i--) if (el.matches(FX.map[i][0])) return FX.map[i][1];
    return 'medium';
  };
  const items = new WeakMap();
  function pick(node) {
    if (!FX.enabled || reduced() || !node || !node.closest) return null;
    const el = node.closest(fullSel);
    if (!el || el.disabled || el.getAttribute('aria-disabled') === 'true') return null;
    return levelOf(el) === 'none' ? null : el;
  }
  function itemFor(el) { let it = items.get(el); if (!it) { it = new Item(el, levelOf(el)); items.set(el, it); } return it; }
  const norm = (e, r) => [((e.clientX - r.left) / r.width - 0.5) * 2, ((e.clientY - r.top) / r.height - 0.5) * 2];

  let cur = null, hoverEl = null;
  document.addEventListener('pointerdown', (e) => {
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    const el = pick(e.target); if (!el) return;
    const n = norm(e, el.getBoundingClientRect());
    cur = { el: el, id: e.pointerId, it: itemFor(el) };
    cur.it.hold(n[0], n[1]);
  }, { capture: true, passive: true });
  window.addEventListener('pointermove', (e) => {
    if (cur && e.pointerId === cur.id) { const n = norm(e, cur.el.getBoundingClientRect()); cur.it.aim(n[0], n[1]); return; }
    if (e.pointerType === 'mouse' && hoverEl) { const n = norm(e, hoverEl.getBoundingClientRect()); itemFor(hoverEl).hoverMove(n[0], n[1]); }
  }, { passive: true });
  function end(e, cancelled) {
    if (!cur || e.pointerId !== cur.id) return;
    const under = document.elementFromPoint(e.clientX, e.clientY);
    cur.it.letGo(cancelled || !(under && cur.el.contains(under)));
    cur = null;
  }
  window.addEventListener('pointerup', (e) => end(e, false), { passive: true });
  window.addEventListener('pointercancel', (e) => end(e, true), { passive: true });
  document.addEventListener('pointerover', (e) => {
    if (e.pointerType !== 'mouse') return;
    const el = pick(e.target); if (!el || el.contains(e.relatedTarget)) return;
    hoverEl = el; itemFor(el).hoverIn();
  }, { passive: true });
  document.addEventListener('pointerout', (e) => {
    if (e.pointerType !== 'mouse') return;
    const el = pick(e.target); if (!el || el.contains(e.relatedTarget)) return;
    if (hoverEl === el) hoverEl = null; itemFor(el).hoverOut();
  }, { passive: true });
  document.addEventListener('keydown', (e) => {
    if (e.repeat || (e.key !== 'Enter' && e.key !== ' ')) return;
    const el = pick(document.activeElement); if (el) itemFor(el).hold(0, 0);
  }, true);
  document.addEventListener('keyup', (e) => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const el = pick(document.activeElement); if (el) itemFor(el).letGo(false);
  }, true);

  /* ---- public API ---- */
  FX.pulse = function (el, level) { // play the press+release bounce by code (shortcuts, landing bounce)
    const hit = pick(el); if (!hit) return;
    const it = itemFor(hit), keep = it.cfg;
    if (level && LEVELS[level]) it.cfg = LEVELS[level];
    it.hold(0, 0);
    setTimeout(() => { it.letGo(false); it.cfg = keep; }, 70);
  };
  FX.setIntensity = function (name) { // 'off' | 'subtle' | 'springy'
    FX.amp = name === 'off' ? 0 : name === 'subtle' ? 0.5 : 1; FX.enabled = name !== 'off';
    try { localStorage.setItem('forge-fx-intensity', name); } catch (e) {}
  };
  try { const s = localStorage.getItem('forge-fx-intensity'); if (s) FX.setIntensity(s); } catch (e) {}
  window.addEventListener('keydown', (e) => { // Ctrl+Alt+M = slow motion (15%) for inspecting animations
    if (e.ctrlKey && e.altKey && (e.key === 'm' || e.key === 'M')) {
      FX.timeScale = FX.timeScale === 1 ? 0.15 : 1; console.info('[ForgeFX] timeScale =', FX.timeScale);
    }
  });
  FX.selfTest = async function () {
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));
    if (reduced()) { console.warn('[ForgeFX] Reduce Motion is ON; test cannot run.'); return false; }
    const b = document.createElement('button');
    b.setAttribute('data-fx', 'strong'); b.textContent = 'fx';
    b.style.cssText = 'position:fixed;left:20px;top:20px;width:48px;height:48px;z-index:99999;';
    document.body.appendChild(b);
    const ev = (t) => new PointerEvent(t, { bubbles: true, cancelable: true, pointerId: 77, pointerType: 'touch', clientX: 44, clientY: 44, button: 0 });
    let min = 9, max = 0;
    const sampler = setInterval(() => { const v = parseFloat(b.style.scale || '1'); if (v < min) min = v; if (v > max) max = v; }, 8);
    b.dispatchEvent(ev('pointerdown')); await wait(150);
    b.dispatchEvent(ev('pointerup')); await wait(1400);
    clearInterval(sampler);
    const clean1 = b.style.scale === '' && b.style.translate === '' && b.style.rotate === '';
    for (let i = 0; i < 30; i++) { b.dispatchEvent(ev('pointerdown')); await wait(15); b.dispatchEvent(ev('pointerup')); await wait(15); }
    await wait(1600);
    const clean2 = b.style.scale === '' && b.style.translate === '' && b.style.rotate === '';
    b.remove();
    const rows = [['press squashes below 0.95', min < 0.95], ['release bounces above 1.02', max > 1.02],
                  ['styles cleaned after settle', clean1], ['30-tap storm leaves styles clean', clean2]];
    rows.forEach((r) => console.log((r[1] ? 'PASS ' : 'FAIL ') + r[0]));
    console.log('min scale', min.toFixed(3), 'max scale', max.toFixed(3));
    return rows.every((r) => r[1]);
  };

  FX.Spring1D = Spring1D; FX.springParams = springParams; FX.run = run; FX.clamp = clamp; FX.reduced = reduced; FX.LEVELS = LEVELS;
  window.ForgeFX = FX;
})();
