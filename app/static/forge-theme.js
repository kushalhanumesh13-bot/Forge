/* forge-theme.js — preference: 'light' | 'dark' | 'system'. Resolved theme is always 'light' or 'dark'. */
(function () {
  'use strict';
  if (window.ForgeTheme) return;
  var KEY = 'forge-theme', root = document.documentElement;
  var mq = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
  var listeners = [], timer = 0;
  var valid = function (p) { return p === 'light' || p === 'dark' || p === 'system'; };
  var reduced = function () { return !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches); };
  function getPref() { try { var s = localStorage.getItem(KEY); if (valid(s)) return s; } catch (e) {} return 'system'; }
  function systemDark() { try { return window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)').matches : false; } catch (e) { return false; } }
  function resolve(pref, sys) { if (sys === undefined) sys = systemDark(); return (pref === 'dark' || (pref === 'system' && sys)) ? 'dark' : 'light'; }
  function apply(pref, animate) {
    var resolved = resolve(pref), prev = root.getAttribute('data-theme');
    if (animate && prev !== resolved && !reduced()) {
      root.classList.add('theme-switching'); clearTimeout(timer);
      timer = setTimeout(function () { root.classList.remove('theme-switching'); }, 260);
    }
    root.setAttribute('data-theme', resolved);
    root.setAttribute('data-theme-pref', pref);
    root.style.colorScheme = resolved;
    var m = document.querySelector('meta[name="theme-color"]');
    if (m) { var c = getComputedStyle(root).getPropertyValue('--bg-app').trim(); if (c) m.setAttribute('content', c); }
    var detail = { preference: pref, resolved: resolved, changed: prev !== resolved };
    document.dispatchEvent(new CustomEvent('forge:themechange', { detail: detail }));
    listeners.slice().forEach(function (fn) { try { fn(detail); } catch (e) {} });
    return detail;
  }
  function setPref(pref) {
    if (!valid(pref)) return;
    try { localStorage.setItem(KEY, pref); } catch (e) {}
    apply(pref, true);
    /* If Forge persists settings on the server/in its own store, ALSO save 'pref' there here (Step 5.3). */
  }
  function onSystemChange() { if (getPref() === 'system') apply('system', true); }
  if (mq) {
    if (mq.addEventListener) mq.addEventListener('change', onSystemChange);
    else if (mq.addListener) mq.addListener(onSystemChange);
  }
  window.addEventListener('storage', function (e) { if (e.key === KEY) apply(getPref(), true); }); // other tabs
  root.style.removeProperty('background-color'); // the pre-paint fallback is no longer needed
  apply(getPref(), false);
  window.ForgeTheme = {
    get: getPref, set: setPref, resolved: function () { return root.getAttribute('data-theme'); },
    systemDark: systemDark, onChange: function (fn) { listeners.push(fn); }, resolve: resolve
  };
})();