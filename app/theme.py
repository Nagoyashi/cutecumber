"""Theme storage shape. Versioned from day one (DECISIONS.md #5).

The theming ENGINE (token -> CSS rendering, the validator, presets) ships in a
later session. This module exists now so that every theme_json ever written to
the database carries `version: 1` and loads through a migration registry —
no stored shape may change without a version bump and a migration function.

Shape v1:
    {
      "version": 1,
      "preset": "<preset slug>",
      "overrides": { ... }        # per-token overrides; validated by the
    }                             # theme validator when the engine ships
"""

import json

THEME_VERSION = 1
DEFAULT_PRESET = "strawberry_milk"


def default_theme() -> dict:
    return {"version": THEME_VERSION, "preset": DEFAULT_PRESET, "overrides": {}}


def default_theme_json() -> str:
    return json.dumps(default_theme(), separators=(",", ":"))


# version N -> function migrating a shape from N to N+1.
# Adding a migration REQUIRES bumping THEME_VERSION in the same commit.
MIGRATIONS: dict[int, callable] = {}


def load_theme(raw: str | None) -> dict:
    """Parse stored theme_json, migrating old shapes forward.

    Anything unparseable or structurally wrong falls back to the default theme
    rather than erroring — a broken theme must never take a public page down.
    """
    try:
        data = json.loads(raw) if raw else None
    except ValueError:
        data = None
    if not isinstance(data, dict):
        return default_theme()

    version = data.get("version")
    if not isinstance(version, int) or version < 1 or version > THEME_VERSION:
        return default_theme()

    while version < THEME_VERSION:
        data = MIGRATIONS[version](data)
        version = data["version"]
    return data
