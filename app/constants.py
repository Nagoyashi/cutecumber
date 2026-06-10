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
MAX_LINKS_PER_PAGE = 50


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
