/* DEV ONLY: ForgeThemeAudit() lists visible text with low contrast in the current theme. */
(function () {
  function parse(c) { var m = /rgba?\(([^)]+)\)/.exec(c); if (!m) return null; var p = m[1].split(/[ ,\/]+/).filter(Boolean).map(parseFloat); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; }
  function lum(c) { var f = function (v) { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); }
  function over(t, b) { var a = t.a + b.a * (1 - t.a); if (!a) return { r: 0, g: 0, b: 0, a: 0 }; return { r: (t.r * t.a + b.r * b.a * (1 - t.a)) / a, g: (t.g * t.a + b.g * b.a * (1 - t.a)) / a, b: (t.b * t.a + b.b * b.a * (1 - t.a)) / a, a: a }; }
  function bgOf(el) {
    var layers = [], n = el;
    while (n && n.nodeType === 1) { var c = parse(getComputedStyle(n).backgroundColor); if (c && c.a > 0) { layers.push(c); if (c.a >= 0.99) break; } n = n.parentElement; }
    var acc = parse(getComputedStyle(document.documentElement).backgroundColor) || { r: 255, g: 255, b: 255, a: 1 };
    if (acc.a < 1) acc = { r: 255, g: 255, b: 255, a: 1 };
    for (var i = layers.length - 1; i >= 0; i--) acc = over(layers[i], acc);
    return acc;
  }
  window.ForgeThemeAudit = function () {
    var bad = [], all = document.body.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
      var el = all[i];
      if (!Array.prototype.some.call(el.childNodes, function (n) { return n.nodeType === 3 && n.textContent.trim(); })) continue;
      var cs = getComputedStyle(el), r = el.getBoundingClientRect();
      if (!r.width || !r.height || cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) < 0.5) continue;
      var fg = parse(cs.color), bg = bgOf(el); if (!fg) continue;
      fg = over(fg, bg);
      var L1 = lum(fg), L2 = lum(bg), ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
      var size = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight, 10) >= 700, need = (size >= 24 || (size >= 18.66 && bold)) ? 3 : 4.5;
      if (ratio < need && !el.disabled && el.getAttribute('aria-disabled') !== 'true') bad.push({ el: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\s+/)[0] : ''), text: el.textContent.trim().slice(0, 30), ratio: +ratio.toFixed(2), need: need });
    }
    console.log(bad.length ? 'LOW CONTRAST: ' + bad.length : 'PASS: no low-contrast text found in ' + document.documentElement.dataset.theme + ' theme');
    if (bad.length) console.table(bad);
    return bad;
  };
})();