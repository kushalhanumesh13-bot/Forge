/* forge-ghost.js — DEV ONLY. Active only when the URL contains ?ghost */
(function () {
  'use strict';
  if (!/[?&]ghost\b/.test(location.search) || window.ForgeGhost) return;
  var FF = window.ForgeFlow;
  if (!FF) { console.error('[ghost] load forge-flow.js first'); return; }
  var LOG = [], T0 = performance.now(), warned = {};
  var layoutish = /^(transform|translate|scale|rotate|top|left|right|bottom|inset|width|height|margin)/;
  function add(kind, msg) { LOG.push({ ms: Math.round(performance.now() - T0), kind: kind, msg: msg }); if (kind === 'WARN') console.warn('[ghost] ' + msg); }
  function once(key, bad, msg) { if (bad) { if (!warned[key]) { warned[key] = 1; add('WARN', msg); } } else { warned[key] = 0; } }
  function stack() { return (new Error().stack || '').split('\n').slice(3, 6).map(function (s) { return s.trim().replace(/^at /, '').replace(/https?:\/\/[^/]+\//, ''); }).join(' <- '); }
  function rs(r) { return Math.round(r.left) + ',' + Math.round(r.top) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height); }
  function offscreen(r) { return r.top < -2 || r.left < -2 || r.bottom > innerHeight + 2 || r.right > innerWidth + 2; }
  function shared() {
    var seen = new Map();
    Object.keys(FF.all).forEach(function (n) {
      var p = FF.all[n].panel;
      if (seen.has(p)) once('shared:' + n, true, 'flows "' + seen.get(p) + '" and "' + n + '" use the SAME panel element: two engines fight over it (phantom animations). Use ONE flow per panel.');
      else seen.set(p, n);
    });
  }
  function instrument(fl) {
    if (fl.__ghost) return; fl.__ghost = true;
    var name = fl.name, to = fl.to.bind(fl), begin = fl.begin.bind(fl), settle = fl.settle.bind(fl);
    fl.to = function (t, tr) {
      add('CALL', name + '.to(' + t + ') from ' + stack());
      if (fl.trigger && !document.contains(fl.trigger)) add('WARN', name + ': its trigger element is not in the page');
      return to(t, tr);
    };
    fl.begin = function () {
      var r = begin(), b = fl.box;
      add('INFO', name + ' begin: panel ' + rs(b) + ' | trigger ' + rs(fl.trigger.getBoundingClientRect()) + ' | viewport ' + innerWidth + 'x' + innerHeight);
      if (offscreen(b)) add('WARN', name + ': panel was measured partly OFF-SCREEN at the start. An old CSS transform/transition is still moving it. This is the "flies under the screen, then snaps" bug.');
      var moving = document.getAnimations().filter(function (a) {
        var el = a.effect && a.effect.target;
        return el && el.contains && el.contains(fl.panel) && (a.animationName || layoutish.test(a.transitionProperty || ''));
      });
      if (moving.length) add('WARN', name + ': ' + moving.length + ' old CSS animation/transition running on the panel or its parent: ' + moving.map(function (a) { return a.animationName || a.transitionProperty; }).join(', '));
      return r;
    };
    fl.settle = function () {
      var wasOpen = fl.p.target === 1, planned = fl.box;
      var out = settle();
      if (wasOpen) requestAnimationFrame(function () {
        var n2 = fl.panel.getBoundingClientRect();
        var d = Math.max(Math.abs(n2.left - planned.left), Math.abs(n2.top - planned.top), Math.abs(n2.width - planned.width), Math.abs(n2.height - planned.height));
        add(d > 1.5 ? 'WARN' : 'INFO', name + ' settled: planned ' + rs(planned) + ' vs real ' + rs(n2) + ' (diff ' + d.toFixed(1) + 'px)' + (d > 1.5 ? ' -> the flying shape ended somewhere else than the real panel = the SNAP at the end' : ''));
      });
      return out;
    };
  }
  var orig = FF.attach;
  FF.attach = function (o) { var fl = orig.call(FF, o); instrument(fl); shared(); return fl; };
  Object.keys(FF.all).forEach(function (n) { instrument(FF.all[n]); }); shared();
  document.addEventListener('click', function (e) {
    var el = e.target.closest ? e.target.closest('button,[role=button],a,li,summary') : null;
    add('CLICK', el ? el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\s+/)[0] : '') : 'page');
  }, true);
  setInterval(function () {
    Object.keys(FF.all).forEach(function (n) {
      var fl = FF.all[n];
      once('blob:' + n, !!(fl.svg && fl.svg.style.display !== 'none' && !fl.live), n + ': STALE BLOB. The flying shape is visible but no animation is running (this is the phantom panel).');
      once('act:' + n, fl.panel.classList.contains('ff-active') && !fl.live, n + ': STALE ff-active class on the panel while no animation is running.');
      once('clip:' + n, !!fl.panel.style.clipPath && !fl.live, n + ': STALE clip-path on the panel while no animation is running.');
    });
  }, 400);
  window.ForgeGhost = {
    report: function () { shared(); console.table(LOG); var w = LOG.filter(function (e) { return e.kind === 'WARN'; }).length; console.log(w ? w + ' WARNING(S): read the WARN rows' : 'NO WARNINGS'); return w; },
    check: function () {
      var rows = Object.keys(FF.all).map(function (n) {
        var fl = FF.all[n], t = fl.trigger;
        return { flow: n, target: fl.p.target, value: +fl.p.value.toFixed(3), live: fl.live, blob: fl.svg ? fl.svg.style.display : '-', ffActive: fl.panel.classList.contains('ff-active'), clip: fl.panel.style.clipPath ? 'SET' : '-', ariaExpanded: t ? t.getAttribute('aria-expanded') : '-' };
      });
      console.table(rows); return rows;
    },
    getLog: function () { return LOG; },
    clear: function () { LOG.length = 0; }
  };
  console.info('[ghost] ON. Use the app, then run ForgeGhost.report()');
})();
