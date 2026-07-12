"""Multi-page sites (Phase B). A creator's HOME page lives in
users.sections_*_json; their SUBPAGES live in the `pages` table, each a titled,
slugged container of the SAME section model (app/sections.py). URL is
/<username>/<slug>.

Every query is user-scoped (`AND user_id = ?`) — IDOR is unacceptable (RULES.md).
The section payload is validated by sections.validate_sections exactly like the
home page; this module owns the page container: slug, title, position, and caps.
"""

from .constants import PAGES_MAX, validate_page_slug, validate_page_title

_COLS = (
    "id, slug, title, position, sections_draft_json, sections_live_json"
)


def list_pages(db, user_id):
    """A user's subpages, ordered for the nav / page switcher."""
    return db.execute(
        f"SELECT {_COLS} FROM pages WHERE user_id = ? ORDER BY position, id",
        (user_id,),
    ).fetchall()


def get_page(db, user_id, slug):
    """One subpage by slug, user-scoped, or None."""
    return db.execute(
        f"SELECT {_COLS} FROM pages WHERE user_id = ? AND slug = ?",
        (user_id, slug),
    ).fetchone()


def page_count(db, user_id) -> int:
    return db.execute(
        "SELECT COUNT(*) AS n FROM pages WHERE user_id = ?", (user_id,)
    ).fetchone()["n"]


def create_page(db, user_id, slug, title):
    """Validate + insert a new subpage. Returns (page_row | None, error | None)."""
    slug = (slug or "").strip().lower()
    title = (title or "").strip()
    err = validate_page_slug(slug) or validate_page_title(title)
    if err:
        return None, err
    if page_count(db, user_id) >= PAGES_MAX:
        return None, f"up to {PAGES_MAX} extra pages for now 🙈"
    if get_page(db, user_id, slug) is not None:
        return None, "you already have a page at that address 🌱"
    pos = db.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 AS p FROM pages WHERE user_id = ?",
        (user_id,),
    ).fetchone()["p"]
    db.execute(
        "INSERT INTO pages (user_id, slug, title, position) VALUES (?, ?, ?, ?)",
        (user_id, slug, title, pos),
    )
    db.commit()
    return get_page(db, user_id, slug), None


def rename_page(db, user_id, slug, title):
    """Change a subpage's nav title. The slug is immutable — the URL is the
    product (like usernames, DECISIONS #3). Returns (ok, error)."""
    err = validate_page_title(title)
    if err:
        return False, err
    n = db.execute(
        "UPDATE pages SET title = ? WHERE user_id = ? AND slug = ?",
        ((title or "").strip(), user_id, slug),
    ).rowcount
    db.commit()
    return (n > 0), (None if n > 0 else "we couldn't find that page 🤔")


def delete_page(db, user_id, slug) -> bool:
    n = db.execute(
        "DELETE FROM pages WHERE user_id = ? AND slug = ?", (user_id, slug)
    ).rowcount
    db.commit()
    return n > 0


def reorder_pages(db, user_id, ordered_slugs) -> bool:
    """Set positions from an EXACT permutation of the user's subpage slugs —
    same exact-permutation guard as link reorder (no partial/foreign writes)."""
    current = {row["slug"] for row in list_pages(db, user_id)}
    if len(ordered_slugs) != len(current) or set(ordered_slugs) != current:
        return False
    for pos, slug in enumerate(ordered_slugs):
        db.execute(
            "UPDATE pages SET position = ? WHERE user_id = ? AND slug = ?",
            (pos, user_id, slug),
        )
    db.commit()
    return True


def save_page_sections(db, user_id, slug, clean_json, publish=False) -> bool:
    """Persist a VALIDATED sections payload (JSON string) to a subpage. On
    publish, also copy it to the live column. Returns whether a row matched."""
    if publish:
        n = db.execute(
            "UPDATE pages SET sections_draft_json = ?, sections_live_json = ?"
            " WHERE user_id = ? AND slug = ?",
            (clean_json, clean_json, user_id, slug),
        ).rowcount
    else:
        n = db.execute(
            "UPDATE pages SET sections_draft_json = ? WHERE user_id = ? AND slug = ?",
            (clean_json, user_id, slug),
        ).rowcount
    db.commit()
    return n > 0
