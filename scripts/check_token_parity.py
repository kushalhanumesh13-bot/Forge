import re, sys
css = open(sys.argv[1], encoding='utf8').read()
light = re.search(r':root\s*\{(.*?)\n\}', css, re.S).group(1)
dark = re.search(r':root\[data-theme="dark"\]\s*\{(.*?)\n\}', css, re.S).group(1)
names = lambda s: set(re.findall(r'(--[\w-]+)\s*:', s))
missing = sorted(names(light) - names(dark) - {'--flow-accent'})
print('tokens in light but missing in dark:', missing or 'none')
sys.exit(1 if missing else 0)
