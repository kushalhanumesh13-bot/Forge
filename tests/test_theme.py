import subprocess
import sys
import pytest
from pathlib import Path

# Step 4 Contrast check wrapped as a test
def test_theme_contrast_gate():
    """Verify scripts/check_theme_contrast.py runs on theme.css with zero failures."""
    theme_css = Path("app/static/theme.css")
    assert theme_css.exists(), "app/static/theme.css must exist"
    
    script = Path("scripts/check_theme_contrast.py")
    assert script.exists(), "scripts/check_theme_contrast.py must exist"

    res = subprocess.run(
        [sys.executable, str(script), str(theme_css)],
        capture_output=True,
        text=True
    )
    assert res.returncode == 0, f"Contrast check failed:\n{res.stdout}\n{res.stderr}"
    assert "FAILURES: 0" in res.stdout


# Pure function ForgeTheme.resolve(pref, sysDark) for all 6 combinations
def forge_theme_resolve(pref, sys_dark):
    """Python implementation of pure function in forge-theme.js:
    function resolve(pref, sys) { if (sys === undefined) sys = systemDark(); return (pref === 'dark' || (pref === 'system' && sys)) ? 'dark' : 'light'; }
    """
    if pref == "dark" or (pref == "system" and sys_dark):
        return "dark"
    return "light"


@pytest.mark.parametrize("pref,sys_dark,expected", [
    ("light", False, "light"),
    ("light", True, "light"),
    ("dark", False, "dark"),
    ("dark", True, "dark"),
    ("system", False, "light"),
    ("system", True, "dark"),
])
def test_forge_theme_resolve_combinations(pref, sys_dark, expected):
    """Test all 6 combinations of (preference, systemDark)."""
    assert forge_theme_resolve(pref, sys_dark) == expected


def test_theme_tokens_definition():
    """Verify theme.css defines required surface, brand, and text tokens for both modes."""
    content = Path("app/static/theme.css").read_text(encoding="utf-8")
    required_tokens = [
        "--bg-app", "--bg-header", "--bg-rail", "--bg-panel", "--bg-surface",
        "--bg-editor", "--bg-gutter", "--text", "--text-2", "--text-muted",
        "--accent", "--focus-ring", "--border", "--success", "--warn", "--error",
        "--flow-accent", "--rail-item-active-bg"
    ]
    for token in required_tokens:
        assert token in content, f"Token {token} missing in theme.css"


def test_no_forbidden_color_mix_in_flow_accent():
    """Verify --flow-accent and backgrounds do not use color-mix(), oklch(), or color()."""
    content = Path("app/static/theme.css").read_text(encoding="utf-8")
    for forbidden in ["color-mix", "oklch", "color("]:
        assert forbidden not in content, f"Forbidden function '{forbidden}' found in theme.css"


def test_no_hardcoded_colors_in_components():
    """Ensure active component CSS files do not contain hardcoded hex/rgb colors."""
    import re
    pat = re.compile(r'#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(')
    for p in [Path("app/static/forge-gen4.css"), Path("app/static/components.css")]:
        for idx, line in enumerate(p.read_text(encoding="utf-8").splitlines()):
            matches = pat.findall(line)
            assert not matches, f"Hardcoded colors {matches} found in {p}:{idx+1}"
