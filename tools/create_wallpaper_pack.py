#!/usr/bin/env python3
"""Create an SD theme collection containing *only* rotating sleep artwork.

Requires Pillow for image conversion. Uses the common CrossPoint theme
validator and deterministic packer; it does not build firmware.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from theme_tool import ThemeError, convert_image, pack_theme, validate

ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
SUPPORTED = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def create(source: Path, output: Path, collection_id: str,
           title: str, author: str, version: str, width: int, height: int) -> dict:
    if not ID.fullmatch(collection_id):
        raise ThemeError("collection ID must be lowercase letters/numbers/hyphens, max 32 chars")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ThemeError("version must be MAJOR.MINOR.PATCH")
    if not source.is_dir():
        raise ThemeError("input must be a directory of images")
    files = sorted(p for p in source.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED)
    if not 1 <= len(files) <= 8:
        raise ThemeError("a wallpaper-only collection requires between 1 and 8 images")
    destination = output / (collection_id + ".crosspoint-theme")
    if destination.exists():
        raise ThemeError("output folder already exists; choose a new output path")
    if not title or not author or len(title) > 180 or len(author) > 180:
        raise ThemeError("title and author are required and must be under 180 characters")

    bitmaps = []
    try:
        for index, image in enumerate(files, 1):
            rel = f"themes/wallpapers/assets/sleep-{index:02d}.cpb"
            convert_image(image, destination / rel, width, height, "cover", 0.5, 0.5, "fs")
            bitmaps.append(rel)
        theme = {
            "schema_version": 1,
            "base": "classic",
            "reference": {"width": width, "height": height, "adapt": "scale-to-fit"},
            "metrics": {},
            "styles": {
                "header_background": "white",
                "header_foreground": "black",
                "selection": "invert",
                "row_separators": False,
                "corners": "square",
                "chamfer_cut": 0
            },
            "assets": {"sleep_art": bitmaps},
            "regions": {
                "sleep": [
                    {"op": "fill", "color": "white"},
                    {"op": "bitmap", "asset": "sleep_art", "fit": "native", "anchor": "center"}
                ]
            }
        }
        manifest = {
            "kind": "theme-pack", "name": collection_id, "title": title,
            "description": "Sleep wallpaper-only CrossPoint theme collection",
            "author": author, "version": version,
            "license": "Original image licenses and attribution remain with their respective owners",
            "themes": [{
                "id": "wallpapers", "title": title, "path": "themes/wallpapers/theme.json",
                "requires": ["theme.sd.v1", "theme.metrics.v1",
                             "theme.images.v1", "theme.composition.v1"]
            }],
            "files": ["manifest.json", "README.md", "themes/wallpapers/theme.json", *bitmaps]
        }
        theme_file = destination / "themes/wallpapers/theme.json"
        theme_file.parent.mkdir(parents=True, exist_ok=True)
        theme_file.write_text(json.dumps(theme, indent=2) + "\n", encoding="utf-8")
        (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (destination / "README.md").write_text(
            f"# {title}\n\nSleep gallery collection by {author}.\n"
            "Requires a theme-capable CrossPoint firmware. Select this theme then choose "
            "Dark/Light sleep mode. Other UI regions use Classic defaults.\n",
            encoding="utf-8"
        )
        result = validate(destination)
        archive = output / f"{collection_id}-{version}.crosspoint-theme.zip"
        pack_theme(destination, archive)
        return {"folder": str(destination), "zip": str(archive), **result}
    except Exception:
        # Don't leave an incomplete installation after conversion/validation fails.
        import shutil
        shutil.rmtree(destination, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", required=True, type=Path, help="folder of 1–8 PNG/JPEG/WebP/BMP images")
    parser.add_argument("--out", required=True, type=Path, help="output directory for payload and ZIP")
    parser.add_argument("--id", required=True, dest="collection_id", help="safe lowercase collection identifier")
    parser.add_argument("--title", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--width", type=int, default=528)
    parser.add_argument("--height", type=int, default=792)
    args = parser.parse_args()
    try:
        report = create(args.images, args.out, args.collection_id, args.title,
                        args.author, args.version, args.width, args.height)
    except (ThemeError, OSError, ValueError, ImportError) as e:
        parser.error(str(e))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
