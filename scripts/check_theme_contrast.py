import re, sys

def lum(h):
    h = h.lstrip('#'); r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

def ratio(a, b):
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)

css = open(sys.argv[1], encoding='utf8').read()

def block(sel):
    m = re.search(re.escape(sel) + r'\s*\{(.*?)\n\}', css, re.S)
    return dict(re.findall(r'(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;', m.group(1))) if m else {}

light = block(':root')
dark = {**light, **block(':root[data-theme="dark"]')}

TEXT_ON = {
    '--text': ['--bg-app', '--bg-header', '--bg-panel', '--bg-surface', '--bg-raised', '--bg-editor', '--bg-gutter'],
    '--text-2': ['--bg-app', '--bg-surface', '--bg-raised', '--bg-editor'],
    '--text-muted': ['--bg-app', '--bg-surface', '--bg-raised', '--bg-editor'],
    '--text-on-accent': ['--accent', '--accent-hover', '--accent-active'],
    '--text-on-rail': ['--bg-rail', '--rail-item-active-bg'],
    '--text-on-tooltip': ['--bg-tooltip'],
    '--badge-fg': ['--badge-bg'],
    '--link': ['--bg-surface'],
    '--success': ['--bg-surface'], '--warn': ['--bg-surface'], '--error': ['--bg-surface'], '--info': ['--bg-surface'],
    '--diff-add-fg': ['--diff-add-bg'], '--diff-del-fg': ['--diff-del-bg'],
}
for t in ['keyword', 'string', 'number', 'comment', 'function', 'class', 'builtin', 'decorator', 'operator', 'punct', 'variable']:
    TEXT_ON['--syn-' + t] = ['--bg-editor']
UI_ON = {'--border-input': ['--bg-raised', '--bg-surface'], '--focus-ring': ['--bg-app', '--bg-surface', '--bg-editor']}

fails = 0
for name, tokens in (('LIGHT', light), ('DARK', dark)):
    for fg, bgs in list(TEXT_ON.items()) + list(UI_ON.items()):
        need = 3.0 if fg in UI_ON else 4.5
        for bg in bgs:
            if fg in tokens and bg in tokens:
                r = ratio(tokens[fg], tokens[bg])
                ok = r >= need
                fails += 0 if ok else 1
                print(('PASS' if ok else 'FAIL'), name, fg, 'on', bg, '%.2f' % r, '(need %.1f)' % need)
print('\nFAILURES:', fails)
sys.exit(1 if fails else 0)