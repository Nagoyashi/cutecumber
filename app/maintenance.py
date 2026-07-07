"""Housekeeping: garbage-collect image files no user row references any more
(issue #81). Avatar and gallery uploads share AVATAR_DIR and the /a/ route;
replacing or removing a gallery photo, or deleting an account, orphaned the old
file — there was no sweep. Conservative by design: only ever touches files that
match our own filename pattern, and only deletes a file once we've proven no
user (avatar OR gallery, draft OR live) still references it.

Run:  flask --app wsgi gc-images
"""

import json
import os

import click

from .avatars import AVATAR_FILE_RE, avatar_dir
from .db import get_db


def _images_in_sections(raw: str | None) -> set:
    """Gallery image filenames referenced in one sections_*_json column."""
    out: set = set()
    try:
        data = json.loads(raw) if raw else None
    except ValueError:
        return out
    if not isinstance(data, dict):
        return out
    for section in data.get("sections", []) or []:
        if not isinstance(section, dict) or section.get("type") != "gallery":
            continue
        for photo in (section.get("props") or {}).get("photos", []) or []:
            img = photo.get("image") if isinstance(photo, dict) else None
            if isinstance(img, str) and AVATAR_FILE_RE.match(img):
                out.add(img)
    return out


def user_gallery_images(row) -> set:
    """Every gallery image a single user references (draft + live)."""
    return _images_in_sections(row["sections_draft_json"]) | _images_in_sections(
        row["sections_live_json"]
    )


def referenced_images(db) -> set:
    """Every image filename any user still references — avatars + galleries."""
    refs: set = set()
    for row in db.execute(
        "SELECT avatar_kind, avatar_value, sections_draft_json, sections_live_json"
        " FROM users"
    ):
        if (
            row["avatar_kind"] == "image"
            and row["avatar_value"]
            and AVATAR_FILE_RE.match(row["avatar_value"])
        ):
            refs.add(row["avatar_value"])
        refs |= user_gallery_images(row)
    return refs


def gc_images(db) -> tuple[int, int]:
    """Delete unreferenced image files from AVATAR_DIR. Returns (deleted, kept).
    Files that don't match our pattern are never touched (they aren't ours)."""
    refs = referenced_images(db)
    directory = avatar_dir()
    deleted = kept = 0
    try:
        names = os.listdir(directory)
    except FileNotFoundError:
        return 0, 0
    for name in names:
        if not AVATAR_FILE_RE.match(name):
            continue
        if name in refs:
            kept += 1
            continue
        try:
            os.remove(os.path.join(directory, name))
            deleted += 1
        except FileNotFoundError:
            pass
    return deleted, kept


@click.command("gc-images")
def gc_images_command() -> None:
    deleted, kept = gc_images(get_db())
    click.echo(f"gc-images: removed {deleted} orphan(s), kept {kept} 🧹")


def init_app(app) -> None:
    app.cli.add_command(gc_images_command)
