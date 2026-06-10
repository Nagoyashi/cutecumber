"""Theme engine tests — per testing policy, the theme-token validator and
saved-shape migrations are required test surface, and AA contrast on presets
is a brand promise ("cute stays accessible") enforced here, not by eyeball.

Run from the repo root:  python -m unittest -v
"""

import unittest

from app import theme
from app.theme import (
    COLOR_KEYS,
    PRESETS,
    contrast,
    default_theme,
    load_theme,
    resolve_theme,
    validate_theme,
)


class TestValidateTheme(unittest.TestCase):
    def test_clean_preset_passes(self):
        clean, error = validate_theme({"version": 1, "preset": "seafoam", "overrides": {}})
        self.assertIsNone(error)
        self.assertEqual(clean, {"version": 1, "preset": "seafoam", "overrides": {}})

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
        expected = set(COLOR_KEYS) | set(theme.ENUM_KEYS)
        for name, preset in PRESETS.items():
            self.assertEqual(set(preset), expected, name)


if __name__ == "__main__":
    unittest.main()
