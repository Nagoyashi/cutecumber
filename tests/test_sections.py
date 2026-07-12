"""Page-builder section model tests. Same required surface as the theme engine:
the SAVE validator is the security boundary (strict), the RENDER resolver must
be tolerant (a bad row never breaks a public page), and premium types are gated
by plan. Mirrors tests/test_theme.py in spirit.

Run from the repo root:  python -m unittest -v
"""

import unittest

from app import sections
from app.sections import (
    ALL_TYPES,
    PREMIUM_TYPES,
    SECTIONS_VERSION,
    VARIANTS,
    default_sections_from_profile,
    load_sections,
    resolve_sections,
    validate_sections,
    validate_sections_detailed,
)


def _page(*secs):
    return {"version": SECTIONS_VERSION, "sections": list(secs)}


def _hero(**over):
    props = {"avatar": "sprout", "name": "mochi"}
    props.update(over)
    return {"type": "hero", "variant": "centered", "props": props}


_MISSING = object()


def _links(items=_MISSING):
    if items is _MISSING:  # sentinel, so an explicit [] actually tests the empty case
        items = [{"emoji": "🌷", "title": "shop", "url": "https://example.com"}]
    return {"type": "links", "variant": "buttons", "props": {"links": items}}


class TestValidateStructure(unittest.TestCase):
    def test_clean_page_passes(self):
        clean, err = validate_sections(_page(_hero(), _links()))
        self.assertIsNone(err)
        self.assertEqual(clean["version"], SECTIONS_VERSION)
        self.assertEqual(len(clean["sections"]), 2)

    def test_non_dict_rejected(self):
        for bad in (None, [], "x", {"sections": "nope"}, {"sections": {}}):
            clean, err = validate_sections(bad)
            self.assertIsNone(clean, repr(bad))
            self.assertIsNotNone(err)

    def test_detailed_reports_offending_section_index(self):
        # A valid hero at 0, an unknown-type section at 1 → the editor needs `at`
        # to point the user straight at the culprit (#103).
        clean, err, at = validate_sections_detailed(
            _page(_hero(), {"type": "banner_ad", "variant": "x", "props": {}}, _links()))
        self.assertIsNone(clean)
        self.assertIsNotNone(err)
        self.assertEqual(at, 1)

    def test_detailed_whole_page_error_has_no_index(self):
        clean, err, at = validate_sections_detailed({"sections": "nope"})
        self.assertIsNone(clean)
        self.assertIsNone(at)  # not a per-section failure

    def test_detailed_clean_page_has_no_error_index(self):
        clean, err, at = validate_sections_detailed(_page(_hero(), _links()))
        self.assertIsNotNone(clean)
        self.assertIsNone(err)
        self.assertIsNone(at)

    def test_unknown_type_rejected(self):
        clean, err = validate_sections(_page({"type": "banner_ad", "variant": "x", "props": {}}))
        self.assertIsNone(clean)
        self.assertIsNotNone(err)

    def test_unknown_variant_rejected(self):
        clean, err = validate_sections(_page(_hero() | {"variant": "diagonal"}))
        self.assertIsNone(clean)
        self.assertIsNotNone(err)

    def test_over_section_cap_rejected(self):
        clean, err = validate_sections(_page(*[_hero() for _ in range(sections.SECTIONS_MAX + 1)]))
        self.assertIsNone(clean)
        self.assertIsNotNone(err)

    def test_opaque_id_preserved_but_capped(self):
        clean, _ = validate_sections(_page(_hero() | {"id": "s-abc123"}))
        self.assertEqual(clean["sections"][0]["id"], "s-abc123")
        clean, _ = validate_sections(_page(_hero() | {"id": "x" * 200}))
        self.assertNotIn("id", clean["sections"][0])  # oversize id dropped, section kept


class TestPremiumGating(unittest.TestCase):
    def test_premium_type_rejected_on_free(self):
        embed = {"type": "embed", "variant": "full",
                 "props": {"kind": "youtube", "url": "https://youtu.be/abc"}}
        clean, err = validate_sections(_page(embed), plan="free")
        self.assertIsNone(clean)
        self.assertIsNotNone(err)

    def test_premium_type_allowed_on_sprout(self):
        embed = {"type": "embed", "variant": "full",
                 "props": {"kind": "youtube", "url": "https://youtu.be/abc"}}
        clean, err = validate_sections(_page(embed), plan="sprout")
        self.assertIsNone(err)
        self.assertEqual(clean["sections"][0]["type"], "embed")

    def test_all_premium_types_gated(self):
        self.assertEqual(PREMIUM_TYPES, {"embed", "signup", "form", "code"})


class TestHero(unittest.TestCase):
    def test_bad_avatar_rejected(self):
        clean, err = validate_sections(_page(_hero(avatar="not-a-set")))
        self.assertIsNone(clean)
        self.assertIsNotNone(err)

    def test_missing_name_rejected(self):
        clean, err = validate_sections(_page({"type": "hero", "variant": "centered",
                                              "props": {"avatar": "sprout"}}))
        self.assertIsNone(clean)
        self.assertIsNotNone(err)

    def test_optional_fields_kept_when_present(self):
        clean, _ = validate_sections(_page(_hero(pronoun="she/her", bio="hi")))
        self.assertEqual(clean["sections"][0]["props"]["pronoun"], "she/her")


class TestLinks(unittest.TestCase):
    def test_bad_url_rejected(self):
        clean, err = validate_sections(_page(_links([
            {"emoji": "", "title": "x", "url": "javascript:alert(1)"}])))
        self.assertIsNone(clean)
        self.assertIsNotNone(err)

    def test_scheme_added_and_url_normalized(self):
        clean, _ = validate_sections(_page(_links([
            {"emoji": "", "title": "x", "url": "example.com"}])))
        self.assertEqual(clean["sections"][0]["props"]["links"][0]["url"], "https://example.com")

    def test_empty_link_list_rejected(self):
        clean, err = validate_sections(_page(_links([])))
        self.assertIsNone(clean)
        self.assertIsNotNone(err)

    def test_over_link_cap_rejected(self):
        items = [{"emoji": "", "title": f"l{i}", "url": "https://e.com"}
                 for i in range(sections.LINKS_PER_SECTION_MAX + 1)]
        clean, err = validate_sections(_page(_links(items)))
        self.assertIsNone(clean)
        self.assertIsNotNone(err)


class TestEmbedHostAllowlist(unittest.TestCase):
    def test_off_allowlist_host_rejected(self):
        bad = {"type": "embed", "variant": "full",
               "props": {"kind": "youtube", "url": "https://evil.example/abc"}}
        clean, err = validate_sections(_page(bad), plan="sprout")
        self.assertIsNone(clean)
        self.assertIsNotNone(err)

    def test_allowlisted_hosts_pass(self):
        for url in ("https://youtu.be/abc", "https://www.youtube.com/watch?v=abc",
                    "https://open.spotify.com/track/x"):
            page = _page({"type": "embed", "variant": "card",
                          "props": {"kind": "youtube", "url": url}})
            clean, err = validate_sections(page, plan="sprout")
            self.assertIsNone(err, url)


class TestDivider(unittest.TestCase):
    def test_off_allowlist_motif_rejected(self):
        clean, err = validate_sections(_page({"type": "divider", "variant": "line",
                                             "props": {"motif": "skull"}}))
        self.assertIsNone(clean)
        self.assertIsNotNone(err)


class TestGalleryImages(unittest.TestCase):
    def test_valid_image_kept_bad_dropped(self):
        page = _page({"type": "gallery", "variant": "three", "props": {"photos": [
            {"caption": "a", "image": "5-0123456789ab.webp"},   # our pattern → kept
            {"caption": "b", "image": "../etc/passwd"},          # off-pattern → dropped
        ]}})
        clean, err = validate_sections(page)
        self.assertIsNone(err)
        photos = clean["sections"][0]["props"]["photos"]
        self.assertEqual(photos[0].get("image"), "5-0123456789ab.webp")
        self.assertNotIn("image", photos[1])  # caption survives, bad image gone


class TestResolveTolerance(unittest.TestCase):
    def test_corrupt_json_yields_empty(self):
        for raw in (None, "", "{not json", "[]", '"hi"', '{"version": 99}',
                    '{"version": 1, "sections": "nope"}'):
            self.assertEqual(resolve_sections(raw), [], repr(raw))

    def test_bad_sections_dropped_good_kept(self):
        import json
        raw = json.dumps(_page(
            _hero(),
            {"type": "unknown", "variant": "x", "props": {}},
            {"type": "hero", "variant": "diagonal", "props": {"avatar": "sprout", "name": "z"}},
            _links(),
        ))
        out = resolve_sections(raw)
        self.assertEqual([s["type"] for s in out], ["hero", "links"])

    def test_resolve_drops_id(self):
        import json
        raw = json.dumps(_page(_hero() | {"id": "s-keep"}))
        out = resolve_sections(raw)
        self.assertNotIn("id", out[0])

    def test_load_rejects_out_of_range_version(self):
        self.assertIsNone(load_sections('{"version": 0, "sections": []}'))
        self.assertIsNone(load_sections('{"version": 999, "sections": []}'))


class TestDefaultFromProfile(unittest.TestCase):
    def test_synthesises_hero_and_links(self):
        user = {"display_name": "Mochi", "username": "mochi", "pronouns": "she/her",
                "bio": "hi", "avatar_kind": "set", "avatar_value": "blossom"}
        links = [{"emoji": "🌷", "title": "shop", "url": "https://example.com"}]
        page = default_sections_from_profile(user, links)
        self.assertEqual(page["sections"][0]["type"], "hero")
        self.assertEqual(page["sections"][0]["props"]["avatar"], "blossom")
        self.assertEqual(page["sections"][1]["type"], "links")
        # And the synthesised page must itself validate.
        clean, err = validate_sections(page)
        self.assertIsNone(err)

    def test_no_links_yields_hero_only(self):
        user = {"display_name": "", "username": "solo", "pronouns": None,
                "bio": None, "avatar_kind": "emoji", "avatar_value": "🥒"}
        page = default_sections_from_profile(user, [])
        self.assertEqual(len(page["sections"]), 1)
        self.assertEqual(page["sections"][0]["props"]["avatar"], "sprout")  # non-set → default


class TestEmbedSrc(unittest.TestCase):
    def test_youtube_forms(self):
        from app.sections import embed_src
        want = "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"
        for url in ("https://youtu.be/dQw4w9WgXcQ",
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "https://youtube.com/embed/dQw4w9WgXcQ"):
            self.assertEqual(embed_src("youtube", url), want, url)

    def test_spotify_track(self):
        from app.sections import embed_src
        self.assertEqual(
            embed_src("spotify", "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"),
            "https://open.spotify.com/embed/track/4cOdK2wGLETKBW3PvgPWqT")

    def test_unparseable_returns_none(self):
        from app.sections import embed_src
        self.assertIsNone(embed_src("youtube", "https://youtu.be/"))
        self.assertIsNone(embed_src("spotify", "https://open.spotify.com/"))


class TestCatalogInvariants(unittest.TestCase):
    def test_every_type_has_variants_and_a_validator(self):
        for t in ALL_TYPES:
            self.assertIn(t, VARIANTS, t)
            self.assertTrue(VARIANTS[t], t)
            self.assertIn(t, sections._VALIDATORS, t)


if __name__ == "__main__":
    unittest.main()
