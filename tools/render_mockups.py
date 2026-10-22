#!/usr/bin/env python3
"""Approximate host-side theme preview. Firmware geometry/fonts are authoritative.

Never used on-reader; the intent is to detect broken asset roles, ink masks,
composition/clipping, and X4 center-crop behavior before changing firmware.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from theme_tool import decode_cpb, read_json, load_theme_definition, resolve_theme_root, validate

RESOURCES = {
    "screen_title": "LIBRARY",
    "date": "OCTOBER 21, 2026",
    "device_name": "XTEINK X3",
    "book_title": "Sample Reading",
    "book_author": "Sample Author",
    "progress_percent": "35%",
    "tagline": "FINISH THE FIGHT",
    "loading_percent": "68%",
}

WHITE = 255
BLACK = 0


def rgb(color: str) -> int:
    return BLACK if color == "black" else WHITE


def load_bitmap(path: Path) -> Image.Image:
    w, h, bits = decode_cpb(path.read_bytes())
    im = Image.new("1", (w, h), 1)
    dst = im.load()
    stride = (w + 7) // 8
    for y in range(h):
        for x in range(w):
            dst[x, y] = 0 if bits[y * stride + x // 8] & (0x80 >> (x % 8)) else 1
    return im.convert("L")


def region_bounds(name: str, width: int, height: int, header_height: int, hints_height: int):
    if name == "header":
        return (0, 0, width, header_height)
    if name == "home":
        return (0, header_height, width, height - hints_height)
    if name == "hints":
        return (0, height - hints_height, width, height)
    return (0, 0, width, height)


def anchor_xy(rect, anchor: str, w: int, h: int, offset: list[int]):
    left, top, right, bottom = rect
    if anchor in ("top-left", "left", "bottom-left"):
        x = left
    elif anchor in ("top", "center", "bottom"):
        x = left + (right - left - w) // 2
    else:
        x = right - w
    if anchor in ("top-left", "top", "top-right"):
        y = top
    elif anchor in ("left", "center", "right"):
        y = top + (bottom - top - h) // 2
    else:
        y = bottom - h
    return x + offset[0], y + offset[1]


def render_op(layer: Image.Image, root: Path, spec: dict, region: str,
              rect, op: dict, font: ImageFont.ImageFont):
    draw = ImageDraw.Draw(layer)
    kind = op["op"]
    color = rgb(op.get("color", "black"))
    anchor = op.get("anchor", "top-left")
    offset = op.get("offset", [0, 0])
    x0, y0, x1, y1 = rect
    width = x1 - x0
    height = y1 - y0
    if kind == "fill":
        draw.rectangle((x0, y0, x1 - 1, y1 - 1), fill=color)
        return
    if kind == "rect":
        rw = op.get("width") or width
        rh = op.get("height") or height
        px, py = anchor_xy(rect, anchor, rw, rh, offset)
        draw.rectangle((px, py, px + rw - 1, py + rh - 1), fill=color)
        return
    if kind == "bitmap":
        asset_ref = spec["assets"][op["asset"]]
        rel = asset_ref[0] if isinstance(asset_ref, list) else asset_ref
        art = load_bitmap(root / rel)
        box_w = min(width, op.get("max_width", width))
        box_h = min(height, op.get("max_height", height))
        if op.get("fit", "contain") == "cover":
            art = ImageOps.fit(art, (box_w, box_h), method=Image.Resampling.NEAREST)
        elif op.get("fit", "contain") == "contain":
            if op.get("paint", "opaque") == "ink-only":
                art.thumbnail((box_w, box_h), Image.Resampling.NEAREST)
            else:
                art = ImageOps.pad(art, (box_w, box_h), color=WHITE,
                                  method=Image.Resampling.NEAREST)
        # native images remain their own dimensions
        px, py = anchor_xy(rect, anchor, art.width, art.height, offset)
        if op.get("paint", "opaque") == "ink-only":
            mask = ImageOps.invert(art)
            solid = Image.new("L", art.size, color)
            layer.paste(solid, (px, py), mask)
        else:
            layer.paste(art, (px, py))
        return
    if kind == "text":
        text = str(RESOURCES.get(op.get("source"), "")) if "source" in op else op["value"]
        bounds = draw.textbbox((0, 0), text, font=font)
        tw, th = bounds[2] - bounds[0], bounds[3] - bounds[1]
        px, py = anchor_xy(rect, anchor, tw, th, offset)
        plate = op.get("plate", "none")
        if plate != "none" and text:
            shade = BLACK if plate == "chamfer-black" else WHITE
            draw.rectangle((px - 8, py - 4, px + tw + 8, py + th + 4), fill=shade)
        draw.text((px, py), text, fill=color, font=font)
        return
    if kind == "line":
        thick = op.get("thickness", 1)
        if op.get("orientation", "horizontal") == "vertical":
            px, _ = anchor_xy(rect, anchor, thick, height, offset)
            draw.rectangle((px, y0, px + thick - 1, y1 - 1), fill=color)
        else:
            _, py = anchor_xy(rect, anchor, width, thick, offset)
            draw.rectangle((x0, py, x1 - 1, py + thick - 1), fill=color)
        return
    if kind == "progress":
        thick = op.get("thickness", 8)
        length = min(width - 64, 360)
        px, py = anchor_xy(rect, anchor, length, thick, offset)
        draw.rectangle((px, py, px + length, py + thick), outline=color, width=2)
        draw.rectangle((px + 2, py + 2, px + round(length * .68) - 2, py + thick - 2),
                       fill=color)
        return
    if kind == "book-card":
        card_width = max(50, width - 32)
        card_height = 116
        px, py = anchor_xy(rect, anchor, card_width, card_height, offset)
        draw.rectangle((px, py, px + card_width, py + card_height), fill=WHITE,
                       outline=BLACK, width=3)
        draw.text((px + 16, py + 18), RESOURCES["book_title"], fill=BLACK, font=font)
        draw.text((px + 16, py + 46), RESOURCES["book_author"], fill=BLACK, font=font)
        draw.line((px + 16, py + 90, px + card_width - 16, py + 90), fill=BLACK, width=2)


def render(root: Path, screen: str, width: int, height: int = 792, theme_id: str = "halo") -> Image.Image:
    root = resolve_theme_root(root)
    validate(root)
    _entry, spec = load_theme_definition(root, read_json(root / "manifest.json"), theme_id)
    if width not in (528, 480):
        raise ValueError("demo supports X3 528 or X4 480 screen widths")
    if screen not in ("home", "boot", "sleep"):
        raise ValueError("unknown screen")
    background = Image.new("L", (width, height), WHITE)
    layout = ["header", "home", "hints"] if screen == "home" else [screen]
    font = ImageFont.load_default()
    for name in layout:
        rect = region_bounds(name, width, height, spec["metrics"].get("headerHeight", 62),
                             spec["metrics"].get("buttonHintsHeight", 40))
        layer = background.copy()
        for op in spec["regions"].get(name, []):
            render_op(layer, root, spec, name, rect, op, font)
        # Critical: all operations must be clipped to their region.
        background.paste(layer.crop(rect), rect[:2])
    return background


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--theme", default="halo", help="Theme ID within the collection")
    p.add_argument("--output", type=Path, default=Path("dist/previews"))
    args = p.parse_args()
    for width, device in ((528, "x3"), (480, "x4")):
        dest = args.output / device
        dest.mkdir(parents=True, exist_ok=True)
        for screen in ("home", "boot", "sleep"):
            render(args.root, screen, width, theme_id=args.theme).save(dest / (screen + ".png"))
        print(device + ": 3 approximate previews in " + str(dest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
