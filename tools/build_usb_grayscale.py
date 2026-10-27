"""Build native four-tone e-ink USB BMPs for HALO from approved grayscale artwork.

Requires Pillow only when regenerating the committed source assets.
The catalog and GitHub release validators themselves use the standard library.
"""
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source-art" / "usb-connected-grayscale.png"
ASSETS = ROOT / "halo.crosspoint-theme" / "themes" / "halo" / "assets"
SOURCE_ASSETS = ROOT / "source-art"
PROFILES = {"x3": (528, 792, "usb-connected.bmp"),
            "x4plus": (480, 800, "usb-connected-touch.bmp")}


def generate() -> None:
    with Image.open(SOURCE) as original:
        for profile, (width, height, name) in PROFILES.items():
            image = ImageOps.exif_transpose(original).convert("L")
            image = ImageOps.pad(image, (width, height), color=255,
                                 method=Image.Resampling.LANCZOS)
            # Preserve highlights and make the armored figure readable on e-ink.
            image = image.point(lambda value: min(255, round(255 * (value / 255) ** 0.84)))
            image = image.point(lambda value: min(3, round(value / 85)))
            image = image.convert("P")
            shades = (0, 85, 170, 255)
            image.putpalette([v for index in range(256)
                              for v in (shades[index] if index < 4 else 255,) * 3])
            target = (ASSETS if profile == "x3" else SOURCE_ASSETS) / name
            image.save(target, format="BMP")
            print(profile, target, target.stat().st_size)


if __name__ == "__main__":
    generate()
