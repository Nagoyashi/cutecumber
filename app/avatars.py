"""Uploaded-avatar pipeline (DECISIONS.md #31). The rules, from the original
spec: re-encode to a fixed format and size (which strips ALL metadata,
including EXIF GPS — phone photos leak home locations), cap input and output
sizes, never serve user bytes as-received, never trust the client's
content-type. The client's filename and MIME type are ignored entirely; the
bytes are identified, transposed for orientation, cropped, and re-encoded.
"""

import io
import os
import re
import secrets

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

from .constants import AVATAR_IMAGE_SIZE, AVATAR_MAX_BYTES, AVATAR_MAX_UPLOAD

# Anything above this pixel count is a decompression bomb, not an avatar.
Image.MAX_IMAGE_PIXELS = 30_000_000

_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}

# user_id "-" 12 hex chars ".webp" — also enforced at serve time (public.py).
AVATAR_FILE_RE = re.compile(r"^\d+-[0-9a-f]{12}\.webp$")


class AvatarError(ValueError):
    """User-facing, kind, and safe to flash."""


def avatar_dir() -> str:
    return os.path.join(current_app.instance_path, "avatars")


def process_avatar(stream) -> bytes:
    """Turn untrusted upload bytes into a clean 176x176 WebP. Raises
    AvatarError with a kind message on anything unusable."""
    data = stream.read(AVATAR_MAX_UPLOAD + 1)
    if len(data) > AVATAR_MAX_UPLOAD:
        raise AvatarError("that photo is a bit too big — 8 MB is the max 🐘")
    if not data:
        raise AvatarError("that file seems to be empty 🤔")

    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError):
        raise AvatarError("we couldn't read that as an image — try a jpg or png 🥺")

    if image.format not in _ALLOWED_FORMATS:
        raise AvatarError("we couldn't read that as an image — try a jpg or png 🥺")

    # Apply the EXIF orientation BEFORE the metadata is dropped, or sideways
    # phone photos stay sideways forever.
    image = ImageOps.exif_transpose(image)

    if image.mode not in ("RGB", "RGBA"):
        has_alpha = image.mode == "P" and "transparency" in image.info
        image = image.convert("RGBA" if has_alpha or image.mode == "LA" else "RGB")

    image = ImageOps.fit(
        image, (AVATAR_IMAGE_SIZE, AVATAR_IMAGE_SIZE), Image.LANCZOS
    )

    # Re-encode WITHOUT passing exif/icc — this is the metadata strip.
    for quality in (82, 70, 58):
        buffer = io.BytesIO()
        image.save(buffer, "WEBP", quality=quality, method=4)
        if buffer.tell() <= AVATAR_MAX_BYTES:
            return buffer.getvalue()
    raise AvatarError("that image wouldn't shrink enough — try a simpler one 🌀")


def store_avatar(user_id: int, blob: bytes) -> str:
    """Write the processed blob; return the new filename (cache-bust built in)."""
    filename = f"{user_id}-{secrets.token_hex(6)}.webp"
    with open(os.path.join(avatar_dir(), filename), "wb") as handle:
        handle.write(blob)
    return filename


def delete_avatar_file(filename: str | None) -> None:
    """Best-effort removal; only touches names matching our own pattern."""
    if filename and AVATAR_FILE_RE.match(filename):
        try:
            os.remove(os.path.join(avatar_dir(), filename))
        except FileNotFoundError:
            pass
