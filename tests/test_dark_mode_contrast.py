"""Report readability in light AND dark mode (static checks on app/static/css/app.css and the report views).

Regression: the printable report forced `background:#fff; color:#10231A`, so the cards, tables and chips nested in
it (which use the dark-theme surfaces) showed near-black text on near-black backgrounds (contrast ~1.0). Text now
uses theme tokens only, and every text/surface pair the report uses must reach WCAG AA (4.5:1) in both themes.
The real-browser check of the rendered page is in tests/e2e/browser_e2e.py (computed colours, both themes).
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSS = (ROOT / "app" / "static" / "css" / "app.css").read_text(encoding="utf-8")
SCREEN_CSS = CSS.split("@media print{", 1)[0] + CSS.split("@media print{", 1)[1].split("}}", 1)[1]


def _tokens(block: str) -> dict:
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})", block))


def _block(selector: str) -> str:
    m = re.search(re.escape(selector) + r"\{(.*?)\n\}", CSS, re.S)
    assert m, selector
    return m.group(1)


LIGHT = _tokens(_block(":root"))
DARK = {**LIGHT, **_tokens(_block('[data-theme="dark"]'))}


def _lum(hex_color: str) -> float:
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _contrast(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# (text token, surface token) pairs used by the report, the diagnosis card and the parent view
PAIRS = [("ink", "surface"), ("ink", "surface-2"), ("ink", "bg"), ("ink-2", "surface"), ("ink-2", "surface-2"),
         ("muted", "surface"), ("muted", "surface-2"), ("muted", "bg"), ("muted", "g-100"),
         ("danger-ink", "danger-bg"), ("danger-ink", "surface"), ("amber-ink", "amber-bg"), ("amber-ink", "surface"),
         ("accent-ink", "g-100"), ("accent-ink", "surface"), ("accent-ink", "surface-2"), ("ink-2", "danger-bg")]


def test_every_report_text_pair_reaches_aa_in_light_and_dark():
    failures = []
    for theme, tokens in (("light", LIGHT), ("dark", DARK)):
        for fg, bg in PAIRS:
            ratio = _contrast(tokens[fg], tokens[bg])
            if ratio < 4.5:
                failures.append(f"{theme}: --{fg} on --{bg} = {ratio:.2f}")
    assert failures == [], failures


def test_the_report_follows_the_theme_instead_of_forcing_white_paper():
    report = re.search(r"\n\.report\{([^}]*)\}", SCREEN_CSS).group(1)
    assert "var(--surface)" in report and "var(--ink)" in report
    assert not re.search(r"#[0-9A-Fa-f]{3,6}|black|white", report)
    headings = re.search(r"\.report h1,\.report h2,\.report h3\{([^}]*)\}", SCREEN_CSS).group(1)
    assert headings.strip() == "color:var(--ink)"


def test_no_text_is_dark_green_or_black_without_a_theme_token():
    # Dark greens are only allowed as text on the always-light lime chips/buttons, or with a dark override.
    allowed = {".btn-lime", ".chip.lime", ".brand-word b", ".price b"}
    offenders = []
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", SCREEN_CSS):
        selector = selector.strip()
        if re.search(r"(?<![-\w])color:\s*(var\(--g-(700|800|900)\)|#000\b|#000000|black\b|#10231A|#0B2E20)", body):
            if not any(selector.endswith(a) for a in allowed):
                offenders.append(selector)
    assert offenders == [], offenders


def test_status_text_uses_the_theme_aware_ink_tokens():
    for selector in (".err", ".chip.red", ".chip.amber", ".gap-banner", ".gap-banner.locked", ".verdict.bad",
                     ".chain .node.root", ".risk.high", ".risk.medium", ".risk.low", ".flow-step.done", ".kpi .v", ".banner"):
        body = re.search(r"(?:^|\})" + re.escape(selector) + r"\{([^}]*)\}", SCREEN_CSS, re.M).group(1)
        color = re.search(r"(?<![-\w])color:([^;}]+)", body).group(1)
        assert color in ("var(--danger-ink)", "var(--amber-ink)", "var(--accent-ink)"), (selector, color)


def test_native_controls_follow_the_theme_and_print_is_always_light():
    assert "color-scheme:light" in _block(":root") and "color-scheme:dark" in _block('[data-theme="dark"]')
    printing = CSS.split("@media print{", 1)[1].split("}}", 1)[0]
    assert '[data-theme="dark"]' in printing and "--ink:#10231A" in printing and "--surface:#FFFFFF" in printing


def test_report_views_have_no_hard_coded_colours():
    for name in ("parent.js", "diagnosis.js"):
        src = (ROOT / "app" / "static" / "js" / "views" / name).read_text(encoding="utf-8")
        assert not re.search(r"color:\s*'#|borderTop:\s*'[^']*#|background:\s*'#", src), name


def test_the_new_diagnosis_card_uses_tokens_only():
    rules = re.findall(r"\n(\.(?:root-cta|dx-|child-id)[^{]*)\{([^}]*)\}", SCREEN_CSS)
    assert len(rules) >= 10
    for selector, body in rules:
        assert not re.search(r"#[0-9A-Fa-f]{3,6}\b|black|white", body), selector
