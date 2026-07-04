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

    def test_premium_code_renders_escaped_not_executed(self):
        self._set_sections({"version": 1, "sections": [
            {"type": "code", "variant": "inert",
             "props": {"code": "<script>alert(1)</script>"}},
        ]})
        resp = self.client.get("/mochi")
        body = resp.get_data(as_text=True)
        # The stored HTML must appear ESCAPED (as text), never as a live tag.
        self.assertIn("&lt;script&gt;", body)
        self.assertNotIn("<script>alert(1)</script>", body)

    def test_embed_renders_as_linkout_not_iframe(self):
        self._set_sections({"version": 1, "sections": [
            {"type": "embed", "variant": "full",
             "props": {"kind": "youtube", "url": "https://youtu.be/dQw4w9WgXcQ"}},
        ]})
        resp = self.client.get("/mochi")
        body = resp.get_data(as_text=True)
        # Facade links out to the allowlisted URL — no iframe, no JS, no
        # third-party request happens before the visitor clicks (RULES.md).
        self.assertNotIn("<iframe", body.lower())
        self.assertNotIn("<script", body.lower())
        self.assertIn('href="https://youtu.be/dQw4w9WgXcQ"', body)
        self.assertIn('rel="noopener noreferrer nofollow"', body)
        self.assertIn("youtu.be", body)  # hostname caption
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


if __name__ == "__main__":
    unittest.main()
