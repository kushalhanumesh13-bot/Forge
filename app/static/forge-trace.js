/* forge-trace.js — DEV ONLY timeline. Inert unless the page URL contains ?trace */
(function () {
  'use strict';
  if (!/[?&]trace\b/.test(location.search) || window.ForgeTrace) return;

  const now = () => performance.now();
  const _st = window.setTimeout.bind(window);
  const _ct = window.clearTimeout.bind(window);
  const T = { t0: 0, gen: 0, ev: [], busy: false, slow: 0, long: 0, ro: 0, roMs: 0, rep: 0 };

  const describe = (el) => {
    if (!el || !el.tagName) return String(el);
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    if (typeof el.className === 'string' && el.className.trim()) s += '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.');
    return s;
  };
  const where = () => (new Error().stack || '').split('\n').slice(3, 6)
    .map((x) => x.trim().replace(/^at /, '').replace(/https?:\/\/[^/]+\//, '')).join(' <- ');
  const mark = (label) => { T.ev.push({ ms: T.t0 ? Math.round(now() - T.t0) : 0, event: label }); };

  /* who is waiting on a timer, an animation event, or the network after a click? */
  window.setTimeout = function (fn, ms) {
    if (T.busy && ms >= 120) mark('setTimeout(' + ms + 'ms) from ' + where());
    return _st.apply(window, arguments);
  };
  const _ael = EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener = function (type, fn, opt) {
    if (T.busy && (type === 'transitionend' || type === 'animationend' || type === 'transitioncancel')) {
      mark('WAIT for ' + type + ' on ' + describe(this) + ' from ' + where());
    }
    return _ael.call(this, type, fn, opt);
  };
  const _fetch = window.fetch;
  if (_fetch) window.fetch = function (input) {
    const url = typeof input === 'string' ? input : (input && input.url) || '';
    const t = now(), track = T.busy;
    if (track) mark('FETCH start ' + url);
    const p = _fetch.apply(this, arguments);
    if (track) p.then(() => mark('FETCH done ' + url + ' (' + Math.round(now() - t) + 'ms)'), () => mark('FETCH failed ' + url));
    return p;
  };
  if (window.ResizeObserver) {
    const RO = window.ResizeObserver;
    window.ResizeObserver = class extends RO {
      constructor(cb) {
        super(function (entries, obs) {
          const t = now();
          try { return cb.call(this, entries, obs); } finally { if (T.busy) { T.ro++; T.roMs += now() - t; } }
        });
      }
    };
  }

  /* long tasks and long animation frames (the second one names the guilty script/function) */
  try {
    new PerformanceObserver((l) => l.getEntries().forEach((e) => {
      if (T.busy) { T.long++; mark('LONG TASK ' + Math.round(e.duration) + 'ms'); }
    })).observe({ entryTypes: ['longtask'] });
  } catch (e) {}
  try {
    new PerformanceObserver((l) => l.getEntries().forEach((e) => {
      if (!T.busy) return;
      const top = (e.scripts || []).slice().sort((a, b) => b.duration - a.duration).slice(0, 3)
        .map((s) => Math.round(s.duration) + 'ms ' + (s.sourceFunctionName || s.invoker || '?') + ' @ ' + String(s.sourceURL || '').split('/').pop() + ':' + (s.sourceCharPosition == null ? '' : s.sourceCharPosition)).join(' | ');
      mark('LONG FRAME ' + Math.round(e.duration) + 'ms scripts: ' + (top || 'none (style/layout/paint cost, not JavaScript)'));
    })).observe({ type: 'long-animation-frame', buffered: false });
  } catch (e) {}

  /* follow the flows: when they start, when they settle, when the panel is shown/hidden */
  function hook() {
    const all = (window.ForgeFlow && window.ForgeFlow.all) || {};
    Object.keys(all).forEach((name) => {
      const fl = all[name];
      if (fl.__traced) return; fl.__traced = true;
      const to = fl.to.bind(fl);
      fl.to = function (...args) { mark('flow[' + name + '].to(' + args[0] + ')'); return to(...args); };
      const os = fl.onSettle;
      fl.onSettle = function (s) {
        mark('flow[' + name + '] SETTLED -> ' + s);
        if (os) os.call(fl, s);
        mark('flow[' + name + '] onSettle callback finished');
      };
      const watchEl = (el, tag) => {
        if (!el) return;
        new MutationObserver(() => {
          const st = el.style;
          const sig = (st.display || '') + '|' + (st.visibility || '') + '|' + (el.hidden ? 'hidden' : '') + '|' + el.className;
          if (sig !== el.__ftSig) {
            el.__ftSig = sig;
            mark(tag + ' changed: display=' + (st.display || '-') + ' visibility=' + (st.visibility || '-') + (el.hidden ? ' hidden' : '') + ' class="' + String(el.className).slice(0, 70) + '"');
          }
        }).observe(el, { attributes: true, attributeFilter: ['class', 'hidden', 'style'] });
      };
      watchEl(fl.panel, 'panel[' + name + ']');
      watchEl(fl.panel.parentElement, 'parent-of-panel[' + name + ']');
    });
  }

  document.addEventListener('click', (e) => {
    hook();
    const gen = ++T.gen;
    T.t0 = now(); T.ev = []; T.slow = 0; T.long = 0; T.ro = 0; T.roMs = 0; T.busy = true;
    mark('CLICK ' + describe(e.target));
    let lastF = 0;
    const watch = (ts) => {
      if (gen !== T.gen) return;
      if (lastF && ts - lastF > 24) { T.slow++; mark('SLOW FRAME ' + Math.round(ts - lastF) + 'ms'); }
      lastF = ts;
      if (now() - T.t0 < 3200) requestAnimationFrame(watch); else T.busy = false;
    };
    requestAnimationFrame(watch);
    _ct(T.rep); T.rep = _st(report, 3300);
  }, true);

  function report() {
    const ev = T.ev, find = (re) => ev.find((e) => re.test(e.event));
    const toEv = find(/\.to\(/), setEv = find(/SETTLED/), doneEv = find(/onSettle callback finished/);
    const ownTimeouts = ev.filter((e) => /^setTimeout/.test(e.event) && !/forge-(fx|flow|trace)/.test(e.event));
    const waits = ev.filter((e) => /^WAIT for/.test(e.event));
    const fetchBefore = toEv ? ev.filter((e) => /^FETCH start/.test(e.event) && e.ms < toEv.ms) : [];
    const checks = [
      ['B1 click -> flow.to() within 50ms', !!toEv && toEv.ms <= 50, toEv ? toEv.ms + 'ms' : 'flow.to() was never called'],
      ['B2 flight (to -> settled) within 900ms', !!(toEv && setEv) && setEv.ms - toEv.ms <= 900, toEv && setEv ? (setEv.ms - toEv.ms) + 'ms' : 'no SETTLED event'],
      ['B3 onSettle callback under 30ms', !!(setEv && doneEv) && doneEv.ms - setEv.ms <= 30, setEv && doneEv ? (doneEv.ms - setEv.ms) + 'ms' : 'n/a'],
      ['B4 slow frames (>24ms) at most 2', T.slow <= 2, T.slow + ' slow frames'],
      ['B5 no long tasks / long frames', T.long === 0, T.long + ' long entries'],
      ['B6 ResizeObserver work <= 30ms', T.roMs <= 30, T.ro + ' callbacks, ' + Math.round(T.roMs) + 'ms'],
      ['B8a no app setTimeout >= 120ms', ownTimeouts.length === 0, ownTimeouts.map((e) => e.event).join(' ; ') || 'none'],
      ['B8b no wait for transitionend/animationend', waits.length === 0, waits.map((e) => e.event).join(' ; ') || 'none'],
      ['B8c no fetch before the flow starts', fetchBefore.length === 0, fetchBefore.map((e) => e.event).join(' ; ') || 'none']
    ];
    console.group('[ForgeTrace] timeline since the click');
    console.table(ev);
    checks.forEach((c) => console.log((c[1] ? 'PASS ' : 'FAIL ') + c[0] + '  ->  ' + c[2]));
    console.groupEnd();
    return checks.every((c) => c[1]);
  }

  function idleCheck(ms) { // B7: run on an idle page, do not click anything
    ms = ms || 2000;
    const orig = window.requestAnimationFrame; let n = 0, who = '';
    window.requestAnimationFrame = function (cb) { n++; if (!who) who = where(); return orig.call(window, cb); };
    _st(() => {
      window.requestAnimationFrame = orig;
      console.log((n === 0 ? 'PASS' : 'FAIL') + ' B7 idle page made ' + n + ' requestAnimationFrame calls in ' + ms + 'ms' + (who ? ' (first caller: ' + who + ')' : ''));
    }, ms);
  }

  window.ForgeTrace = { mark: mark, report: report, events: () => T.ev.slice(), hook: hook, idleCheck: idleCheck };
  console.info('[ForgeTrace] ON. Click a panel button; a report prints after ~3 seconds. ForgeTrace.idleCheck() checks for background loops.');
})();
