"""Theme engine tests — per testing policy, the theme-token validator and
saved-shape migrations are required test surface, and AA contrast on presets
is a brand promise ("cute stays accessible") enforced here, not by eyeball.

Run from the repo root:  python -m unittest -v
"""

import os
import re
import unittest

from app import theme
from app.theme import (
    COLOR_KEYS,
    DECORATION_TOKENS,
    MAX_DECORATIONS,
    PRESETS,
    contrast,
    default_theme,
    load_theme,
    resolve_theme,
    validate_theme,
)

PACKS_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "static", "packs")


class TestValidateTheme(unittest.TestCase):
    def test_clean_preset_passes(self):
        clean, error = validate_theme({"version": 1, "preset": "seafoam", "overrides": {}})
        self.assertIsNone(error)
        self.assertEqual(
            clean, {"version": theme.THEME_VERSION, "preset": "seafoam", "overrides": {}}
        )

    def test_real_override_kept(self):
        clean, error = validate_theme(
            {"version": 1, "preset": "seafoam", "overrides": {"accent": "#112233"}}
        )
        self.assertIsNone(error)
        self.assertEqual(clean["overrides"], {"accent": "#112233"})

    def test_uppercase_hex_normalized(self):
        clean, _ = validate_theme(
            {"version": 1, "preset": "seafoam", "overrides": {"accent": "#AABBCC"}}
        )
        self.assertEqual(clean["overrides"]["accent"], "#aabbcc")

    def test_values_equal_to_preset_are_dropped(self):
        clean, _ = validate_theme(
            {"version": 1, "preset": "seafoam",
             "overrides": {"bg": PRESETS["seafoam"]["bg"], "font": PRESETS["seafoam"]["font"]}}
        )
        self.assertEqual(clean["overrides"], {})

    def test_bad_hex_rejected(self):
        for bad in ("#abc", "red", "#gggggg", "112233", "#11223344", ""):
            clean, error = validate_theme(
                {"version": 1, "preset": "seafoam", "overrides": {"bg": bad}}
            )
            self.assertIsNone(clean, f"{bad!r} accepted")
            self.assertIsNotNone(error)

    def test_bad_enum_rejected(self):
        clean, error = validate_theme(
            {"version": 1, "preset": "seafoam", "overrides": {"button_shape": "blob"}}
        )
        self.assertIsNone(clean)
        self.assertIsNotNone(error)

    def test_unknown_key_rejected(self):
        clean, error = validate_theme(
            {"version": 1, "preset": "seafoam", "overrides": {"custom_css": "body{}"}}
        )
        self.assertIsNone(clean)
        self.assertIsNotNone(error)

    def test_unknown_preset_rejected(self):
        clean, error = validate_theme({"version": 1, "preset": "hotdog_water", "overrides": {}})
        self.assertIsNone(clean)
        self.assertIsNotNone(error)

    def test_non_dict_inputs_rejected(self):
        for bad in (None, [], "theme", {"preset": "seafoam", "overrides": []}):
            clean, error = validate_theme(bad)
            self.assertIsNone(clean)
            self.assertIsNotNone(error)


class TestResolveTheme(unittest.TestCase):
    def test_override_applied(self):
        t = resolve_theme({"version": 1, "preset": "seafoam", "overrides": {"accent": "#112233"}})
        self.assertEqual(t["accent"], "#112233")

    def test_invalid_override_ignored_at_render(self):
        t = resolve_theme(
            {"version": 1, "preset": "seafoam",
             "overrides": {"accent": "javascript:alert(1)", "button_shape": "blob"}}
        )
        self.assertEqual(t["accent"], PRESETS["seafoam"]["accent"])
        self.assertEqual(t["button_shape"], PRESETS["seafoam"]["button_shape"])

    def test_garbage_theme_falls_back_to_default(self):
        t = resolve_theme({"preset": "nope"})
        self.assertEqual(t["bg"], PRESETS[theme.DEFAULT_PRESET]["bg"])

    def test_computed_values_present(self):
        t = resolve_theme(default_theme())
        for key in ("muted", "accent_text", "shadow", "radius", "page_background", "heading_stack"):
            self.assertIn(key, t)

    def test_generated_css_is_autoescape_transparent(self):
        # No quotes/ampersands/angle brackets may appear in generated CSS
        # values — that's what lets us avoid |safe entirely.
        for name in PRESETS:
            t = resolve_theme({"version": 1, "preset": name, "overrides": {}})
            for value in (t["page_background"], t["shadow"], t["heading_stack"]):
                for ch in "<>&\"'":
                    self.assertNotIn(ch, value, f"{name}: {ch!r} in {value[:60]}…")


class TestLoadThemeAndMigrations(unittest.TestCase):
    def test_corrupt_json_falls_back(self):
        for raw in (None, "", "{not json", "[]", '"hi"', '{"version": "one"}', '{"version": 99}'):
            self.assertEqual(load_theme(raw), default_theme(), raw)

    def test_migration_chain_runs(self):
        original_version, original_migrations = theme.THEME_VERSION, dict(theme.MIGRATIONS)
        try:
            theme.THEME_VERSION = 2
            theme.MIGRATIONS[1] = lambda d: {**d, "version": 2, "migrated": True}
            out = load_theme('{"version": 1, "preset": "seafoam", "overrides": {}}')
            self.assertEqual(out["version"], 2)
            self.assertTrue(out["migrated"])
        finally:
            theme.THEME_VERSION = original_version
            theme.MIGRATIONS.clear()
            theme.MIGRATIONS.update(original_migrations)


class TestPresetAccessibility(unittest.TestCase):
    """'Cute stays accessible: every preset theme passes WCAG AA contrast,
    no exceptions.' This test IS that rule."""

    AA = 4.5

    def test_every_preset_passes_aa(self):
        for name in PRESETS:
            t = resolve_theme({"version": 1, "preset": name, "overrides": {}})
            with self.subTest(preset=name):
                self.assertGreaterEqual(contrast(t["text"], t["bg"]), self.AA)
                self.assertGreaterEqual(contrast(t["text"], t["surface"]), self.AA)
                self.assertGreaterEqual(contrast(t["muted"], t["bg"]), self.AA)
                self.assertGreaterEqual(contrast(t["accent_text"], t["accent"]), self.AA)

    def test_every_preset_is_a_complete_token_set(self):
        expected = set(COLOR_KEYS) | set(theme.ENUM_KEYS) | {"decoration"}
        for name, preset in PRESETS.items():
            self.assertEqual(set(preset), expected, name)

    def test_every_preset_decoration_is_a_valid_capped_list(self):
        for name, preset in PRESETS.items():
            deco = preset["decoration"]
            self.assertIsInstance(deco, list, name)
            self.assertLessEqual(len(deco), MAX_DECORATIONS, name)
            for token in deco:
                self.assertIn(token, DECORATION_TOKENS, f"{name}: {token}")


class TestDecorationValidation(unittest.TestCase):
    """Decoration is a multi list now: validated against the registry, capped
    at MAX_DECORATIONS, de-duplicated — at save (strict) and render (tolerant)."""

    def test_valid_list_kept(self):
        clean, error = validate_theme({"version": 2, "preset": "seafoam",
            "overrides": {"decoration": ["basic/hearts", "garden_patch/daisy"]}})
        self.assertIsNone(error)
        self.assertEqual(clean["overrides"]["decoration"],
                         ["basic/hearts", "garden_patch/daisy"])

    def test_unknown_token_rejected(self):
        clean, error = validate_theme({"version": 2, "preset": "seafoam",
            "overrides": {"decoration": ["basic/hearts", "evil/script"]}})
        self.assertIsNone(clean)
        self.assertIsNotNone(error)

    def test_over_cap_rejected(self):
        toks = ["basic/hearts", "basic/stars", "basic/sparkles",
                "garden_patch/daisy", "garden_patch/leaf", "garden_patch/sprout"]
        clean, error = validate_theme({"version": 2, "preset": "seafoam",
            "overrides": {"decoration": toks}})
        self.assertIsNone(clean)
        self.assertIsNotNone(error)

    def test_non_list_rejected(self):
        clean, error = validate_theme({"version": 2, "preset": "seafoam",
            "overrides": {"decoration": "basic/hearts"}})
        self.assertIsNone(clean)
        self.assertIsNotNone(error)

    def test_duplicates_collapsed(self):
        clean, _ = validate_theme({"version": 2, "preset": "seafoam",
            "overrides": {"decoration": ["basic/hearts", "basic/hearts"]}})
        self.assertEqual(clean["overrides"]["decoration"], ["basic/hearts"])

    def test_explicit_empty_persists_against_decorated_preset(self):
        # strawberry_milk defaults to ["basic/hearts"]; an explicit [] is a real
        # choice ("no decorations") and must survive, not collapse to default.
        clean, _ = validate_theme({"version": 2, "preset": "strawberry_milk",
            "overrides": {"decoration": []}})
        self.assertEqual(clean["overrides"].get("decoration"), [])

    def test_decoration_equal_to_preset_dropped(self):
        clean, _ = validate_theme({"version": 2, "preset": "strawberry_milk",
            "overrides": {"decoration": ["basic/hearts"]}})
        self.assertNotIn("decoration", clean["overrides"])

    def test_render_drops_unknown_and_caps(self):
        toks = ["garden_patch/daisy", "evil/x", "basic/hearts", "basic/stars",
                "basic/sparkles", "garden_patch/leaf", "garden_patch/sprout"]
        t = resolve_theme({"version": 2, "preset": "seafoam",
            "overrides": {"decoration": toks}})
        self.assertNotIn("evil/x", t["decoration"])
        self.assertLessEqual(len(t["decoration"]), MAX_DECORATIONS)

    def test_render_non_list_falls_back_to_preset(self):
        t = resolve_theme({"version": 2, "preset": "strawberry_milk",
            "overrides": {"decoration": "garbage"}})
        self.assertEqual(t["decoration"], PRESETS["strawberry_milk"]["decoration"])


class TestThemeMigrationV1toV2(unittest.TestCase):
    """v1 (single string) -> v2 (list of tokens). Real migration, not the
    generic mechanism test above."""

    def test_string_decoration_becomes_basic_token_list(self):
        out = load_theme('{"version":1,"preset":"seafoam","overrides":{"decoration":"hearts"}}')
        self.assertEqual(out["version"], 2)
        self.assertEqual(out["overrides"]["decoration"], ["basic/hearts"])

    def test_none_decoration_becomes_empty_list(self):
        out = load_theme('{"version":1,"preset":"strawberry_milk","overrides":{"decoration":"none"}}')
        self.assertEqual(out["overrides"]["decoration"], [])

    def test_untouched_v1_theme_just_version_bumps(self):
        out = load_theme('{"version":1,"preset":"seafoam","overrides":{}}')
        self.assertEqual(out["version"], 2)
        self.assertEqual(out["overrides"], {})

    def test_migrated_theme_resolves_cleanly(self):
        out = load_theme('{"version":1,"preset":"lavender_haze","overrides":{"decoration":"sparkles"}}')
        self.assertEqual(resolve_theme(out)["decoration"], ["basic/sparkles"])


class TestDecorationPackAssets(unittest.TestCase):
    """The DECORATION_TOKENS registry IS the boundary; it must match the shipped
    tiles exactly, and the tiles must obey the DESIGN_PACKS safety rules."""

    def test_every_token_has_a_static_tile(self):
        for token in DECORATION_TOKENS:
            pack, slug = token.split("/")
            self.assertTrue(os.path.isfile(os.path.join(PACKS_DIR, pack, slug + ".svg")),
                            f"missing tile for {token}")

    def test_no_stray_tiles_outside_the_registry(self):
        on_disk = set()
        for pack in os.listdir(PACKS_DIR):
            pdir = os.path.join(PACKS_DIR, pack)
            if os.path.isdir(pdir):
                on_disk |= {f"{pack}/{f[:-4]}" for f in os.listdir(pdir) if f.endswith(".svg")}
        self.assertEqual(on_disk, set(DECORATION_TOKENS))

    def test_tiles_are_small_and_inert(self):
        unsafe = re.compile(r"(?i)<script|<foreignobject|<image|xlink:href|data:|\son\w+=")
        for token in DECORATION_TOKENS:
            pack, slug = token.split("/")
            with open(os.path.join(PACKS_DIR, pack, slug + ".svg"), encoding="utf-8") as fh:
                svg = fh.read()
            self.assertLessEqual(len(svg.encode("utf-8")), 8192, f"{token} over 8 KB")
            self.assertIsNone(unsafe.search(svg), f"{token} carries an unsafe construct")


INDEX_HTML = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "index.html")


class TestLandingChromeContrast(unittest.TestCase):
    """Brand chrome lives outside the preset engine, so the AA tests above
    never covered it — and the landing CTA shipped at 2.36:1 (issue #36). The
    accent pills carry --accent-ink (not white) on both --accent and its hover
    --accent-deep; guard those token pairs so the regression can't return."""

    AA = 4.5

    def _root_tokens(self):
        with open(INDEX_HTML, encoding="utf-8") as fh:
            css = fh.read()
        return {
            name: re.search(rf"--{name}:\s*(#[0-9a-fA-F]{{3,6}})", css).group(1)
            for name in ("accent", "accent-deep", "accent-ink")
        }

    def test_accent_pill_ink_meets_aa_on_accent_and_hover(self):
        t = self._root_tokens()
        self.assertGreaterEqual(
            contrast(t["accent-ink"], t["accent"]), self.AA,
            f"accent-ink {t['accent-ink']} on accent {t['accent']} fails AA",
        )
        self.assertGreaterEqual(
            contrast(t["accent-ink"], t["accent-deep"]), self.AA,
            f"accent-ink {t['accent-ink']} on hover {t['accent-deep']} fails AA",
        )


if __name__ == "__main__":
    unittest.main()
