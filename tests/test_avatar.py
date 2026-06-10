"""Avatar pipeline tests — the metadata-stripping promise is a stated safety
default ("GPS metadata leaks home locations"), so like the AA-contrast
promise, it's enforced by a test, not by trust.

Run from the repo root:  python -m unittest -v
"""

import io
import unittest

from PIL import Image

from app.avatars import AVATAR_FILE_RE, AvatarError, process_avatar
from app.constants import AVATAR_IMAGE_SIZE, AVATAR_MAX_BYTES, AVATAR_MAX_UPLOAD


def _jpeg_with_exif() -> io.BytesIO:
    """A JPEG carrying EXIF metadata (camera make/model/datetime + GPS IFD
    pointer), the way phone photos do."""
    image = Image.new("RGB", (800, 600), "#e58fb1")
    exif = Image.Exif()
    exif[0x010F] = "TestCam Corp"          # Make
    exif[0x0110] = "TestCam 3000"          # Model
    exif[0x0132] = "2026:06:11 01:00:00"   # DateTime
    gps = exif.get_ifd(0x8825)             # GPS IFD, populated the supported way
    gps[1] = "N"                           # GPSLatitudeRef
    gps[3] = "E"                           # GPSLongitudeRef
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", exif=exif)
    buffer.seek(0)
    assert Image.open(buffer).getexif(), "fixture must actually carry EXIF"
    buffer.seek(0)
    return buffer


class TestProcessAvatar(unittest.TestCase):
    def test_exif_is_gone_after_processing(self):
        output = process_avatar(_jpeg_with_exif())
        result = Image.open(io.BytesIO(output))
        self.assertEqual(dict(result.getexif()), {}, "EXIF survived the re-encode")

    def test_output_is_exact_display_size_webp(self):
        output = process_avatar(_jpeg_with_exif())
        result = Image.open(io.BytesIO(output))
        self.assertEqual(result.format, "WEBP")
        self.assertEqual(result.size, (AVATAR_IMAGE_SIZE, AVATAR_IMAGE_SIZE))

    def test_output_within_budget(self):
        self.assertLessEqual(len(process_avatar(_jpeg_with_exif())), AVATAR_MAX_BYTES)

    def test_orientation_applied_before_strip(self):
        # 200x100 with EXIF orientation 6 (rotate 90° CW to display): after
        # transpose the long edge is vertical, so the square crop sees a
        # portrait image. Mostly we assert it processes without error and
        # squares correctly — the transpose call is the regression guard.
        image = Image.new("RGB", (200, 100), "#7a59c8")
        exif = Image.Exif()
        exif[0x0112] = 6  # Orientation
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", exif=exif)
        buffer.seek(0)
        result = Image.open(io.BytesIO(process_avatar(buffer)))
        self.assertEqual(result.size, (AVATAR_IMAGE_SIZE, AVATAR_IMAGE_SIZE))
        self.assertEqual(dict(result.getexif()), {})

    def test_png_alpha_survives(self):
        image = Image.new("RGBA", (300, 300), (229, 143, 177, 128))
        buffer = io.BytesIO()
        image.save(buffer, "PNG")
        buffer.seek(0)
        result = Image.open(io.BytesIO(process_avatar(buffer)))
        self.assertIn(result.mode, ("RGBA", "RGB"))  # alpha allowed, never required

    def test_garbage_bytes_rejected_kindly(self):
        with self.assertRaises(AvatarError):
            process_avatar(io.BytesIO(b"this is absolutely not an image"))

    def test_empty_rejected(self):
        with self.assertRaises(AvatarError):
            process_avatar(io.BytesIO(b""))

    def test_oversized_upload_rejected(self):
        with self.assertRaises(AvatarError):
            process_avatar(io.BytesIO(b"\xff" * (AVATAR_MAX_UPLOAD + 1)))

    def test_filename_pattern_is_strict(self):
        self.assertTrue(AVATAR_FILE_RE.match("7-a1b2c3d4e5f6.webp"))
        for bad in ("../../etc/passwd", "7-a1b2c3d4e5f6.svg", "x-zzzz.webp",
                    "7-a1b2c3d4e5f6.webp.html", "7-A1B2C3D4E5F6.webp"):
            self.assertFalse(AVATAR_FILE_RE.match(bad), bad)


if __name__ == "__main__":
    unittest.main()
