"""Multi-page (Phase B) model tests: slug/title validation, page CRUD strictly
user-scoped (IDOR), caps + uniqueness, exact-permutation reorder, and orphan-image
GC counting subpage photos. Reuses the create_app()+temp-DB harness.
"""

import json

from app import pages
from app.constants import PAGES_MAX, validate_page_slug, validate_page_title
from app.db import get_db
from tests.test_security import SecurityTestBase


class TestPageValidation(SecurityTestBase):
    def test_valid_slugs(self):
        for s in ("about", "my-shop", "faq2", "a1"):
            self.assertIsNone(validate_page_slug(s), s)

    def test_bad_slugs(self):
        for s in ("", "a", "-x", "x-", "Cap", "sp ace", "under_score", "x" * 41):
            self.assertIsNotNone(validate_page_slug(s), s)

    def test_reserved_slug_rejected(self):
        self.assertIsNotNone(validate_page_slug("home"))
        self.assertIsNotNone(validate_page_slug("index"))

    def test_title_validation(self):
        self.assertIsNone(validate_page_title("About me"))
        self.assertIsNotNone(validate_page_title(""))
        self.assertIsNotNone(validate_page_title("x" * 41))


class TestPageCrud(SecurityTestBase):
    def setUp(self):
        super().setUp()
        self.a, _ = self._create_user("a@test.test", username="ana")
        self.b, _ = self._create_user("b@test.test", username="ben")

    def test_create_lowercases_slug_and_get(self):
        with self.app.app_context():
            db = get_db()
            row, err = pages.create_page(db, self.a, "About", "About Me")
            self.assertIsNone(err)
            self.assertEqual(row["slug"], "about")
            self.assertEqual(pages.get_page(db, self.a, "about")["title"], "About Me")

    def test_duplicate_slug_rejected(self):
        with self.app.app_context():
            db = get_db()
            pages.create_page(db, self.a, "shop", "Shop")
            _, err = pages.create_page(db, self.a, "shop", "Shop 2")
            self.assertIsNotNone(err)

    def test_cap_enforced(self):
        with self.app.app_context():
            db = get_db()
            for i in range(PAGES_MAX):
                _, err = pages.create_page(db, self.a, f"page{i}", f"Page {i}")
                self.assertIsNone(err)
            _, err = pages.create_page(db, self.a, "one-more", "One More")
            self.assertIsNotNone(err)

    def test_crud_is_user_scoped(self):
        with self.app.app_context():
            db = get_db()
            pages.create_page(db, self.a, "secret", "Secret")
            # user B cannot see, delete, rename, or save into user A's page (IDOR)
            self.assertIsNone(pages.get_page(db, self.b, "secret"))
            self.assertFalse(pages.delete_page(db, self.b, "secret"))
            ok, _ = pages.rename_page(db, self.b, "secret", "Hacked")
            self.assertFalse(ok)
            self.assertFalse(pages.save_page_sections(db, self.b, "secret", "{}"))
            self.assertIsNotNone(pages.get_page(db, self.a, "secret"))  # untouched
            self.assertTrue(pages.delete_page(db, self.a, "secret"))

    def test_reorder_exact_permutation(self):
        with self.app.app_context():
            db = get_db()
            for s in ("one", "two", "three"):
                pages.create_page(db, self.a, s, s.title())
            self.assertTrue(pages.reorder_pages(db, self.a, ["three", "one", "two"]))
            self.assertEqual(
                [p["slug"] for p in pages.list_pages(db, self.a)],
                ["three", "one", "two"],
            )
            self.assertFalse(pages.reorder_pages(db, self.a, ["one", "two"]))       # missing
            self.assertFalse(pages.reorder_pages(db, self.a, ["one", "two", "ghost"]))  # foreign

    def test_save_then_publish(self):
        with self.app.app_context():
            db = get_db()
            pages.create_page(db, self.a, "about", "About")
            payload = json.dumps({"version": 1, "sections": []})
            self.assertTrue(pages.save_page_sections(db, self.a, "about", payload))
            row = pages.get_page(db, self.a, "about")
            self.assertIsNotNone(row["sections_draft_json"])
            self.assertIsNone(row["sections_live_json"])  # save must not publish
            self.assertTrue(
                pages.save_page_sections(db, self.a, "about", payload, publish=True))
            self.assertIsNotNone(pages.get_page(db, self.a, "about")["sections_live_json"])


class TestPageImageGc(SecurityTestBase):
    def test_referenced_images_includes_subpage_photos(self):
        from app.maintenance import referenced_images

        uid, _ = self._create_user("gc@test.test", username="gcuser")
        img = "1-abcdef012345.webp"  # matches the stored-image filename pattern
        page = json.dumps({"version": 1, "sections": [
            {"type": "gallery", "variant": "three",
             "props": {"photos": [{"caption": "", "image": img}]}}]})
        with self.app.app_context():
            db = get_db()
            pages.create_page(db, uid, "gallery", "Gallery")
            pages.save_page_sections(db, uid, "gallery", page, publish=True)
            # a live subpage's photo is referenced → GC must not sweep it
            self.assertIn(img, referenced_images(db))
