"""The page-builder section model. Validated content, never user CSS/HTML.

STAGING surface (behind BUILDER_ENABLED). A builder page is a vertical stack of
pre-composed sections, stored in users.sections_draft_json (editor working copy)
and users.sections_live_json (what the public page renders when non-NULL).

Stored shape (users.sections_*_json):
    {
      "version": 1,
      "sections": [
        {"id": "s-abc123", "type": "hero", "variant": "centered",
         "props": {"avatar": "sprout", "name": "mochi", "pronoun": "she/her",
                   "bio": "…"}},
        ...
      ]
    }

Same philosophy as app/theme.py, applied to content instead of colour:
- validate_sections() guards the SAVE path STRICTLY — unknown type, unknown
  variant for that type, over-cap lengths/counts, off-allowlist tokens, or a
  premium type on a free plan are REJECTED outright.
- resolve_sections() guards the RENDER path TOLERANTLY — anything invalid is
  silently dropped; a bad row must never break a public page. It never raises.
- `id` is an opaque client string, used only for edit bookkeeping, never
  rendered.
- Every value that reaches a template is a validated allowlist token, a
  length-capped string rendered ESCAPED, or a validated http(s) URL. No section
  value ever becomes CSS/HTML — no |safe anywhere, exactly like theme.py.

Premium types (embed/signup/form/code) validate here but their public rendering
(sandboxed embeds, form storage, the code sandbox) lands in later builder
cycles. `code` is inert (escaped) until its cross-origin sandbox exists.
"""

import json

from .constants import (
    BIO_MAX,
    DISPLAY_NAME_MAX,
    FORM_FIELDS_MAX,
    GALLERY_PHOTOS_MAX,
    LINK_EMOJI_MAX,
    LINK_TITLE_MAX,
    LINKS_PER_SECTION_MAX,
    PRONOUNS_MAX,
    SECTION_BODY_MAX,
    SECTION_BUTTON_MAX,
    SECTION_CAPTION_MAX,
    SECTION_CODE_MAX,
    SECTION_HEADING_MAX,
    SECTIONS_MAX,
    SOCIAL_ICONS_MAX,
    validate_link_url,
)
from .constants import AVATAR_SETS

SECTIONS_VERSION = 1

# Free vs premium section TYPES. Premium types require plan == 'sprout' on save.
FREE_TYPES = frozenset({"hero", "links", "gallery", "about", "socials", "divider"})
PREMIUM_TYPES = frozenset({"embed", "signup", "form", "code"})
ALL_TYPES = FREE_TYPES | PREMIUM_TYPES

# Allowed variants per type. The FIRST entry is the default (used when an
# unknown/absent variant is tolerated on render).
VARIANTS = {
    "hero":    ("centered", "split", "banner"),
    "links":   ("buttons", "cards", "tiles"),
    "gallery": ("three", "polaroid"),
    "about":   ("simple", "note", "split"),
    "socials": ("bubbles", "pill"),
    "divider": ("line", "row"),
    "embed":   ("full", "card"),
    "signup":  ("band", "card"),
    "form":    ("card",),
    "code":    ("inert",),
}

DIVIDER_MOTIFS = frozenset(
    {"sparkle", "sparklePink", "blossom", "heart", "bow", "leaf"}
)
EMBED_KINDS = frozenset({"youtube", "spotify"})
# Strict host allowlist for the click-to-load embed facade (handoff §2.7). The
# facade is server-rendered; no third-party request happens until the visitor
# clicks. Enforced again at render when embeds ship.
EMBED_HOSTS = frozenset(
    {"youtube.com", "www.youtube.com", "youtu.be",
     "youtube-nocookie.com", "www.youtube-nocookie.com",
     "open.spotify.com"}
)

_GENERIC_ERR = "that section didn't make sense to us 🤔"


# --------------------------------------------------------------- small helpers

def _clean_text(value, cap: int) -> str | None:
    """A trimmed string within `cap`, or None if it isn't a usable string.
    Length is bounded but content is NOT sanitised here — it renders escaped."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > cap:
        return None
    return value


def _clean_emoji(value, cap: int = LINK_EMOJI_MAX) -> str:
    """Length-cap an emoji field (rendered escaped; see constants.py rationale).
    Returns '' for anything unusable rather than rejecting the whole section."""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    return value if 0 < len(value) <= cap else ""


# ------------------------------------------------------- per-type SAVE guards
# Each returns (clean_props, None) or (None, error). Strict: reject rather than
# coerce, so the editor gets a clear signal and nothing half-valid is stored.

def _v_hero(props: dict):
    avatar = props.get("avatar")
    if avatar not in AVATAR_SETS:
        return None, "pick one of our avatars for the hero 🌱"
    name = _clean_text(props.get("name"), DISPLAY_NAME_MAX)
    if name is None:
        return None, "your hero needs a name 🌸"
    clean = {"avatar": avatar, "name": name}
    if "pronoun" in props and props["pronoun"]:
        pronoun = _clean_text(props.get("pronoun"), PRONOUNS_MAX)
        if pronoun is None:
            return None, _GENERIC_ERR
        clean["pronoun"] = pronoun
    if "bio" in props and props["bio"]:
        bio = _clean_text(props.get("bio"), BIO_MAX)
        if bio is None:
            return None, _GENERIC_ERR
        clean["bio"] = bio
    return clean, None


def _v_links(props: dict):
    raw = props.get("links")
    if not isinstance(raw, list) or not raw:
        return None, "add at least one link 🔗"
    if len(raw) > LINKS_PER_SECTION_MAX:
        return None, f"up to {LINKS_PER_SECTION_MAX} links per section 🙈"
    out = []
    for item in raw:
        if not isinstance(item, dict):
            return None, _GENERIC_ERR
        title = _clean_text(item.get("title"), LINK_TITLE_MAX)
        if title is None:
            return None, "each link needs a title 🌱"
        url, err = validate_link_url(item.get("url", ""))
        if err:
            return None, err
        out.append({"emoji": _clean_emoji(item.get("emoji")), "title": title, "url": url})
    return {"links": out}, None


def _v_gallery(props: dict):
    raw = props.get("photos")
    if not isinstance(raw, list) or not raw:
        return None, "add a photo or two 📸"
    if len(raw) > GALLERY_PHOTOS_MAX:
        return None, f"up to {GALLERY_PHOTOS_MAX} photos per gallery 🙈"
    out = []
    for item in raw:
        if not isinstance(item, dict):
            return None, _GENERIC_ERR
        # Uploads aren't wired yet: only a caption is stored for now (handoff
        # §2.3). The public page skips image-less photos; the editor shows the
        # placeholder tile.
        caption = props_caption = item.get("caption", "")
        if caption:
            caption = _clean_text(props_caption, SECTION_CAPTION_MAX)
            if caption is None:
                return None, _GENERIC_ERR
        out.append({"caption": caption or ""})
    return {"photos": out}, None


def _v_about(props: dict):
    heading = _clean_text(props.get("heading"), SECTION_HEADING_MAX)
    if heading is None:
        return None, "give your story a heading 🌸"
    body = _clean_text(props.get("body"), SECTION_BODY_MAX)
    if body is None:
        return None, "add a little story 🌱"
    return {"heading": heading, "body": body}, None


def _v_socials(props: dict):
    # v1: a space-separated emoji string, each token becomes a bubble (handoff
    # §2.5). Real platform icons + URLs are a later cycle.
    raw = props.get("icons", "")
    if not isinstance(raw, str):
        return None, _GENERIC_ERR
    tokens = [t for t in raw.split() if t][:SOCIAL_ICONS_MAX]
    tokens = [t for t in (_clean_emoji(t) for t in tokens) if t]
    if not tokens:
        return None, "add a social icon or two ✨"
    return {"icons": " ".join(tokens)}, None


def _v_divider(props: dict):
    motif = props.get("motif")
    if motif not in DIVIDER_MOTIFS:
        return None, "pick one of our little motifs 🎀"
    return {"motif": motif}, None


def _v_embed(props: dict):
    from urllib.parse import urlsplit

    kind = props.get("kind")
    if kind not in EMBED_KINDS:
        return None, "pick youtube or spotify 🎬"
    url, err = validate_link_url(props.get("url", ""))
    if err:
        return None, err
    host = urlsplit(url).netloc.lower().split(":")[0]
    if host not in EMBED_HOSTS:
        return None, "we can only embed youtube or spotify links 🌱"
    return {"kind": kind, "url": url}, None


def _v_signup(props: dict):
    heading = _clean_text(props.get("heading"), SECTION_HEADING_MAX)
    if heading is None:
        return None, "give your mail list a heading 🌸"
    button = _clean_text(props.get("button"), SECTION_BUTTON_MAX) or "sign up"
    return {"heading": heading, "button": button}, None


def _v_form(props: dict):
    heading = _clean_text(props.get("heading"), SECTION_HEADING_MAX)
    if heading is None:
        return None, "give your form a heading 🌸"
    raw = props.get("fields", "")
    if not isinstance(raw, str):
        return None, _GENERIC_ERR
    fields = [f.strip() for f in raw.split(",") if f.strip()][:FORM_FIELDS_MAX]
    fields = [f for f in (_clean_text(f, SECTION_BUTTON_MAX) for f in fields) if f]
    if not fields:
        return None, "add a field or two for your form 🌱"
    return {"heading": heading, "fields": fields}, None


def _v_code(props: dict):
    code = _clean_text(props.get("code"), SECTION_CODE_MAX)
    if code is None:
        return None, f"custom html can be up to {SECTION_CODE_MAX} characters 🙈"
    return {"code": code}, None


_VALIDATORS = {
    "hero": _v_hero, "links": _v_links, "gallery": _v_gallery, "about": _v_about,
    "socials": _v_socials, "divider": _v_divider, "embed": _v_embed,
    "signup": _v_signup, "form": _v_form, "code": _v_code,
}


# ------------------------------------------------------------------ validate

def validate_sections(data: dict, plan: str = "free") -> tuple[dict | None, str | None]:
    """SAVE-path validation. Returns (clean, None) or (None, error).

    Strict: unknown type/variant, over-cap counts/lengths, off-allowlist
    tokens, and premium types on a non-'sprout' plan are all rejected.
    """
    if not isinstance(data, dict):
        return None, _GENERIC_ERR
    raw = data.get("sections")
    if not isinstance(raw, list):
        return None, _GENERIC_ERR
    if len(raw) > SECTIONS_MAX:
        return None, f"up to {SECTIONS_MAX} sections per page 🙈"

    clean = []
    for section in raw:
        if not isinstance(section, dict):
            return None, _GENERIC_ERR
        stype = section.get("type")
        if stype not in ALL_TYPES:
            return None, "that section isn't one of ours 🤔"
        if stype in PREMIUM_TYPES and plan != "sprout":
            return None, "that section blooms with sprout 🌱 — upgrade to unlock it"
        variant = section.get("variant")
        if variant not in VARIANTS[stype]:
            return None, "that section style isn't one of ours 🎀"
        props = section.get("props")
        if not isinstance(props, dict):
            return None, _GENERIC_ERR
        clean_props, err = _VALIDATORS[stype](props)
        if err:
            return None, err
        entry = {"type": stype, "variant": variant, "props": clean_props}
        sid = section.get("id")
        if isinstance(sid, str) and 0 < len(sid) <= 40:
            entry["id"] = sid
        clean.append(entry)

    return {"version": SECTIONS_VERSION, "sections": clean}, None


# --------------------------------------------------------- stored-shape / load

# version N -> function migrating a shape from N to N+1 (mirrors theme.py). Empty
# for now; adding a migration REQUIRES bumping SECTIONS_VERSION in the same commit.
MIGRATIONS: dict[int, callable] = {}


def load_sections(raw: str | None) -> dict | None:
    """Parse stored sections JSON, migrating old shapes forward; never raises.
    Returns None when there's nothing usable (so callers fall back to legacy)."""
    try:
        data = json.loads(raw) if raw else None
    except ValueError:
        data = None
    if not isinstance(data, dict):
        return None
    version = data.get("version")
    if not isinstance(version, int) or version < 1 or version > SECTIONS_VERSION:
        return None
    while version < SECTIONS_VERSION:
        data = MIGRATIONS[version](data)
        version = data["version"]
    return data


# ------------------------------------------------------------------ resolve

def resolve_sections(raw: str | None) -> list[dict]:
    """RENDER-path resolution. Tolerant: parse, then drop any section with an
    unknown type, an unknown variant, or props that don't survive its SAVE
    guard. Never raises; returns a list of {type, variant, props} ready for the
    template. `id` is intentionally dropped — it's never rendered.
    """
    data = load_sections(raw)
    if data is None:
        return []
    out = []
    for section in data.get("sections", []):
        if not isinstance(section, dict):
            continue
        stype = section.get("type")
        variant = section.get("variant")
        if stype not in ALL_TYPES or variant not in VARIANTS[stype]:
            continue
        props = section.get("props")
        if not isinstance(props, dict):
            continue
        # Re-run the type guard tolerantly: a section that no longer validates
        # (rule tightened since save, corrupted row) is silently skipped.
        clean_props, err = _VALIDATORS[stype](props)
        if err:
            continue
        out.append({"type": stype, "variant": variant, "props": clean_props})
    return out


# --------------------------------------------------- migrate an existing user

def default_sections_from_profile(user, links) -> dict:
    """Synthesise a starting page from an existing profile + links list on the
    user's FIRST visit to the builder (handoff §1.4). Does NOT write — the row
    is only persisted when they first save in the builder. `user` is a sqlite
    Row / mapping; `links` is an iterable of {emoji, title, url} rows.
    """
    def _get(row, key):
        try:
            return row[key]
        except (KeyError, IndexError, TypeError):
            return None

    name = (_get(user, "display_name") or _get(user, "username") or "").strip()
    hero_props = {
        "avatar": _get(user, "avatar_value") if _get(user, "avatar_kind") == "set"
        and _get(user, "avatar_value") in AVATAR_SETS else "sprout",
        "name": name or "me",
    }
    if _get(user, "pronouns"):
        hero_props["pronoun"] = _get(user, "pronouns")
    if _get(user, "bio"):
        hero_props["bio"] = _get(user, "bio")

    sections = [{"type": "hero", "variant": "centered", "props": hero_props}]

    link_items = []
    for row in (links or []):
        title = (_get(row, "title") or "").strip()
        url = _get(row, "url") or ""
        if not title or not url:
            continue
        link_items.append({"emoji": _clean_emoji(_get(row, "emoji")),
                            "title": title, "url": url})
        if len(link_items) >= LINKS_PER_SECTION_MAX:
            break
    if link_items:
        sections.append({"type": "links", "variant": "buttons",
                         "props": {"links": link_items}})

    return {"version": SECTIONS_VERSION, "sections": sections}
