"""Builder editor tests. The access gate is security-relevant: with the flag on
the builder is open to every authenticated creator, but a flag-off request must
get a plain 404 (no hint the surface exists), and the staging plan toggle is
restricted to the internal allowlist. The save/publish loop must round-trip
through validate_sections and only touch the live column on publish.

Reuses the create_app()+temp-DB harness from test_security.
"""

import io
import json
import os

from PIL import Image

from app.db import get_db
from app.security import session_auth_fragment
from tests.test_security import SecurityTestBase


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (24, 18), (200, 120, 150)).save(buf, "PNG")
    buf.seek(0)
    return buf

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

    def test_non_allowlisted_user_still_gets_editor(self):
        # The allowlist is no longer the access gate — any logged-in creator gets
        # the editor when the flag is on.
        self.app.config["BUILDER_ALLOWLIST"] = frozenset({"someone@else.test"})
        resp = self.client.get("/dash/builder")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'id="builder"', resp.data)

    def test_anonymous_redirected_to_login(self):
        anon = self.app.test_client()
        resp = anon.get("/dash/builder")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])

    def test_editor_csp_allows_fetch(self):
        # The editor autosaves/publishes via fetch(); the dash CSP must allow
        # same-origin connect (default-src 'none' would block it). Regression
        # guard — the whole editor is dead without this.
        resp = self.client.get("/dash/builder")
        csp = resp.headers["Content-Security-Policy"]
        self.assertIn("connect-src 'self'", csp)
        self.assertIn("script-src 'self'", csp)
        self.assertNotIn("unsafe-inline", csp)  # inline styles are avoided, not allowed


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


class TestBuilderPresetAndPlan(BuilderTestBase):
    def _form(self, path, **fields):
        fields["_csrf"] = "testcsrf"
        return self.client.post(path, data=fields)

    def test_preset_applies_to_theme(self):
        resp = self._form("/dash/builder/preset", preset="seafoam")
        self.assertTrue(resp.get_json()["ok"])
        pub = self.client.get("/mochi")  # theme drives the page background
        self.assertEqual(pub.status_code, 200)

    def test_premium_preset_rejected_on_free(self):
        resp = self._form("/dash/builder/preset", preset="lavender_haze")
        self.assertFalse(resp.get_json()["ok"])

    def test_plan_toggle_unlocks_premium(self):
        # Flip to sprout via the staging toggle…
        resp = self._form("/dash/builder/plan", plan="sprout")
        self.assertEqual(resp.get_json(), {"ok": True, "plan": "sprout"})
        # …now a premium section saves, and the premium preset is accepted.
        s = self._post("/dash/builder/save", {"version": 1, "sections": [
            {"type": "code", "variant": "inert", "props": {"code": "<b>x</b>"}}]})
        self.assertTrue(s.get_json()["ok"])
        p = self._form("/dash/builder/preset", preset="midnight_snack")
        self.assertTrue(p.get_json()["ok"])

    def test_bad_plan_rejected(self):
        resp = self._form("/dash/builder/plan", plan="galaxy")
        self.assertFalse(resp.get_json()["ok"])

    def test_plan_toggle_restricted_to_internal_allowlist(self):
        # A logged-in creator who ISN'T in the internal allowlist still reaches
        # the editor, but the staging plan toggle is a 404 for them — premium is
        # "coming soon", not self-upgradable.
        self.app.config["BUILDER_ALLOWLIST"] = frozenset({"someone@else.test"})
        self.assertEqual(self.client.get("/dash/builder").status_code, 200)
        resp = self._form("/dash/builder/plan", plan="sprout")
        self.assertEqual(resp.status_code, 404)
        with self.app.app_context():
            plan = get_db().execute(
                "SELECT plan FROM users WHERE id = ?", (self.uid,)).fetchone()["plan"]
        self.assertEqual(plan, "free")  # unchanged


class TestBuilderUpload(BuilderTestBase):
    def test_upload_returns_processed_webp_filename(self):
        resp = self.client.post("/dash/builder/upload",
                                data={"_csrf": "testcsrf", "photo": (_png(), "pic.png")},
                                content_type="multipart/form-data")
        d = resp.get_json()
        self.assertTrue(d["ok"])
        self.assertRegex(d["filename"], r"^\d+-[0-9a-f]{12}\.webp$")  # re-encoded, our pattern

    def test_uploaded_photo_renders_in_public_gallery(self):
        up = self.client.post("/dash/builder/upload",
                              data={"_csrf": "testcsrf", "photo": (_png(), "pic.png")},
                              content_type="multipart/form-data").get_json()
        page = {"version": 1, "sections": [
            {"type": "gallery", "variant": "three",
             "props": {"photos": [{"caption": "hi", "image": up["filename"]}]}}]}
        self._post("/dash/builder/publish", page)
        pub = self.client.get("/mochi").get_data(as_text=True)
        self.assertIn("/a/" + up["filename"], pub)

    def test_non_image_rejected(self):
        resp = self.client.post("/dash/builder/upload",
                                data={"_csrf": "testcsrf", "photo": (io.BytesIO(b"nope"), "x.txt")},
                                content_type="multipart/form-data")
        self.assertFalse(resp.get_json()["ok"])


class TestImageGC(BuilderTestBase):
    def _upload(self):
        return self.client.post("/dash/builder/upload",
                                data={"_csrf": "testcsrf", "photo": (_png(), "p.png")},
                                content_type="multipart/form-data").get_json()["filename"]

    def _path(self, name):
        from app.avatars import avatar_dir
        return os.path.join(avatar_dir(), name)

    def test_gc_removes_orphans_keeps_referenced(self):
        import os as _os
        from app.maintenance import gc_images
        keep = self._upload()
        orphan = self._upload()
        self._post("/dash/builder/publish", {"version": 1, "sections": [
            {"type": "gallery", "variant": "three",
             "props": {"photos": [{"caption": "", "image": keep}]}}]})
        with self.app.app_context():
            self.assertTrue(_os.path.exists(self._path(keep)))
            self.assertTrue(_os.path.exists(self._path(orphan)))
            deleted, kept = gc_images(get_db())
            self.assertEqual((deleted, kept), (1, 1))
            self.assertTrue(_os.path.exists(self._path(keep)))     # referenced → kept
            self.assertFalse(_os.path.exists(self._path(orphan)))  # orphan → gone

    def test_gc_never_touches_foreign_files(self):
        import os as _os
        from app.avatars import avatar_dir
        from app.maintenance import gc_images
        with self.app.app_context():
            stray = _os.path.join(avatar_dir(), "not-ours.txt")
            with open(stray, "w") as fh:
                fh.write("keep me")
            gc_images(get_db())
            self.assertTrue(_os.path.exists(stray))  # off-pattern → never deleted

    def test_account_delete_removes_gallery_images(self):
        import os as _os
        img = self._upload()
        self._post("/dash/builder/publish", {"version": 1, "sections": [
            {"type": "gallery", "variant": "three",
             "props": {"photos": [{"caption": "", "image": img}]}}]})
        with self.app.app_context():
            self.assertTrue(_os.path.exists(self._path(img)))
        self.client.post("/dash/account/delete",
                         data={"_csrf": "testcsrf", "password": "correct-horse-battery"})
        with self.app.app_context():
            self.assertFalse(_os.path.exists(self._path(img)))  # gone with the account


class TestBuilderPages(BuilderTestBase):
    """Multi-page builder: create/rename/delete/reorder subpages, and save/publish
    routing to the active page (not the home page)."""

    def _form(self, path, **fields):
        fields["_csrf"] = "testcsrf"
        return self.client.post(path, data=fields)

    def test_create_then_editor_loads_subpage(self):
        self.assertEqual(
            self._form("/dash/builder/pages", slug="about", title="About").get_json(),
            {"ok": True, "slug": "about"})
        self.assertEqual(self.client.get("/dash/builder?page=about").status_code, 200)
        self.assertEqual(self.client.get("/dash/builder?page=ghost").status_code, 404)

    def test_bad_slug_rejected(self):
        self.assertFalse(self._form("/dash/builder/pages", slug="Bad Slug!", title="X").get_json()["ok"])

    def test_save_and_publish_route_to_subpage_not_home(self):
        from app import pages
        self._form("/dash/builder/pages", slug="about", title="About")
        page = {"version": 1, "sections": [
            {"type": "about", "variant": "simple", "props": {"heading": "hi", "body": "on the subpage"}}]}
        self.client.post("/dash/builder/save",
                         data={"_csrf": "testcsrf", "page": "about", "sections": json.dumps(page)})
        with self.app.app_context():
            db = get_db()
            row = pages.get_page(db, self.uid, "about")
            self.assertIsNotNone(row["sections_draft_json"])
            self.assertIsNone(row["sections_live_json"])       # save != publish
            home = db.execute("SELECT sections_draft_json FROM users WHERE id=?", (self.uid,)).fetchone()
            self.assertIsNone(home["sections_draft_json"])     # home untouched
        self.client.post("/dash/builder/publish",
                         data={"_csrf": "testcsrf", "page": "about", "sections": json.dumps(page)})
        pub = self.client.get("/mochi/about")
        self.assertEqual(pub.status_code, 200)
        self.assertIn("on the subpage", pub.get_data(as_text=True))

    def test_rename_and_delete(self):
        from app import pages
        self._form("/dash/builder/pages", slug="about", title="About")
        self.assertTrue(self._form("/dash/builder/pages/rename", page="about", title="My Story").get_json()["ok"])
        with self.app.app_context():
            self.assertEqual(pages.get_page(get_db(), self.uid, "about")["title"], "My Story")
        self.assertTrue(self._form("/dash/builder/pages/delete", page="about").get_json()["ok"])
        self.assertEqual(self.client.get("/dash/builder?page=about").status_code, 404)

    def test_reorder(self):
        for s in ("one", "two"):
            self._form("/dash/builder/pages", slug=s, title=s.title())
        self.assertTrue(self._form("/dash/builder/pages/reorder", order=json.dumps(["two", "one"])).get_json()["ok"])
        self.assertFalse(self._form("/dash/builder/pages/reorder", order=json.dumps(["two"])).get_json()["ok"])
