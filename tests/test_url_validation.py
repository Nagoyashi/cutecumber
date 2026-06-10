"""URL validator tests — the XSS front line gets tests; trivial code does not
(see PROJECT_STRUCTURE.md conventions).

Run from the repo root:
    python -m unittest -v
Uses stdlib unittest on purpose: pytest is not on the dependency list
(DECISIONS.md #17).
"""

import unittest

from app.constants import LINK_URL_MAX, validate_link_url


class TestValidateLinkUrl(unittest.TestCase):
    def assertValid(self, raw, expected=None):
        url, error = validate_link_url(raw)
        self.assertIsNone(error, f"{raw!r} unexpectedly rejected: {error}")
        self.assertEqual(url, expected if expected is not None else raw)

    def assertRejected(self, raw):
        url, error = validate_link_url(raw)
        self.assertIsNone(url, f"{raw!r} unexpectedly accepted as {url!r}")
        self.assertIsNotNone(error)

    # --- happy paths ---

    def test_https(self):
        self.assertValid("https://example.com")

    def test_http(self):
        self.assertValid("http://example.com")

    def test_path_query_fragment(self):
        self.assertValid("https://example.com/a/b?q=1&r=2#frag")

    def test_explicit_port(self):
        self.assertValid("https://example.com:8443/shop")

    def test_surrounding_whitespace_stripped(self):
        self.assertValid("  https://example.com  ", "https://example.com")

    def test_schemeless_gets_https(self):
        self.assertValid("example.com", "https://example.com")

    def test_schemeless_with_path(self):
        self.assertValid("ko-fi.com/someone", "https://ko-fi.com/someone")

    def test_unicode_domain(self):
        self.assertValid("https://日本.example")

    # --- the XSS front line ---

    def test_javascript_scheme(self):
        self.assertRejected("javascript:alert(1)")

    def test_javascript_scheme_mixed_case(self):
        # urlsplit lowercases the scheme, so case games don't slip through
        self.assertRejected("JaVaScRiPt:alert(1)")

    def test_data_scheme(self):
        self.assertRejected("data:text/html,<script>alert(1)</script>")

    def test_vbscript_scheme(self):
        self.assertRejected("vbscript:msgbox(1)")

    def test_file_scheme(self):
        self.assertRejected("file:///etc/passwd")

    def test_ftp_scheme(self):
        self.assertRejected("ftp://example.com/x")

    def test_protocol_relative(self):
        # "//evil.com" picks up the page's scheme in a browser; after our
        # https:// prepend it parses with an empty netloc and is rejected.
        self.assertRejected("//evil.com")

    # --- malformed input ---

    def test_empty(self):
        self.assertRejected("")

    def test_whitespace_only(self):
        self.assertRejected("   ")

    def test_none(self):
        self.assertRejected(None)

    def test_embedded_space(self):
        self.assertRejected("https://example.com/a b")

    def test_embedded_newline(self):
        self.assertRejected("https://exa\nmple.com")

    def test_control_character(self):
        self.assertRejected("https://example.com/\x01x")

    def test_no_host(self):
        self.assertRejected("https://")

    def test_dotless_host(self):
        self.assertRejected("https://localhost")

    def test_bare_word(self):
        # auto-https turns it into https://hello — dotless host, rejected
        self.assertRejected("hello")

    def test_overlong(self):
        self.assertRejected("https://example.com/" + "a" * LINK_URL_MAX)

    def test_schemeless_host_with_port_known_limitation(self):
        # urlsplit reads "example.com:8080" as scheme example.com — we reject
        # rather than guess. Users add http(s):// for non-standard ports.
        self.assertRejected("example.com:8080")


if __name__ == "__main__":
    unittest.main()
