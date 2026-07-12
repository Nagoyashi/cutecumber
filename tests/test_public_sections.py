"""Public builder-render path (STAGING). The section stack must render server
-side, keep the public-page promises (zero JS, no cookie for anonymous
visitors), and fall back to the legacy links page when no live sections exist.

Reuses the create_app()+temp-DB harness from test_security.

Run from the repo root:  python -m unittest -v
"""

import json
import unittest

from app.db import get_db
from app.sections import validate_sections
from tests.test_security import SecurityTestBase


class TestPublicSections(SecurityTestBase):
    def setUp(self):
        super().setUp()
        self.uid, _ = self._create_user("builder@test.test", username="mochi")
        self.client = self.app.test_client()

    def _set_sections(self, page, plan="sprout"):
        clean, err = validate_sections(page, plan=plan)
        self.assertIsNone(err, err)
        with self.app.app_context():
            db = get_db()
            db.execute(
                "UPDATE users SET sections_live_json = ? WHERE id = ?",
                (json.dumps(clean), self.uid),
            )
            db.commit()

    def test_section_stack_renders(self):
        self._set_sections({"version": 1, "sections": [
            {"type": "hero", "variant": "centered",
             "props": {"avatar": "blossom", "name": "mochi", "bio": "tiny happy things"}},
            {"type": "links", "variant": "cards",
             "props": {"links": [{"emoji": "🌷", "title": "shop", "url": "https://example.com/store"}]}},
            {"type": "divider", "variant": "line", "props": {"motif": "sparkle"}},
        ]})
        resp = self.client.get("/mochi")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_data(as_text=True)
        self.assertIn("tiny happy things", body)
        self.assertIn("linkcard", body)          # the cards variant rendered
        self.assertIn("example.com", body)       # hostname filter stripped scheme
        self.assertIn("#m-sparkle", body)         # divider motif via the sprite
        self.assertIn("blossom.svg", body)        # hero avatar from the set

    def test_zero_javascript_and_cookie_free(self):
        self._set_sections({"version": 1, "sections": [
            {"type": "hero", "variant": "banner", "props": {"avatar": "sprout", "name": "z"}},
        ]})
        resp = self.client.get("/mochi")
        self.assertNotIn(b"<script", resp.data.lower())
        self.assertNotIn(b"<iframe", resp.data.lower())
        self.assertNotIn("Set-Cookie", resp.headers)

    def test_premium_code_renders_in_sandboxed_iframe(self):
        self._set_sections({"version": 1, "sections": [
            {"type": "code", "variant": "inert",
             "props": {"code": "<script>alert(1)</script><b>hi</b>"}},
        ]})
        resp = self.client.get("/mochi")
        body = resp.get_data(as_text=True)
        # Rendered inside a sandboxed srcdoc iframe (no allow-scripts), with the
        # user HTML escaped into the srcdoc attribute — never a live top-level tag.
        self.assertIn("<iframe", body.lower())
        self.assertIn("sandbox", body)
        self.assertIn("srcdoc=", body)
        self.assertIn("&lt;script&gt;", body)
        self.assertNotIn("<script>alert(1)</script>", body)
        # No page-level script (code needs no JS); CSP frames only same-origin.
        self.assertNotIn("/static/embed.js", body)
        self.assertIn("frame-src 'self'", resp.headers["Content-Security-Policy"])

    def test_embed_click_to_load_and_scoped_csp(self):
        self._set_sections({"version": 1, "sections": [
            {"type": "embed", "variant": "full",
             "props": {"kind": "youtube", "url": "https://youtu.be/dQw4w9WgXcQ"}},
        ]})
        resp = self.client.get("/mochi")
        body = resp.get_data(as_text=True)
        # NO iframe in the initial HTML — no third-party request until the click.
        self.assertNotIn("<iframe", body.lower())
        # Facade carries the derived nocookie embed src + a link-out fallback.
        self.assertIn('data-embed="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"', body)
        self.assertIn('href="https://youtu.be/dQw4w9WgXcQ"', body)
        self.assertIn('rel="noopener noreferrer nofollow"', body)
        # embed.js is included ONLY here, and the CSP exception is armed.
        self.assertIn("/static/embed.js", body)
        csp = resp.headers["Content-Security-Policy"]
        self.assertIn("script-src 'self'", csp)
        self.assertIn("frame-src https://www.youtube-nocookie.com https://open.spotify.com", csp)
        self.assertNotIn("Set-Cookie", resp.headers)

    def test_non_embed_page_stays_strict(self):
        # A page WITHOUT an embed keeps the strict CSP — no script, no frame-src.
        self._set_sections({"version": 1, "sections": [
            {"type": "hero", "variant": "centered", "props": {"avatar": "sprout", "name": "z"}}]})
        resp = self.client.get("/mochi")
        self.assertNotIn(b"<script", resp.data.lower())
        csp = resp.headers["Content-Security-Policy"]
        self.assertNotIn("script-src", csp)
        self.assertNotIn("frame-src http", csp)

    def test_signup_form_render_as_linkout(self):
        self._set_sections({"version": 1, "sections": [
            {"type": "signup", "variant": "band",
             "props": {"heading": "join my garden", "button": "sign up",
                       "url": "https://buttondown.email/mochi"}},
            {"type": "form", "variant": "card",
             "props": {"heading": "say hi", "button": "get in touch",
                       "url": "https://forms.example.com/mochi"}},
        ]})
        resp = self.client.get("/mochi")
        body = resp.get_data(as_text=True)
        # Link-out buttons to the creator's own destinations — no on-site form,
        # no input, no cookie, no third-party request before the click.
        self.assertNotIn("<form", body.lower())
        self.assertNotIn("<input", body.lower())
        self.assertIn('href="https://buttondown.email/mochi"', body)
        self.assertIn('href="https://forms.example.com/mochi"', body)
        self.assertIn('rel="noopener noreferrer nofollow"', body)
        self.assertNotIn("Set-Cookie", resp.headers)

    def test_falls_back_to_legacy_when_no_live_sections(self):
        resp = self.client.get("/mochi")  # sections_live_json is NULL
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("linkcard", resp.get_data(as_text=True))

    def test_corrupt_sections_column_falls_back(self):
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE users SET sections_live_json = ? WHERE id = ?",
                       ("{not json", self.uid))
            db.commit()
        resp = self.client.get("/mochi")
        self.assertEqual(resp.status_code, 200)  # tolerant resolve → legacy page


class TestMultiPage(SecurityTestBase):
    def setUp(self):
        super().setUp()
        self.uid, _ = self._create_user("site@test.test", username="mochi")
        self.client = self.app.test_client()

    def _add_page(self, slug, title, sections, publish=True):
        from app import pages
        clean, err = validate_sections(sections, plan="sprout")
        self.assertIsNone(err, err)
        with self.app.app_context():
            db = get_db()
            pages.create_page(db, self.uid, slug, title)
            pages.save_page_sections(db, self.uid, slug, json.dumps(clean), publish=publish)

    _ABOUT = {"version": 1, "sections": [
        {"type": "about", "variant": "simple",
         "props": {"heading": "my story", "body": "once upon a cucumber"}}]}

    def test_published_subpage_renders(self):
        self._add_page("about", "About", self._ABOUT)
        resp = self.client.get("/mochi/about")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("once upon a cucumber", resp.get_data(as_text=True))

    def test_unknown_subpage_404s(self):
        self.assertEqual(self.client.get("/mochi/ghost").status_code, 404)

    def test_unpublished_subpage_404s(self):
        self._add_page("draft", "Draft", self._ABOUT, publish=False)
        self.assertEqual(self.client.get("/mochi/draft").status_code, 404)

    def test_slug_case_redirects_to_lowercase(self):
        self._add_page("about", "About", self._ABOUT)
        resp = self.client.get("/mochi/About")
        self.assertEqual(resp.status_code, 301)
        self.assertTrue(resp.headers["Location"].endswith("/mochi/about"))

    def test_site_nav_appears_with_published_subpage(self):
        self._add_page("about", "About", self._ABOUT)
        # home (legacy links page) now carries the nav to home + about
        home = self.client.get("/mochi").get_data(as_text=True)
        self.assertIn('class="site-nav"', home)
        self.assertIn("/mochi/about", home)
        self.assertIn(">home<", home)
        # the subpage marks itself current
        sub = self.client.get("/mochi/about").get_data(as_text=True)
        self.assertIn('aria-current="page"', sub)

    def test_no_nav_without_subpages(self):
        self.assertNotIn('class="site-nav"', self.client.get("/mochi").get_data(as_text=True))

    def test_subpage_is_zero_javascript(self):
        self._add_page("about", "About", self._ABOUT)
        body = self.client.get("/mochi/about").get_data(as_text=True)
        self.assertNotIn("<script", body)


if __name__ == "__main__":
    unittest.main()
