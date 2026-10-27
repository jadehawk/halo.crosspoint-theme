"""Publish one native-resolution HALO theme per actual device display size.

The source payload retains the original approved 528x792 artwork. An X4+
package crops/pads only full-width bitmaps to 480x800 without upscaling or
stretching pixels. All narrow icons/fonts remain unchanged. Future sizes can
be added by defining a resolution profile, not rewriting catalog selection.
"""
from __future__ import annotations

import argparse
import copy
import io
import json
import zipfile
from pathlib import Path

import theme_tool

PROFILES = {"x3": (528, 792), "x4plus": (480, 800)}
FULL_WIDTH = {"home-hero.cpb", "usb-connected.cpb"}
PREFIX = "halo.crosspoint-theme/"
ASSETS = "themes/halo/assets/"


def fit_ink_canvas(blob: bytes, target_width: int, target_height: int) -> bytes:
    """Center-crop/pad individual ink pixels, never scale the source drawing."""
    width, height, raw = theme_tool.decode_cpb(blob)
    stride = (width + 7) // 8
    new_stride = (target_width + 7) // 8
    converted = bytearray(new_stride * target_height)
    source_x0 = max(0, (width - target_width) // 2)
    source_y0 = max(0, (height - target_height) // 2)
    dest_x0 = max(0, (target_width - width) // 2)
    dest_y0 = max(0, (target_height - height) // 2)
    draw_w = min(width, target_width)
    draw_h = min(height, target_height)
    for y in range(draw_h):
        for x in range(draw_w):
            if raw[(y + source_y0) * stride + (x + source_x0) // 8] & (0x80 >> ((x + source_x0) % 8)):
                xx = x + dest_x0
                yy = y + dest_y0
                converted[yy * new_stride + xx // 8] |= 0x80 >> (xx % 8)
    return theme_tool.encode_cpb(bytes(converted), target_width, target_height)


def packages(root: Path, output: Path) -> list[Path]:
    payload = root / PREFIX.rstrip("/")
    original = theme_tool.read_json(payload / "manifest.json")
    scene_source = theme_tool.read_json(payload / "themes/halo/theme.json")
    theme_tool.validate(payload)
    version = original["version"]
    assert original["name"] == "halo"
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for profile, (screen_width, screen_height) in PROFILES.items():
        manifest = copy.deepcopy(original)
        manifest["target_resolution"] = {"width": screen_width, "height": screen_height}
        scene = copy.deepcopy(scene_source)
        scene["reference"].update(width=screen_width, height=screen_height)
        changed = {}
        if profile == "x4plus":
            for name in FULL_WIDTH:
                path = ASSETS + name
                width, height, _ = theme_tool.decode_cpb((payload / path).read_bytes())
                new_height = screen_height if height == 792 else height
                changed[path] = fit_ink_canvas((payload / path).read_bytes(), screen_width, new_height)
        for bitmap in (payload / "themes/halo/sleep").glob("*.cpb"):
            rel = "themes/halo/sleep/" + bitmap.name
            raw = bitmap.read_bytes()
            if profile == "x4plus":
                raw = fit_ink_canvas(raw, screen_width, screen_height)
            changed[rel] = raw
        changed["manifest.json"] = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        changed["themes/halo/theme.json"] = (json.dumps(scene, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        target = output / f"halo-{profile}-{version}.crosspoint-theme.zip"
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in sorted(changed.keys() | set(manifest["files"])):
                info = zipfile.ZipInfo(PREFIX + name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, changed.get(name, (payload / name).read_bytes()))
        with zipfile.ZipFile(target) as archive:
            assert set(archive.namelist()) == {PREFIX + name for name in (manifest["files"] + sorted(changed.keys() - set(manifest["files"]))) }
        results.append(target)
        print(f"{profile}: {target.name} ({target.stat().st_size} bytes, {len(manifest['files'])} files)")
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "dist")
    args = parser.parse_args()
    packages(args.root, args.output)


if __name__ == "__main__":
    main()
