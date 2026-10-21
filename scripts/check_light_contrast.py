import re, sys
def lum(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda v: v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])
def ratio(a, b):
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)
css = open(sys.argv[1], encoding='utf8').read()
t = dict(re.findall(r'(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;', re.search(r':root\s*\{(.*?)\n\}', css, re.S).group(1)))
SURF = ['--bg-app', '--bg-header', '--bg-panel', '--bg-surface', '--bg-raised', '--bg-editor']
pairs = [(f, b, 4.5) for f in ['--text', '--text-2', '--text-muted', '--link', '--success', '--warn', '--error', '--info'] for b in SURF]
pairs += [('--text-on-accent', a, 4.5) for a in ['--accent', '--accent-hover', '--accent-active']]
pairs += [('--text-on-rail', '--bg-rail', 4.5), ('--text-on-rail', '--rail-item-active-bg', 4.5),
          ('--text-on-tooltip', '--bg-tooltip', 4.5), ('--badge-fg', '--badge-bg', 4.5),
          ('--diff-add-fg', '--diff-add-bg', 4.5), ('--diff-del-fg', '--diff-del-bg', 4.5)]
pairs += [('--syn-' + n, '--bg-editor', 4.5) for n in ['keyword', 'string', 'number', 'comment', 'function', 'class', 'builtin', 'decorator', 'operator', 'punct', 'variable']]
pairs += [('--border-input', b, 3.0) for b in ['--bg-raised', '--bg-surface']] + [('--focus-ring', b, 3.0) for b in SURF]
fails = 0
for f, b, need in pairs:
    if f in t and b in t:
        r = ratio(t[f], t[b]); ok = r >= need; fails += 0 if ok else 1
        print('PASS' if ok else 'FAIL', f, 'on', b, '%.2f' % r, '(need %.1f)' % need)
print('FAILURES:', fails)
sys.exit(1 if fails else 0)
