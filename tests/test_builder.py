"""Builder editor tests (STAGING). The access gate is security-relevant — a
non-allowlisted user must get a plain 404, never a hint the surface exists —
and the save/publish loop must round-trip through validate_sections and only
touch the live column on publish.

Reuses the create_app()+temp-DB harness from test_security.
"""

import json

from app.db import get_db
from app.security import session_auth_fragment
from tests.test_security import SecurityTestBase

ALLOWED = "owner@test.test"


class BuilderTestBase(SecurityTestBase):
    def setUp(self):
        super().setUp()
        self.uid, self.pw_hash = self._create_user(ALLOWED, username="mochi")
        self.app.config["BUILDER_ENABLED"] = True
        self.app.config["BUILDER_ALLOWLIST"] = frozenset({ALLOWED})
        self.client = self.app.test_client()
        self._login(self.uid, self.pw_hash)

    def _login(self, uid, pw_hash):
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
            sess["auth"] = session_auth_fragment(pw_hash)
            sess["_csrf"] = "testcsrf"

    def _post(self, path, sections):
        return self.client.post(path, data={"_csrf": "testcsrf", "sections": json.dumps(sections)})


class TestBuilderGate(BuilderTestBase):
    def test_allowlisted_user_gets_editor(self):
        resp = self.client.get("/dash/builder")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'id="builder"', resp.data)

    def test_flag_off_is_404(self):
        self.app.config["BUILDER_ENABLED"] = False
        self.assertEqual(self.client.get("/dash/builder").status_code, 404)

    def test_non_allowlisted_is_404_not_a_hint(self):
        self.app.config["BUILDER_ALLOWLIST"] = frozenset({"someone@else.test"})
        resp = self.client.get("/dash/builder")
        self.assertEqual(resp.status_code, 404)

    def test_anonymous_redirected_to_login(self):
        anon = self.app.test_client()
        resp = anon.get("/dash/builder")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])


class TestBuilderSavePublish(BuilderTestBase):
    HERO = {"version": 1, "sections": [
        {"type": "hero", "variant": "centered", "props": {"avatar": "sprout", "name": "mochi"}}]}

    def test_save_persists_draft_but_not_live(self):
        resp = self._post("/dash/builder/save", self.HERO)
        self.assertEqual(resp.get_json(), {"ok": True})
        with self.app.app_context():
            row = get_db().execute(
                "SELECT sections_draft_json, sections_live_json FROM users WHERE id = ?",
                (self.uid,)).fetchone()
        self.assertIsNotNone(row["sections_draft_json"])
        self.assertIsNone(row["sections_live_json"])  # save must NOT publish

    def test_publish_sets_live_and_public_renders(self):
        resp = self._post("/dash/builder/publish", self.HERO)
        self.assertTrue(resp.get_json()["ok"])
        pub = self.client.get("/mochi")
        self.assertEqual(pub.status_code, 200)
        self.assertIn("hero-centered", pub.get_data(as_text=True))

    def test_invalid_sections_rejected_inline(self):
        resp = self._post("/dash/builder/save",
                          {"version": 1, "sections": [{"type": "nope", "variant": "x", "props": {}}]})
        body = resp.get_json()
        self.assertFalse(body["ok"])
        self.assertIn("error", body)

    def test_premium_section_rejected_on_free_plan(self):
        # The seeded user is on the default 'free' plan.
        resp = self._post("/dash/builder/save", {"version": 1, "sections": [
            {"type": "code", "variant": "inert", "props": {"code": "<b>x</b>"}}]})
        self.assertFalse(resp.get_json()["ok"])
