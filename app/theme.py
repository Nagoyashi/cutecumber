"""The theming engine. Validated design tokens, never user CSS/HTML.

Shape v2 (stored in users.theme_json):
    {
      "version": 2,
      "preset": "<one of PRESETS>",
      "overrides": { <subset of COLOR_KEYS + ENUM_KEYS + "decoration", diffs from
                      preset only; "decoration" is a LIST of "<pack>/<slug>"
                      tokens, capped at MAX_DECORATIONS> }
    }
v1 stored "decoration" as a single string; load_theme() migrates it forward.

The same philosophy as link URLs applies: validate_theme() guards the SAVE
path strictly (reject anything off-allowlist), and resolve_theme() guards the
RENDER path tolerantly (silently ignore any invalid token — a bad row must
never break a public page).

Every value that reaches a template is either a validated #rrggbb hex, an
allowlisted enum, or a string CONSTRUCTED HERE from those — user input never
becomes CSS any other way. Generated CSS strings deliberately contain no
quotes, ampersands, or angle brackets so Jinja autoescaping passes them
through untouched (no |safe anywhere, per project rule).

Derived values (muted text, button-label color on accent, shadow tint) are
computed from the palette rather than stored, so they can't be set wrong.
WCAG AA for all presets is enforced by tests/test_theme.py.
"""

import json
import re
from urllib.parse import quote

THEME_VERSION = 2
DEFAULT_PRESET = "strawberry_milk"

HEX_RE = re.compile(r"^#[0-9a-f]{6}$")

COLOR_KEYS = ("bg", "bg2", "surface", "text", "accent")

ENUM_KEYS = {
    "font": ("system", "fredoka", "comfortaa"),
    # "scalloped" is deferred: no clean CSS technique fits the budget yet
    # (DECISIONS.md #22). Revisit at the polish pass.
    "button_shape": ("pill", "rounded", "square"),
    "button_style": ("filled", "outline", "soft_shadow"),
    "background": ("solid", "gradient", "stripes", "dots"),
}

# Decorations are MULTI (DECISIONS.md #21 addendum): "decoration" is a LIST of
# "<pack>/<slug>" tokens, capped at MAX_DECORATIONS, validated against this
# registry at SAVE and at RENDER. "basic/*" are the original accent-tinted
# inline glyphs; the designer packs are full_color static tiles served from
# app/static/packs/<pack>/<slug>.svg — curated, never user-uploaded
# (DECISIONS.md #30 / DESIGN_PACKS.md). The registry IS the boundary; an
# unknown token is dropped at render. Adding/removing tokens here is a
# validation-rule change, not a shape change (no version bump needed for that).
MAX_DECORATIONS = 5

DECORATION_PACKS = {
    "basic":          ("sparkles", "hearts", "stars"),
    "garden_patch":   ("baby_cuke", "sprout", "leaf", "daisy", "ladybug"),
    "cozy_cafe":      ("matcha_cup", "strawberry", "cookie", "cake", "heart"),
    "little_friends": ("froggy", "boo", "bun", "shroom", "twinkle"),
    "sakura_dreams":  ("blossom", "petal", "bow", "cloud", "sparkle"),
}
DECORATION_TOKENS = frozenset(
    f"{pack}/{slug}" for pack, slugs in DECORATION_PACKS.items() for slug in slugs
)

# Picker metadata (display name + emoji per pack.json). Drives the grouped
# checkbox catalog in the theme editor; render never touches it.
DECORATION_CATALOG = [
    {"pack": "basic",          "name": "basics",         "emoji": "✨",
     "slugs": DECORATION_PACKS["basic"]},
    {"pack": "garden_patch",   "name": "garden patch",   "emoji": "🥒",
     "slugs": DECORATION_PACKS["garden_patch"]},
    {"pack": "cozy_cafe",      "name": "cozy café",      "emoji": "🍓",
     "slugs": DECORATION_PACKS["cozy_cafe"]},
    {"pack": "little_friends", "name": "little friends", "emoji": "🐸",
     "slugs": DECORATION_PACKS["little_friends"]},
    {"pack": "sakura_dreams",  "name": "sakura dreams",  "emoji": "🌸",
     "slugs": DECORATION_PACKS["sakura_dreams"]},
]


def clean_decorations(value) -> list:
    """Keep only known tokens, de-duplicated in order, capped at the max.
    Used by both the strict save path and the tolerant render path — neither
    can produce an out-of-registry or over-cap decoration list."""
    if not isinstance(value, list):
        return []
    out = []
    for token in value:
        if token in DECORATION_TOKENS and token not in out:
            out.append(token)
        if len(out) >= MAX_DECORATIONS:
            break
    return out

# Self-hosted display fonts (h1 only; body text is always the system stack).
# Subsetted latin WOFF2 from fontsource via npm — each well under the 30 KB
# per-page font budget. At most ONE font ever loads per page.
FONTS = {
    "fredoka": {
        "family": "Fredoka",
        "file": "fredoka-latin-600-normal.woff2",
        "weight": 600,
    },
    "comfortaa": {
        "family": "Comfortaa",
        "file": "comfortaa-latin-700-normal.woff2",
        "weight": 700,
    },
}

# Every preset is a COMPLETE token set. tests/test_theme.py enforces WCAG AA
# (4.5:1) for: text/bg, text/surface, muted/bg, accent_text/accent.
PRESETS = {
    "strawberry_milk": {
        "bg": "#fff5f7", "bg2": "#ffe2ee", "surface": "#ffffff",
        "text": "#53343f", "accent": "#e58fb1",
        "font": "fredoka", "button_shape": "pill", "button_style": "filled",
        "background": "gradient", "decoration": ["basic/hearts"],
    },
    "matcha_latte": {
        "bg": "#f4f9ef", "bg2": "#e3f0d8", "surface": "#ffffff",
        "text": "#36462f", "accent": "#6f9a5d",
        "font": "comfortaa", "button_shape": "rounded", "button_style": "soft_shadow",
        "background": "gradient", "decoration": [],
    },
    "lavender_haze": {
        "bg": "#f7f3fd", "bg2": "#e8dcfa", "surface": "#ffffff",
        "text": "#45375f", "accent": "#7a59c8",
        "font": "comfortaa", "button_shape": "pill", "button_style": "outline",
        "background": "gradient", "decoration": ["basic/sparkles"],
    },
    "cherry_cola": {
        "bg": "#fdf1ef", "bg2": "#f6d7d4", "surface": "#fffaf8",
        "text": "#5c2730", "accent": "#b23350",
        "font": "fredoka", "button_shape": "rounded", "button_style": "filled",
        "background": "stripes", "decoration": [],
    },
    "seafoam": {
        "bg": "#eefaf6", "bg2": "#d6f1e8", "surface": "#ffffff",
        "text": "#1e453f", "accent": "#1f7d76",
        "font": "system", "button_shape": "pill", "button_style": "soft_shadow",
        "background": "dots", "decoration": [],
    },
    "midnight_snack": {
        "bg": "#232338", "bg2": "#2d2d49", "surface": "#303051",
        "text": "#f1edf9", "accent": "#f3a7c3",
        "font": "fredoka", "button_shape": "pill", "button_style": "filled",
        "background": "gradient", "decoration": ["basic/stars"],
    },
}

_ACCENT_TEXT_DARK = "#221a26"


# ---------------------------------------------------------------- color math

def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def mix(color_a: str, color_b: str, weight_a: float) -> str:
    """Blend two hex colors; weight_a is color_a's share (0..1)."""
    a, b = _hex_to_rgb(color_a), _hex_to_rgb(color_b)
    return _rgb_to_hex(*(round(ca * weight_a + cb * (1 - weight_a)) for ca, cb in zip(a, b)))


def _luminance(value: str) -> float:
    def channel(c: int) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in _hex_to_rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(color_a: str, color_b: str) -> float:
    """WCAG contrast ratio between two hex colors (1..21)."""
    la, lb = _luminance(color_a), _luminance(color_b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# --------------------------------------------------------- stored-shape v1

def default_theme() -> dict:
    return {"version": THEME_VERSION, "preset": DEFAULT_PRESET, "overrides": {}}


def default_theme_json() -> str:
    return json.dumps(default_theme(), separators=(",", ":"))


# version N -> function migrating a shape from N to N+1.
# Adding a migration REQUIRES bumping THEME_VERSION in the same commit.
_V1_DECORATION_MAP = {
    "sparkles": "basic/sparkles", "hearts": "basic/hearts", "stars": "basic/stars",
}


def _migrate_v1_to_v2(data: dict) -> dict:
    """v1 stored `decoration` as one string ("none"/"sparkles"/"hearts"/
    "stars"); v2 stores a LIST of "<pack>/<slug>" tokens. Only a stored
    OVERRIDE needs rewriting — preset defaults are read from code at resolve
    time, so an untouched theme just gets its version stamped."""
    overrides = data.get("overrides")
    if isinstance(overrides, dict) and "decoration" in overrides:
        old = overrides["decoration"]
        mapped = _V1_DECORATION_MAP.get(old) if isinstance(old, str) else None
        overrides["decoration"] = [mapped] if mapped else []
    data["version"] = 2
    return data


MIGRATIONS: dict[int, callable] = {1: _migrate_v1_to_v2}


def load_theme(raw: str | None) -> dict:
    """Parse stored theme_json, migrating old shapes forward; never raises."""
    try:
        data = json.loads(raw) if raw else None
    except ValueError:
        data = None
    if not isinstance(data, dict):
        return default_theme()

    version = data.get("version")
    if not isinstance(version, int) or version < 1 or version > THEME_VERSION:
        return default_theme()

    while version < THEME_VERSION:
        data = MIGRATIONS[version](data)
        version = data["version"]
    return data


# ----------------------------------------------------------------- validate

def validate_theme(data: dict) -> tuple[dict | None, str | None]:
    """SAVE-path validation. Returns (clean_theme, None) or (None, error).

    Strict: unknown keys, malformed hex, and off-allowlist enums are rejected
    outright. Values equal to the preset's own are dropped, so overrides only
    ever store actual differences (and "reset" is just an empty dict).
    """
    if not isinstance(data, dict):
        return None, "that theme didn't make sense to us 🤔"
    preset_name = data.get("preset")
    preset = PRESETS.get(preset_name)
    if preset is None:
        return None, "pick one of our presets first 🌈"
    raw_overrides = data.get("overrides", {})
    if not isinstance(raw_overrides, dict):
        return None, "that theme didn't make sense to us 🤔"

    clean: dict = {}
    for key, value in raw_overrides.items():
        if key in COLOR_KEYS:
            if not isinstance(value, str) or not HEX_RE.match(value.lower()):
                return None, "colors need to be hex codes like #ffd3e0 🎨"
            value = value.lower()
        elif key == "decoration":
            if not isinstance(value, list):
                return None, "that theme didn't make sense to us 🤔"
            if len(value) > MAX_DECORATIONS:
                return None, f"up to {MAX_DECORATIONS} decorations — pick your favorites 🌼"
            if any(tok not in DECORATION_TOKENS for tok in value):
                return None, "that decoration isn't one of ours — pick from the packs 🎀"
            value = clean_decorations(value)  # de-dupe, preserve order
        elif key in ENUM_KEYS:
            if value not in ENUM_KEYS[key]:
                return None, "that option isn't one of ours — pick from the list 🤔"
        else:
            return None, "that theme has settings we don't recognise 🤔"
        if value != preset[key]:
            clean[key] = value

    return {"version": THEME_VERSION, "preset": preset_name, "overrides": clean}, None


# ------------------------------------------------------------------ resolve

_RADII = {"pill": "999px", "rounded": "14px", "square": "4px"}

_SPARKLE = "M12 0L14.6 9.4 24 12 14.6 14.6 12 24 9.4 14.6 0 12 9.4 9.4Z"
_HEART = (
    "M12 21.4C7.2 17.6 4 14.2 4 10.4 4 7.7 6 6 8.2 6c1.5 0 3 .8 3.8 2.1"
    "C12.8 6.8 14.3 6 15.8 6 18 6 20 7.7 20 10.4c0 3.8-3.2 7.2-8 11z"
)
_STAR = "M12 1.8l3 6.2 6.8.9-5 4.8 1.3 6.7-6.1-3.3-6.1 3.3 1.3-6.7-5-4.8 6.8-.9z"
_DECOR_PATHS = {"sparkles": _SPARKLE, "hearts": _HEART, "stars": _STAR}


def _data_uri(svg: str) -> str:
    # safe="" percent-encodes everything non-alphanumeric, so the result is
    # valid inside an UNQUOTED css url() and passes Jinja autoescape untouched.
    return "data:image/svg+xml," + quote(svg, safe="")


def _decoration_layer(token: str, accent: str) -> str:
    """One tiled CSS background layer for a "<pack>/<slug>" decoration token.
    basic/* glyphs are accent-tinted inline data: URIs (zero requests, theme-
    matched); designer-pack tiles are cached static SVGs from /static/packs/."""
    pack, _, slug = token.partition("/")
    if pack == "basic":
        path = _DECOR_PATHS[slug]
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' width='130' height='130'>"
            f"<g fill='{accent}' fill-opacity='.38'>"
            f"<path d='{path}' transform='translate(16 20)'/>"
            f"<path d='{path}' transform='translate(82 84) scale(.55)'/>"
            "</g></svg>"
        )
        return f"url({_data_uri(svg)})"
    return f"url(/static/packs/{pack}/{slug}.svg)"


def _dots_layer(bg2: str) -> str:
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='26' height='26'>"
        f"<circle cx='13' cy='13' r='2.6' fill='{bg2}'/></svg>"
    )
    return f"url({_data_uri(svg)})"


def _page_background(t: dict) -> str:
    """Complete CSS background value: optional decoration layer on top of the
    chosen background type, base color always last. All inputs validated hex
    or fixed literals from this file."""
    layers = []
    for token in t["decoration"]:
        layers.append(_decoration_layer(token, t["accent"]))
    if t["background"] == "gradient":
        layers.append(f"linear-gradient(160deg,{t['bg']} 0%,{t['bg2']} 100%)")
    elif t["background"] == "stripes":
        layers.append(f"repeating-linear-gradient(135deg,{t['bg']} 0 22px,{t['bg2']} 22px 30px)")
    elif t["background"] == "dots":
        layers.append(_dots_layer(t["bg2"]))
    if not layers:
        return t["bg"]
    layers[-1] += " " + t["bg"]
    return ",".join(layers)


def resolve_theme(theme: dict) -> dict:
    """RENDER-path resolution. Tolerant: anything invalid falls back to the
    preset (or the default preset). Returns the full token set plus every
    computed value the public template needs."""
    preset = PRESETS.get(theme.get("preset") if isinstance(theme, dict) else None)
    if preset is None:
        preset = PRESETS[DEFAULT_PRESET]
    tokens = dict(preset)

    overrides = theme.get("overrides") if isinstance(theme, dict) else None
    if isinstance(overrides, dict):
        for key, value in overrides.items():
            if key in COLOR_KEYS and isinstance(value, str) and HEX_RE.match(value.lower()):
                tokens[key] = value.lower()
            elif key == "decoration" and isinstance(value, list):
                tokens["decoration"] = clean_decorations(value)
            elif key in ENUM_KEYS and value in ENUM_KEYS[key]:
                tokens[key] = value

    # computed, never stored
    tokens["muted"] = mix(tokens["text"], tokens["bg"], 0.74)
    tokens["accent_text"] = max(
        ("#ffffff", _ACCENT_TEXT_DARK), key=lambda c: contrast(c, tokens["accent"])
    )
    r, g, b = _hex_to_rgb(tokens["accent"])
    tokens["shadow"] = f"rgba({r},{g},{b},.32)"
    tokens["radius"] = _RADII[tokens["button_shape"]]
    tokens["page_background"] = _page_background(tokens)

    font = FONTS.get(tokens["font"])
    if font:
        tokens["font_file"] = f"/static/fonts/{font['file']}"
        tokens["font_family"] = font["family"]
        tokens["heading_weight"] = font["weight"]
        tokens["heading_stack"] = f"{font['family']},system-ui,sans-serif"
    else:
        tokens["font_file"] = None
        tokens["heading_weight"] = 700
        tokens["heading_stack"] = "system-ui,-apple-system,sans-serif"
    return tokens
