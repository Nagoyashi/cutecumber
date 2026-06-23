"""Security regression tests — the promises strangers rely on get tests, the
way EXIF-stripping and AA-contrast do (issue #6). These lock in behaviour that
must never silently regress:

- CSRF: every mutating request is rejected without a matching token (DECISIONS #4).
- IDOR: a user can't touch another user's links — the `AND user_id = ?` line
  (RULES.md, links.py).
- Cookie-free public pages: GET /<username> sets no cookie and pulls zero
  third-party requests (DECISIONS #8 — this is the smoke test that entry cites).
- Password reset: tokens are single-use and expire (DECISIONS #26).
- Login: identical response for unknown email vs wrong password — no account
  enumeration; >72-byte passwords don't blow up (DECISIONS #6).

Run from the repo root:  python -m unittest -v
stdlib unittest on purpose (DECISIONS #17). Integration-level: builds the app
via create_app() with a temp DB, exactly like test_avatar.py's env pattern.
"""

import os
import re
import tempfile
import time
import unittest

import bcrypt

from app import create_app
from app.auth import _token_hash
from app.constants import validate_username
from app.db import get_db, init_db
from app.security import session_auth_fragment
from app.theme import THEME_VERSION, default_theme_json

SITE_ORIGIN = "http://test.local"
_ENV_KEYS = ("SECRET_KEY", "DATABASE", "AVATAR_DIR", "COOKIE_SECURE", "SITE_ORIGIN")


class SecurityTestBase(unittest.TestCase):
    """Builds an isolated app on a throwaway SQLite file per test, with rate
    limiting off so a test never trips a limiter counter."""

    def setUp(self):
        self._prev_env = {k: os.environ.get(k) for k in _ENV_KEYS}
        workdir = tempfile.mkdtemp()
        os.environ["SECRET_KEY"] = "x" * 40
        os.environ["DATABASE"] = os.path.join(workdir, "test.db")
        os.environ["AVATAR_DIR"] = os.path.join(workdir, "avatars")
        os.environ["COOKIE_SECURE"] = "0"  # test client speaks http; keep the cookie
        os.environ["SITE_ORIGIN"] = SITE_ORIGIN

        self.app = create_app()
        # Rate limits are exercised elsewhere; here they'd just make repeated
        # logins/link edits flaky once a counter fills.
        self.app.config["RATELIMIT_ENABLED"] = False
        with self.app.app_context():
            init_db()

    def tearDown(self):
        for key, value in self._prev_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    # --- fixtures -----------------------------------------------------------

    def _create_user(self, email, password="correct-horse-battery", username=None):
        pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO users (email, password_hash, username, theme_json,"
                " theme_version) VALUES (?, ?, ?, ?, ?)",
                (email, pw_hash, username, default_theme_json(), THEME_VERSION),
            )
            db.commit()
            return cur.lastrowid, pw_hash

    def _add_link(self, user_id, title="My Link", url="https://example.com", position=0):
        with self.app.app_context():
            db = get_db()
            cur = db.execute(
                "INSERT INTO links (user_id, title, url, position) VALUES (?, ?, ?, ?)",
                (user_id, title, url, position),
            )
            db.commit()
            return cur.lastrowid

    def _get_link(self, link_id):
        with self.app.app_context():
            return (
                get_db()
                .execute("SELECT * FROM links WHERE id = ?", (link_id,))
                .fetchone()
            )

    def _login(self, client, user_id, pw_hash, csrf="tok"):
        with client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["auth"] = session_auth_fragment(pw_hash)
            sess["_csrf"] = csrf

    def _arm_csrf(self, client, csrf="tok"):
        with client.session_transaction() as sess:
            sess["_csrf"] = csrf


class TestCsrf(SecurityTestBase):
    """A forged mutating request (no/wrong token) must be refused — proven on a
    real data mutation, the link delete."""

    def setUp(self):
        super().setUp()
        self.uid, self.pw = self._create_user("a@test.test", username="alice")
        self.link_id = self._add_link(self.uid)
        self.client = self.app.test_client()
        self._login(self.client, self.uid, self.pw)

    def test_missing_csrf_token_rejected(self):
        resp = self.client.post(f"/dash/links/{self.link_id}", data={"action": "delete"})
        self.assertEqual(resp.status_code, 400)
        self.assertIsNotNone(self._get_link(self.link_id), "link deleted despite missing CSRF")

    def test_wrong_csrf_token_rejected(self):
        resp = self.client.post(
            f"/dash/links/{self.link_id}",
            data={"action": "delete", "_csrf": "not-the-token"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIsNotNone(self._get_link(self.link_id), "link deleted despite wrong CSRF")

    def test_matching_csrf_token_allows(self):
        resp = self.client.post(
            f"/dash/links/{self.link_id}",
            data={"action": "delete", "_csrf": "tok"},
        )
        self.assertNotEqual(resp.status_code, 400)
        self.assertIsNone(self._get_link(self.link_id), "valid CSRF delete didn't take")


class TestLinkIdor(SecurityTestBase):
    """User A, fully authenticated and with a valid CSRF token, still cannot
    read/modify user B's links — the per-user query filter is the boundary."""

    def setUp(self):
        super().setUp()
        self.a_id, self.a_pw = self._create_user("alice@test.test", username="alice")
        self.b_id, self.b_pw = self._create_user("bob@test.test", username="bob")
        self.b_link = self._add_link(self.b_id, title="Bob's link", url="https://bob.test")
        self.client = self.app.test_client()
        self._login(self.client, self.a_id, self.a_pw)  # logged in AS ALICE

    def test_cannot_edit_another_users_link(self):
        self.client.post(
            f"/dash/links/{self.b_link}",
            data={"action": "save", "title": "HACKED", "url": "https://evil.test", "_csrf": "tok"},
        )
        row = self._get_link(self.b_link)
        self.assertEqual(row["title"], "Bob's link")
        self.assertEqual(row["url"], "https://bob.test")

    def test_cannot_delete_another_users_link(self):
        self.client.post(
            f"/dash/links/{self.b_link}",
            data={"action": "delete", "_csrf": "tok"},
        )
        self.assertIsNotNone(self._get_link(self.b_link), "Alice deleted Bob's link (IDOR)")

    def test_cannot_reorder_another_users_link(self):
        # Alice owns no links; submitting Bob's id is not an exact permutation
        # of her (empty) set, so the reorder is refused and Bob is untouched.
        self.client.post(
            "/dash/links/reorder",
            data={"order": str(self.b_link), "_csrf": "tok"},
        )
        self.assertEqual(self._get_link(self.b_link)["position"], 0)


class TestPublicPageCookieFree(SecurityTestBase):
    """The privacy promise as a passing test: a public profile sets no cookie
    and references no third-party origin (DECISIONS #8, RULES.md perf budget)."""

    def setUp(self):
        super().setUp()
        self.uid, _ = self._create_user("cuke@test.test", username="cuke")
        self.client = self.app.test_client()

    def test_sets_no_cookie_for_anonymous_visitor(self):
        resp = self.client.get("/cuke")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("Set-Cookie", resp.headers, "public page set a cookie")

    def test_ships_zero_javascript(self):
        resp = self.client.get("/cuke")
        self.assertNotIn(b"<script", resp.data.lower())

    def test_no_third_party_requests(self):
        resp = self.client.get("/cuke")
        body = resp.get_data(as_text=True)
        absolute = re.findall(r"https?://[^\s\"'<>)]+", body)
        external = [u for u in absolute if not u.startswith(SITE_ORIGIN)]
        self.assertEqual(external, [], f"public page references third-party URLs: {external}")


class TestResetToken(SecurityTestBase):
    """Reset tokens are single-use and time-limited (DECISIONS #26)."""

    def _set_reset(self, user_id, token, expires):
        with self.app.app_context():
            db = get_db()
            db.execute(
                "UPDATE users SET reset_token_hash = ?, reset_expires = ? WHERE id = ?",
                (_token_hash(token), expires, user_id),
            )
            db.commit()

    def test_token_is_single_use(self):
        uid, _ = self._create_user("reset@test.test")
        self._set_reset(uid, "live-token", int(time.time()) + 3600)

        consumer = self.app.test_client()
        self._arm_csrf(consumer)
        first = consumer.post(
            "/reset/live-token",
            data={"_csrf": "tok", "password": "a-fresh-cozy-password"},
        )
        self.assertEqual(first.status_code, 302)
        self.assertIn("/dash", first.headers["Location"])  # logged straight in

        # Same token again, fresh visitor: must be refused now that it's spent.
        reuse = self.app.test_client().get("/reset/live-token")
        self.assertEqual(reuse.status_code, 302)
        self.assertTrue(reuse.headers["Location"].endswith("/reset"))

    def test_expired_token_is_rejected(self):
        uid, _ = self._create_user("expired@test.test")
        self._set_reset(uid, "stale-token", int(time.time()) - 10)  # already dead

        resp = self.app.test_client().get("/reset/stale-token")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.headers["Location"].endswith("/reset"))


class TestLoginEnumeration(SecurityTestBase):
    """Login must not reveal which emails have accounts, and a >72-byte password
    must fail kindly rather than raise (DECISIONS #6)."""

    # Substring without the apostrophe — the flash renders it HTML-escaped
    # (&#39;), and we only care that the SAME neutral message shows both times.
    NEUTRAL = b"match anything we know"

    def setUp(self):
        super().setUp()
        self._create_user("known@test.test", password="the-correct-password")

    def test_unknown_email_and_wrong_password_are_indistinguishable(self):
        c1 = self.app.test_client()
        self._arm_csrf(c1)
        unknown = c1.post(
            "/login",
            data={"_csrf": "tok", "identifier": "nobody@test.test", "password": "whatever"},
        )
        c2 = self.app.test_client()
        self._arm_csrf(c2)
        wrong = c2.post(
            "/login",
            data={"_csrf": "tok", "identifier": "known@test.test", "password": "wrong-password"},
        )
        self.assertEqual(unknown.status_code, wrong.status_code)
        self.assertIn(self.NEUTRAL, unknown.data)
        self.assertIn(self.NEUTRAL, wrong.data)

    def test_overlong_password_fails_without_error(self):
        client = self.app.test_client()
        self._arm_csrf(client)
        resp = client.post(
            "/login",
            data={"_csrf": "tok", "identifier": "known@test.test", "password": "x" * 100},
        )
        self.assertEqual(resp.status_code, 200)  # not a 500 from bcrypt's 72-byte limit
        self.assertIn(self.NEUTRAL, resp.data)


class TestResetTokenScrub(unittest.TestCase):
    """The reset token must never reach an access log (issue #11). The pure
    scrubber gunicorn runs over each request path is the boundary."""

    def test_reset_token_is_redacted(self):
        from app.security import scrub_sensitive_path

        self.assertEqual(
            scrub_sensitive_path("/reset/super-secret-token"), "/reset/[redacted]"
        )

    def test_other_paths_untouched(self):
        from app.security import scrub_sensitive_path

        for path in ("/reset", "/login", "/alice", "/static/avatars/berry.svg"):
            self.assertEqual(scrub_sensitive_path(path), path)


class TestImmutableStaticCaching(SecurityTestBase):
    """Curated art (avatars, pack tiles, fonts) is immutable-cached so public
    pages stop revalidating it every load (issue #12)."""

    def setUp(self):
        super().setUp()
        self.client = self.app.test_client()

    def _cache_control(self, path):
        resp = self.client.get(path)
        try:
            return resp.headers.get("Cache-Control", "")
        finally:
            resp.close()

    def test_avatar_and_pack_tiles_are_immutable(self):
        for path in (
            "/static/avatars/berry.svg",
            "/static/packs/sakura_dreams/sparkle.svg",
            "/static/fonts/fredoka-latin-600-normal.woff2",
        ):
            self.assertIn("immutable", self._cache_control(path), path)

    def test_css_is_not_force_cached(self):
        # dash.css can change between deploys without a new name — must revalidate.
        self.assertNotIn("immutable", self._cache_control("/static/dash.css"))


class TestErrorWebhook(SecurityTestBase):
    """Optional error reporting: no-op when unset, scrubbed payload when set,
    and never raises (issue #13, DECISIONS #36)."""

    def test_noop_when_unset(self):
        from app import monitoring

        os.environ.pop("ERROR_WEBHOOK_URL", None)
        sent = []
        with self.app.test_request_context("/reset/secret-token"):
            # urlopen must never be called; if it were, this would record it.
            orig = monitoring.urllib.request.urlopen
            monitoring.urllib.request.urlopen = lambda *a, **k: sent.append(a)
            try:
                monitoring._report(self.app, ValueError("boom"))
            finally:
                monitoring.urllib.request.urlopen = orig
        self.assertEqual(sent, [], "reported despite ERROR_WEBHOOK_URL unset")

    def test_reports_scrubbed_payload_when_set(self):
        import json

        from app import monitoring

        captured = {}

        class _Resp:
            def close(self):
                pass

        def _fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _Resp()

        os.environ["ERROR_WEBHOOK_URL"] = "https://sink.test/hook"
        orig = monitoring.urllib.request.urlopen
        monitoring.urllib.request.urlopen = _fake_urlopen
        try:
            with self.app.test_request_context("/reset/secret-token"):
                monitoring._report(self.app, ValueError("boom"))
        finally:
            monitoring.urllib.request.urlopen = orig
            os.environ.pop("ERROR_WEBHOOK_URL", None)

        self.assertEqual(captured["url"], "https://sink.test/hook")
        self.assertEqual(captured["body"]["path"], "/reset/[redacted]")
        self.assertIn("ValueError: boom", captured["body"]["exception"])

    def test_delivery_failure_never_raises(self):
        from app import monitoring

        def _boom(*a, **k):
            raise monitoring.urllib.error.URLError("network down")

        os.environ["ERROR_WEBHOOK_URL"] = "https://sink.test/hook"
        orig = monitoring.urllib.request.urlopen
        monitoring.urllib.request.urlopen = _boom
        try:
            with self.app.test_request_context("/x"):
                monitoring._report(self.app, ValueError("boom"))  # must not raise
        finally:
            monitoring.urllib.request.urlopen = orig
            os.environ.pop("ERROR_WEBHOOK_URL", None)


class TestUsernameOrEmailLogin(SecurityTestBase):
    """Login accepts email OR username as the identifier (#54). They never
    collide (usernames lack '@', emails require it)."""

    def setUp(self):
        super().setUp()
        self._create_user("rob@test.test", password="a-good-password", username="rob")

    def _attempt(self, identifier, password="a-good-password"):
        client = self.app.test_client()
        self._arm_csrf(client)
        return client.post(
            "/login",
            data={"_csrf": "tok", "identifier": identifier, "password": password},
        )

    def test_login_by_email(self):
        resp = self._attempt("rob@test.test")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dash", resp.headers["Location"])

    def test_login_by_username(self):
        resp = self._attempt("rob")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dash", resp.headers["Location"])

    def test_login_by_username_is_case_insensitive(self):
        resp = self._attempt("ROB")  # the route lowercases the identifier
        self.assertEqual(resp.status_code, 302)

    def test_wrong_password_for_known_username_is_refused(self):
        resp = self._attempt("rob", password="nope")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"match anything we know", resp.data)


class TestAvatarDefaultAndLegacy(SecurityTestBase):
    """v0.4.0 (#43): new accounts default to set:sprout; legacy emoji and
    gradient avatars still render even though the picker no longer offers them
    (retired from the picker, kept at render — DECISIONS #13 addendum)."""

    def _set_avatar(self, user_id, kind, value):
        with self.app.app_context():
            db = get_db()
            db.execute(
                "UPDATE users SET avatar_kind = ?, avatar_value = ? WHERE id = ?",
                (kind, value, user_id),
            )
            db.commit()

    def test_signup_defaults_to_set_sprout(self):
        client = self.app.test_client()
        self._arm_csrf(client)
        resp = client.post(
            "/signup",
            data={"_csrf": "tok", "email": "new@test.test", "password": "a-cozy-password"},
        )
        self.assertEqual(resp.status_code, 302)
        with self.app.app_context():
            row = (
                get_db()
                .execute(
                    "SELECT avatar_kind, avatar_value FROM users WHERE email = ?",
                    ("new@test.test",),
                )
                .fetchone()
            )
        self.assertEqual((row["avatar_kind"], row["avatar_value"]), ("set", "sprout"))

    def test_legacy_emoji_avatar_still_renders(self):
        uid, _ = self._create_user("emoji@test.test", username="emojiuser")
        self._set_avatar(uid, "emoji", "🌸")
        body = self.app.test_client().get("/emojiuser").get_data(as_text=True)
        self.assertIn("🌸", body)  # not the 🥒 fallback

    def test_legacy_gradient_avatar_still_renders(self):
        uid, _ = self._create_user("grad@test.test", username="graduser")
        self._set_avatar(uid, "gradient", "matcha_latte")
        body = self.app.test_client().get("/graduser").get_data(as_text=True)
        self.assertIn("avatar-g", body)


class TestClaimCollisionState(SecurityTestBase):
    """A claim collision re-renders the form inline (200) with the attempted
    name preserved and claimable suggestion chips — no flash+redirect, no claim
    made (#52, spec §B5)."""

    def setUp(self):
        super().setUp()
        self._create_user("taken@test.test", username="cuke")  # 'cuke' is taken
        self.uid, self.pw = self._create_user("new@test.test")  # no username yet
        self.client = self.app.test_client()
        self._login(self.client, self.uid, self.pw)

    def test_taken_username_renders_inline_with_suggestions(self):
        resp = self.client.post("/dash/claim", data={"username": "cuke", "_csrf": "tok"})
        self.assertEqual(resp.status_code, 200)  # rendered, not redirected
        body = resp.get_data(as_text=True)
        self.assertIn("is-error", body)
        self.assertIn('value="cuke"', body)          # attempt preserved
        self.assertIn("suggest-chip", body)          # suggestions offered
        # The claimer still has no username — a collision claims nothing.
        with self.app.app_context():
            row = get_db().execute(
                "SELECT username FROM users WHERE id = ?", (self.uid,)
            ).fetchone()
        self.assertIsNone(row["username"])

    def test_every_suggestion_chip_is_actually_free(self):
        resp = self.client.post("/dash/claim", data={"username": "cuke", "_csrf": "tok"})
        body = resp.get_data(as_text=True)
        chips = re.findall(r'class="suggest-chip" href="\?claim_try=([^"]+)"', body)
        self.assertTrue(chips, "no suggestion chips rendered")
        with self.app.app_context():
            for name in chips:
                self.assertIsNone(validate_username(name), f"suggested invalid name {name!r}")
                taken = get_db().execute(
                    "SELECT 1 FROM users WHERE username = ?", (name,)
                ).fetchone()
                self.assertIsNone(taken, f"suggested an already-taken name {name!r}")

    def test_suggestion_link_prefills_the_field(self):
        # A chip's ?claim_try=<name> prefills the claim input on GET.
        body = self.client.get("/dash?claim_try=mochi").get_data(as_text=True)
        self.assertIn('value="mochi"', body)

    def test_malformed_prefill_is_ignored(self):
        body = self.client.get("/dash?claim_try=__nope__").get_data(as_text=True)
        self.assertNotIn('value="__nope__"', body)


class TestNotFoundFunnel(SecurityTestBase):
    """A dead /<username> becomes a claim funnel: 404 + 'claim this username'
    CTA carrying the name; stays cookie-free and zero-JS (#52, spec §B6)."""

    def setUp(self):
        super().setUp()
        self.client = self.app.test_client()

    def test_free_username_funnels_to_claim(self):
        resp = self.client.get("/freebie")
        self.assertEqual(resp.status_code, 404)
        body = resp.get_data(as_text=True)
        self.assertIn("freebie", body)
        self.assertIn("/signup", body)

    def test_funnel_is_cookie_free_and_zero_js(self):
        resp = self.client.get("/freebie")
        self.assertNotIn("Set-Cookie", resp.headers, "404 funnel set a cookie")
        self.assertNotIn(b"<script", resp.data.lower())

    def test_reserved_name_stays_generic(self):
        # Reserved names aren't claimable — no funnel CTA naming them.
        resp = self.client.get("/login")  # 'login' is a real route, not a 404
        self.assertNotEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
