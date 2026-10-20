const fs = require('fs');

function lum(h) {
    h = h.replace('#', '');
    const r = parseInt(h.slice(0, 2), 16) / 255;
    const g = parseInt(h.slice(2, 4), 16) / 255;
    const b = parseInt(h.slice(4, 6), 16) / 255;
    const f = c => c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
}

function ratio(a, b) {
    const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
}

const css = fs.readFileSync(process.argv[2], 'utf8');

function block(sel) {
    const re = new RegExp(sel.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\s*\\{(.*?)\\n\\}', 's');
    const m = css.match(re);
    if (!m) return {};
    const matches = m[1].matchAll(/--[\w-]+\s*:\s*(#[0-9a-fA-F]{6})\s*;/g);
    const obj = {};
    for (const match of matches) {
        const fullMatch = match[0];
        const parts = fullMatch.split(':').map(s => s.trim());
        obj[parts[0]] = parts[1];
    }
    return obj;
}

const light = block(':root');
const dark = {...light, ...block(':root\\[data-theme="dark"\\]')};

const TEXT_ON = {
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
};
['keyword', 'string', 'number', 'comment', 'function', 'class', 'builtin', 'decorator', 'operator', 'punct', 'variable'].forEach(t => {
    TEXT_ON['--syn-' + t] = ['--bg-editor'];
});
const UI_ON = {'--border-input': ['--bg-raised', '--bg-surface'], '--focus-ring': ['--bg-app', '--bg-surface', '--bg-editor']};

let fails = 0;
for (const [name, tokens] of [['LIGHT', light], ['DARK', dark]]) {
    for (const [fg, bgs] of [...Object.entries(TEXT_ON), ...Object.entries(UI_ON)]) {
        const need = UI_ON[fg] ? 3.0 : 4.5;
        for (const bg of bgs) {
            if (fg in tokens && bg in tokens) {
                const r = ratio(tokens[fg], tokens[bg]);
                const ok = r >= need;
                fails += ok ? 0 : 1;
                console.log((ok ? 'PASS' : 'FAIL'), name, fg, 'on', bg, r.toFixed(2), '(need ' + need.toFixed(1) + ')');
            }
        }
    }
}
console.log('\nFAILURES:', fails);
process.exit(fails ? 1 : 0);