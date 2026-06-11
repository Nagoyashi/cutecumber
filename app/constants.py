"""Shared constants and tiny validators. One source of truth for limits.

Usernames live at the URL root (cutecumber.cc/<username>), so every route
prefix we will ever want must be reserved here BEFORE a user can claim it.
When adding a new top-level route, add its name to RESERVED_USERNAMES in the
same commit.
"""

import re

RESERVED_USERNAMES = frozenset(
    {
        "admin",
        "api",
        "login",
        "signup",
        "logout",
        "dash",
        "settings",
        "static",
        "assets",
        "help",
        "about",
        "terms",
        "privacy",
        "l",
        "app",
        "www",
        "cutecumber",
        "official",
        "reset",
        "imprint",
        "impressum",
        "legal",
    }
)

# 3-30 chars, lowercase letters / digits / dash / underscore,
# must start and end with a letter or digit (no leading/trailing separators).
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,28}[a-z0-9]$")
USERNAME_MIN = 3
USERNAME_MAX = 30

EMAIL_MAX = 254
PASSWORD_MIN = 8
PASSWORD_MAX_BYTES = 72  # hard bcrypt limit; bcrypt 4+/5 raises beyond this

# Profile field caps (enforced when profile editing ships; defined now so the
# numbers live in exactly one place).
DISPLAY_NAME_MAX = 60
BIO_MAX = 500
PRONOUNS_MAX = 40
LINK_TITLE_MAX = 100
LINK_URL_MAX = 2000
LINK_EMOJI_MAX = 8  # generous enough for ZWJ sequences like 🏳️‍🌈
MAX_LINKS_PER_PAGE = 50

# Link URLs: scheme allowlist, validated at save AND at render (DECISIONS.md
# #15). This is the XSS front line — a stored javascript: URL rendered into an
# href is game over, so nothing gets stored OR rendered without passing here.
ALLOWED_LINK_SCHEMES = ("http", "https")


def validate_link_url(raw: str) -> tuple[str | None, str | None]:
    """Validate and normalize a link URL.

    Returns (normalized_url, error_message) — exactly one is None.
    Scheme-less input ("example.com") gets https:// prepended, because that's
    what people paste. Everything that isn't plain http(s) to a real host is
    rejected: javascript:, data:, vbscript:, ftp:, protocol-relative, spaces,
    control characters, missing or dotless hosts.
    """
    from urllib.parse import urlsplit

    url = (raw or "").strip()
    if not url:
        return None, "links need a URL 🌱"
    if len(url) > LINK_URL_MAX:
        return None, f"that URL is a bit long — {LINK_URL_MAX} characters is the max 🙈"
    if any(ch.isspace() or ord(ch) < 0x20 or ord(ch) == 0x7F for ch in url):
        return None, "URLs can't contain spaces or control characters 🤏"

    try:
        parts = urlsplit(url)
    except ValueError:
        return None, "that URL doesn't look quite right 🤔"

    if not parts.scheme:
        url = "https://" + url
        try:
            parts = urlsplit(url)
        except ValueError:
            return None, "that URL doesn't look quite right 🤔"

    if parts.scheme not in ALLOWED_LINK_SCHEMES:
        return None, "links have to start with http:// or https:// 🔗"
    if not parts.netloc or "." not in parts.netloc:
        return None, "that doesn't look like a web address we can send people to 🤔"

    return url, None

# Uploaded avatars (DECISIONS.md #31): re-encoded to this exact display
# size, EXIF (incl. GPS) stripped by re-encode, hard output cap per budget.
# Freed usernames rest before re-claim — blocks day-one impersonation of a
# deleted account's old audience (DECISIONS.md #29).
TOMBSTONE_DAYS = 30

AVATAR_IMAGE_SIZE = 176          # 88px circle at 2x for retina
AVATAR_MAX_BYTES = 30 * 1024     # output budget: 30 KB
AVATAR_MAX_UPLOAD = 8 * 1024 * 1024  # input cap: 8 MB (phone photos)

# Avatars are curated tokens, never freeform input (DECISIONS.md #13).
# Validated at save AND at render; render falls back to the default on
# anything unrecognised so a bad row can never break a public page.
DEFAULT_AVATAR_EMOJI = "🥒"

AVATAR_EMOJI = (
    "🥒", "🍓", "🍵", "🍒", "🌊", "🌙",
    "⭐", "🌷", "🌸", "🌼", "🍄", "🐸",
    "🐱", "🐰", "🦋", "🐝", "🍑", "🍋",
    "🫐", "🍰", "🧸", "🎀", "✨", "💖",
)

# name -> (color_from, color_to). Rendered as linear-gradient(135deg, …).
# Names line up with the working theme-preset list on purpose.
# NOTE: swatch styles in static/dash.css duplicate these colors — keep in sync.
AVATAR_GRADIENTS = {
    "strawberry_milk": ("#ffd3e0", "#fff0f3"),
    "matcha_latte": ("#cfe8cf", "#f3f9f4"),
    "lavender_haze": ("#ddd1f0", "#f4effb"),
    "cherry_cola": ("#e8a0b4", "#fbe3ea"),
    "seafoam": ("#c9ece4", "#eafaf6"),
    "midnight_snack": ("#4a4e69", "#22223b"),
}


def validate_username(username: str) -> str | None:
    """Return a user-facing error message, or None if the username is valid.

    Caller must lowercase + strip first. Reserved names checked after shape so
    the error messages stay specific.
    """
    if not USERNAME_RE.match(username or ""):
        return (
            "usernames are 3–30 characters of lowercase letters, numbers, "
            "dashes or underscores — and can't start or end with a dash or "
            "underscore 🌱"
        )
    if username in RESERVED_USERNAMES:
        return "that one's reserved for us — pick another and it's all yours 💚"
    return None
