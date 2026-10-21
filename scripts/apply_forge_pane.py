with open('app/static/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

replacements = [
    ('sideFlow?.to(1, trigger, tgRect);', 'if (window.ForgeFlow && window.ForgeFlow.restore) window.ForgeFlow.restore(sidebar);\n    ForgePane.set(sideFlow, true, trigger);'),
    ('sideFlow?.to(0);', 'if (!ForgePane.set(sideFlow, false)) {\n      sidebar.classList.remove("is-open");\n      sidebar.classList.add("is-collapsed");\n      if (window.ForgeFlow && window.ForgeFlow.restore) window.ForgeFlow.restore(sidebar);\n    }'),
    ('settingsFlow?.to(1, btn);', 'ForgePane.set(settingsFlow, true, btn);'),
    ('settingsFlow?.to(0);', 'ForgePane.set(settingsFlow, false);'),
    ('keysFlow?.to(1, btn);', 'ForgePane.set(keysFlow, true, btn);'),
    ('keysFlow?.to(0);', 'ForgePane.set(keysFlow, false);'),
    ('paletteFlow?.to(0);', 'ForgePane.set(paletteFlow, false);'),
    ('paletteFlow?.to(1, trigger);', 'ForgePane.set(paletteFlow, true, trigger);'),
    ('dockFlow?.to(1, trigger);', 'ForgePane.set(dockFlow, true, trigger);'),
    ('dockFlow?.to(0);', 'ForgePane.set(dockFlow, false);')
]

for old, new in replacements:
    assert old in c, f'target not found: {old}'
    c = c.replace(old, new, 1)

with open('app/static/app.js', 'w', encoding='utf-8', newline='') as f:
    f.write(c)

print('SUCCESS')
