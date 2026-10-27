#!/usr/bin/env python3
"""Host-side CrossPoint *theme* tooling. Does not update or invoke firmware.

Run: python tools/theme_tool.py --help
The .cpb/v1 format is provisional until the firmware contract is approved.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import struct
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path, PurePosixPath

THEME_SUFFIX = ".crosspoint-theme"
HEADER = struct.Struct("<4sBBHHHII")  # magic, version, flags, w, h, stride, length, crc32
MAGIC = b"CPTB"
BITMAP_VERSION = 1
FLAGS = 1  # bit 7 is leftmost pixel, bit=1 is black ink, trailing row bits zero
MAX_WIDTH = 1024
MAX_HEIGHT = 1024
MAX_BITMAP_BYTES = 128 * 1024
MAX_PACKAGE_BYTES = 64 * 1024 * 1024  # Mirrors the verified firmware ZIP expanded-byte budget.
MAX_FILES = 64
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
ASSET_ROLES = {"header_emblem", "home_hero", "home_footer", "screen_art", "screen_background_art", "boot_art", "sleep_art", "sleep_emblem", "usb_art"}
ASSET_ROLES |= {role + "_touch" for role in tuple(ASSET_ROLES)}
ASSET_ROLES.add("screen_touch_art")  # Existing optional footer role.
REGIONS = {"header", "home", "boot", "sleep", "hints", "screen", "screen_background", "usb"}
SOURCES = {
    "screen_title", "date", "device_name", "book_title", "book_author",
    "progress_percent", "tagline", "loading_percent"
}
PALETTE = {"black", "white"}
ANCHORS = {"top-left", "top", "top-right", "left", "center", "right",
           "bottom-left", "bottom", "bottom-right"}
OPERATIONS = {"fill", "rect", "bitmap", "text", "line", "book-card", "progress"}

# All keys below correspond to the current firmware ThemeMetrics structure.
# Wide, safe upper bounds are *host* constraints; firmware must independently validate.
METRIC_FIELDS = set("""
batteryWidth batteryHeight topPadding batteryBarHeight headerHeight verticalSpacing
previewPadding previewHeightPercent contentSidePadding listRowHeight
listWithSubtitleRowHeight listRowGap listRowRadius listInset listSidePadding
listSelectionStyle listScrollWidth listScrollSide listTitleBold listSeparators
headerSidePadding headerUnderlineSize headerTitleAlign headerBatterySide
headerShowsClock headerClockCentered menuRowHeight menuSpacing tabSpacing
tabBarHeight coverGridTabBarHeight tabPillFullSlot scrollBarWidth
scrollBarRightOffset homeTopPadding homeCoverHeight homeCoverTileHeight
homeRecentBooksCount homeContinueReadingInMenu homeMenuTopOffset
buttonHintsHeight sideButtonHintsWidth progressBarHeight progressBarMarginTop
statusBarHorizontalMargin statusBarVerticalMargin keyboardKeyHeight
keyboardKeySpacing keyboardCenteredText keyboardVerticalOffset
keyboardTextFieldWidthPercent keyboardWidthPercent popupTopOffsetRatio
popupMarginX popupMarginY popupFrameThickness popupCornerRadius popupTextBold
popupTextInverted popupTextBaselineOffsetY popupProgressBarHeight
popupProgressDrawOutline popupProgressClampPercent popupProgressFillInverted
popupProgressOutlineInverted optionPopupItemSpacing optionPopupInnerPadding
optionPopupSelectionVPadding optionPopupDialogSideMargin
textFieldHorizontalPadding textFieldNormalThickness textFieldCursorThickness
textFieldLineEndOffset controlRadius sheetRadius capsuleRadius
""".split())
BOOL_METRICS = {
    "listTitleBold", "listSeparators", "headerShowsClock", "headerClockCentered",
    "tabPillFullSlot", "homeContinueReadingInMenu", "keyboardCenteredText",
    "popupTextBold", "popupTextInverted", "popupProgressDrawOutline",
    "popupProgressClampPercent", "popupProgressFillInverted", "popupProgressOutlineInverted"
}
PERCENT_METRICS = {"previewHeightPercent", "keyboardTextFieldWidthPercent", "keyboardWidthPercent"}
SIGNED_METRICS = {"keyboardVerticalOffset", "popupTextBaselineOffsetY", "textFieldLineEndOffset"}
ENUM_METRICS = {
    "listSelectionStyle": {0, 1, 2, 3}, "listScrollSide": {0, 1},
    "headerTitleAlign": {0, 1, 2}, "headerBatterySide": {0, 1},
}
HOST_LIMIT_NOTE = "Host policy limits; firmware must recheck all input independently."


class ThemeError(ValueError):
    """Invalid theme package, scene, or bitmap."""


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ThemeError("duplicate JSON key: " + key)
        result[key] = value
    return result


def read_json(path: Path) -> dict:
    try:
        if path.stat().st_size > 128 * 1024:
            raise ThemeError("JSON file too large: " + str(path))
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ThemeError("invalid JSON at " + str(path) + ": " + str(exc)) from exc
    if not isinstance(payload, dict):
        raise ThemeError(str(path) + ": expected JSON object")
    return payload


def require(condition, message: str):
    if not condition:
        raise ThemeError(message)


def exact_keys(value, allowed: set[str], required: set[str], context: str):
    require(isinstance(value, dict), context + " must be an object")
    missing = required - value.keys()
    unknown = value.keys() - allowed
    require(not missing, context + " missing keys: " + ", ".join(sorted(missing)))
    require(not unknown, context + " unknown keys: " + ", ".join(sorted(unknown)))


def safe_path(raw: str) -> str:
    require(isinstance(raw, str) and 0 < len(raw) <= 180, "unsafe empty/long path")
    require("\\" not in raw and ":" not in raw and "\x00" not in raw, "unsafe path: " + raw)
    posix = PurePosixPath(raw)
    require(not posix.is_absolute() and all(x not in ("", ".", "..") for x in raw.split("/")),
            "unsafe relative path: " + raw)
    return raw


def located_file(root: Path, relative: str) -> Path:
    safe_path(relative)
    candidate = root / relative
    # Symlinks are rejected, including symlinked parent folders.
    part = root
    for component in relative.split("/"):
        part = part / component
        require(not part.is_symlink(), "symlinks forbidden: " + relative)
    require(candidate.is_file() and candidate.resolve().is_relative_to(root.resolve()),
            "file missing/outside theme root: " + relative)
    return candidate


def encode_cpb(bits: bytes, width: int, height: int) -> bytes:
    require(type(width) is int and type(height) is int and
            1 <= width <= MAX_WIDTH and 1 <= height <= MAX_HEIGHT, "invalid image dimensions")
    stride = (width + 7) // 8
    require(len(bits) == stride * height and len(bits) <= MAX_BITMAP_BYTES,
            "invalid bitmap length/size")
    mask = (1 << (8 - (width % 8))) - 1 if width % 8 else 0
    if mask:
        require(all((bits[(y + 1) * stride - 1] & mask) == 0 for y in range(height)),
                "bitmap has nonzero row padding bits")
    return HEADER.pack(MAGIC, BITMAP_VERSION, FLAGS, width, height, stride, len(bits),
                       zlib.crc32(bits) & 0xFFFFFFFF) + bits


def decode_cpb(blob: bytes) -> tuple[int, int, bytes]:
    require(len(blob) >= HEADER.size, "truncated bitmap header")
    magic, version, flags, width, height, stride, count, crc = HEADER.unpack_from(blob)
    require(magic == MAGIC and version == BITMAP_VERSION and flags == FLAGS,
            "unsupported bitmap signature, version or flags")
    require(1 <= width <= MAX_WIDTH and 1 <= height <= MAX_HEIGHT, "invalid bitmap dimensions")
    require(stride == (width + 7) // 8, "bitmap stride mismatch")
    require(count == stride * height and count <= MAX_BITMAP_BYTES, "bitmap payload length invalid")
    require(len(blob) == HEADER.size + count, "truncated or trailing bitmap data")
    bits = blob[HEADER.size:]
    require((zlib.crc32(bits) & 0xFFFFFFFF) == crc, "bitmap CRC32 mismatch")
    # Check any padding bits; avoids ambiguous bitstream decoding.
    mask = (1 << (8 - (width % 8))) - 1 if width % 8 else 0
    if mask:
        require(all((bits[(y + 1) * stride - 1] & mask) == 0 for y in range(height)),
                "bitmap padding must be zero")
    return width, height, bits


def bool_or_int(value) -> bool:
    return type(value) is int


def check_metrics(metrics: dict):
    exact_keys(metrics, METRIC_FIELDS, set(), "metrics")
    for name, value in metrics.items():
        if name in BOOL_METRICS:
            require(type(value) is bool, "metric " + name + " must be boolean")
        elif name == "popupTopOffsetRatio":
            require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1,
                    "metric popupTopOffsetRatio must be 0..1")
        else:
            require(bool_or_int(value), "metric " + name + " must be integer")
            if name in ENUM_METRICS:
                require(value in ENUM_METRICS[name], "invalid metric enum " + name)
            elif name in PERCENT_METRICS:
                require(0 <= value <= 100, "invalid metric percentage " + name)
            elif name in SIGNED_METRICS:
                require(-128 <= value <= 128, "metric out of range " + name)
            elif name == "capsuleRadius":
                require(0 <= value <= 255, "metric out of range " + name)
            else:
                require(0 <= value <= 1024, "metric out of range " + name)


def check_region_op(op: dict, assets: dict, region: str, index: int):
    tag = region + "[" + str(index) + "]"
    require(isinstance(op, dict), tag + " must be object")
    kind = op.get("op")
    require(kind in OPERATIONS, tag + " unsupported primitive")
    shared = {"op", "color", "anchor", "offset"}
    optional = {
        "fill": set(), "rect": {"width", "height"},
        "bitmap": {"asset", "fit", "paint", "max_width", "max_height"},
        "text": {"source", "value", "font", "tracking", "max_width", "plate"},
        "line": {"thickness", "orientation"},
        "book-card": {"variant", "badge_asset"},
        "progress": {"source", "thickness"},
    }
    exact_keys(op, shared | optional[kind], {"op"}, tag)
    require(op.get("color", "black") in PALETTE, tag + " unsupported color")
    require(op.get("anchor", "top-left") in ANCHORS, tag + " invalid anchor")
    offset = op.get("offset", [0, 0])
    require(isinstance(offset, list) and len(offset) == 2 and
            all(type(v) is int and -1024 <= v <= 1024 for v in offset), tag + " invalid offset")
    for field in ("max_width", "max_height", "thickness", "tracking"):
        if field in op:
            limit = 10 if field == "tracking" else 1024
            require(type(op[field]) is int and 0 <= op[field] <= limit, tag + " invalid " + field)
    if kind == "rect":
        require(type(op.get("width")) is int and 0 <= op["width"] <= 1024 and
                type(op.get("height")) is int and 0 <= op["height"] <= 1024,
                tag + " invalid rect size")
    if kind == "bitmap":
        require(op.get("asset") in assets, tag + " unknown bitmap asset")
        require(op.get("fit", "contain") in ("contain", "cover", "native"), tag + " invalid fit")
        require(op.get("paint", "opaque") in ("opaque", "ink-only"), tag + " invalid paint")
    if kind == "text":
        require(op.get("plate", "none") in ("none", "chamfer-black", "chamfer-white"), tag + " invalid text plate")
        require(("source" in op) != ("value" in op), tag + " requires one of source/value")
        if "source" in op:
            require(op["source"] in SOURCES, tag + " invalid text source")
        else:
            require(isinstance(op["value"], str) and len(op["value"]) <= 128, tag + " bad text")
        require(op.get("font", "ui_regular") in
                ("ui_small", "ui_regular", "ui_bold", "display"), tag + " invalid font slot")
    if kind == "line":
        require(op.get("orientation", "horizontal") in ("horizontal", "vertical"),
                tag + " invalid line orientation")
    if kind == "book-card":
        require(region == "home" and op.get("variant", "standard") in ("standard", "outlined", "filled", "cover"),
                tag + " unsupported book card")
        if "badge_asset" in op:
            require(op.get("variant") != "cover", tag + " cover variant cannot use badge asset")
            require(op["badge_asset"] in assets and isinstance(assets[op["badge_asset"]], str),
                    tag + " unknown badge asset")
    if kind == "progress":
        require(op.get("source", "loading_percent") in ("loading_percent", "progress_percent"),
                tag + " invalid progress source")


def verify_cpfont(file: Path) -> None:
    """Validate the v4 monochrome font container without relying on local HALO sources."""
    data = file.read_bytes()
    require(64 <= len(data) <= 200 * 1024, "invalid cpfont size")
    require(data[:8] == bytes((67, 80, 70, 79, 78, 84, 0, 0)), "invalid cpfont signature")
    require(struct.unpack_from("<H", data, 8)[0] == 4 and
            struct.unpack_from("<H", data, 10)[0] == 0,
            "font must be monochrome cpfont v4 without unsupported flags")
    count = data[12]
    require(1 <= count <= 4 and len(data) >= 32 + 32 * count, "invalid cpfont style count")
    toc = struct.Struct("<B3xIIBhhHHBBBI4x")
    interval_record = struct.Struct("<III")
    glyph_record = struct.Struct("<BBHhhH2xI")
    section_start = 32 + 32 * count
    offsets = []
    roles = set()
    metadata = []
    for i in range(count):
        role, intervals, glyphs, height, asc, desc, kl, kr, cl, cr, lig, offset = toc.unpack_from(data, 32 + 32 * i)
        require(role <= 3 and role not in roles, "duplicate/invalid cpfont style role")
        roles.add(role)
        require(0 < intervals <= 4096 and 0 < glyphs <= 65536 and 0 < height < 256,
                "invalid cpfont style metadata")
        require(kl == kr == cl == cr == lig == 0, "unsupported cpfont kerning/ligatures")
        require(section_start <= offset < len(data), "invalid cpfont section offset")
        offsets.append(offset)
        metadata.append((intervals, glyphs))
    require(0 in roles, "cpfont must include regular style (0)")
    require(offsets == sorted(set(offsets)), "invalid cpfont section ordering")

    for i, (offset, (intervals, glyphs)) in enumerate(zip(offsets, metadata)):
        end = offsets[i + 1] if i + 1 < count else len(data)
        glyph_table = offset + intervals * interval_record.size
        bitmap_start = glyph_table + glyphs * glyph_record.size
        require(bitmap_start <= end, "cpfont interval/glyph table exceeds style section")
        last_codepoint = -1
        expected_index = 0
        for j in range(intervals):
            first, last, index = interval_record.unpack_from(data, offset + j * interval_record.size)
            require(first <= last <= 0x10FFFF and first > last_codepoint,
                    "invalid/overlapping cpfont Unicode intervals")
            span = last - first + 1
            require(index == expected_index and expected_index + span <= glyphs,
                    "invalid cpfont glyph index/interval span")
            expected_index += span
            last_codepoint = last
        require(expected_index == glyphs, "cpfont intervals do not cover glyph count")

        bitmap_length = end - bitmap_start
        for j in range(glyphs):
            width, height, _advance, _left, _top, length, data_offset = glyph_record.unpack_from(
                data, glyph_table + j * glyph_record.size)
            packed = (width * height + 7) // 8
            require(length == packed, "invalid cpfont glyph bitmap length")
            require(data_offset <= bitmap_length and length <= bitmap_length - data_offset,
                    "cpfont glyph bitmap extends outside style section")



def resolve_theme_root(path: Path) -> Path:
    """Accept either the repo root or the direct <id>.crosspoint-theme payload."""
    root = path.resolve()
    require(root.is_dir(), "theme path must be a directory")
    if (root / "manifest.json").is_file():
        require(root.name.endswith(THEME_SUFFIX), "theme root must end .crosspoint-theme")
        return root
    candidates = [
        child for child in root.iterdir()
        if child.is_dir() and not child.is_symlink()
        and child.name.endswith(THEME_SUFFIX)
        and (child / "manifest.json").is_file()
    ]
    require(len(candidates) == 1, "repository must contain exactly one .crosspoint-theme payload")
    return candidates[0].resolve()


def load_theme_definition(root: Path, manifest: dict, theme_id: str) -> tuple[dict, dict]:
    """Select one theme in the collection; callers must validate the pack first."""
    matches = [item for item in manifest["themes"] if item["id"] == theme_id]
    require(len(matches) == 1, "unknown theme ID: " + theme_id)
    entry = matches[0]
    return entry, read_json(located_file(root, entry["path"]))


def validate(root: Path) -> dict:
    """Validate an entire collection, including every included theme and shared asset."""
    root = resolve_theme_root(root)
    require(root.name.endswith(THEME_SUFFIX), "theme root must end .crosspoint-theme")
    manifest = read_json(root / "manifest.json")
    expected = {"kind", "name", "title", "description", "author", "version",
                "files", "themes", "license"}
    exact_keys(manifest, expected | {"target_resolution"}, expected, "manifest")
    if "target_resolution" in manifest:
        dims = manifest["target_resolution"]
        require(isinstance(dims, dict) and set(dims) == {"width", "height"} and
                all(type(dims[k]) is int and 1 <= dims[k] <= MAX_HEIGHT for k in ("width", "height")),
                "theme target_resolution must specify positive width and height")
    require(manifest["kind"] == "theme-pack", "manifest kind must be theme-pack")
    name = manifest["name"]
    require(isinstance(name, str) and ID_RE.fullmatch(name) is not None, "invalid theme ID")
    require(root.name == name + THEME_SUFFIX, "root folder must equal theme ID + .crosspoint-theme")
    require(isinstance(manifest["version"], str) and VERSION_RE.fullmatch(manifest["version"]),
            "invalid semantic version")
    for field in ("title", "description", "author", "license"):
        require(isinstance(manifest[field], str) and
                1 <= len(manifest[field]) <= 180, "invalid field: " + field)
    require(all(manifest[field].isascii() for field in ("title", "description", "author")),
            "display metadata must use ASCII supported by device fonts")
    themes = manifest["themes"]
    require(isinstance(themes, list) and 1 <= len(themes) <= 16,
            "theme-pack requires 1..16 theme definitions")
    ids = set()
    theme_paths = set()
    for entry in themes:
        exact_keys(entry, {"id", "title", "path", "requires"},
                   {"id", "title", "path", "requires"}, "theme entry")
        tid = entry["id"]
        require(isinstance(tid, str) and ID_RE.fullmatch(tid) is not None,
                "invalid theme ID in collection")
        require(tid not in ids, "duplicate theme ID in collection: " + tid)
        ids.add(tid)
        require(isinstance(entry["title"], str) and 1 <= len(entry["title"]) <= 100 and
                entry["title"].isascii(), "theme title must be short displayable ASCII")
        require(isinstance(entry["path"], str), "invalid theme definition path")
        safe_path(entry["path"])
        require(entry["path"] == "themes/" + tid + "/theme.json",
                "theme definition must be at themes/<id>/theme.json")
        theme_paths.add(entry["path"])
        requires = entry["requires"]
        require(isinstance(requires, list) and 1 <= len(requires) <= 16 and
                all(isinstance(x, str) and re.fullmatch(r"[a-z0-9.-]{1,48}", x) for x in requires)
                and len(set(requires)) == len(requires) and "theme.sd.v1" in requires,
                "theme must require unique supported capabilities including theme.sd.v1")

    files = manifest["files"]
    require(isinstance(files, list) and 3 <= len(files) <= MAX_FILES and
            all(isinstance(x, str) for x in files) and len(set(files)) == len(files),
            "files must be a short unique list")
    require({"manifest.json", "README.md", "DETAILS.md"}.issubset(files) and theme_paths.issubset(files),
            "missing mandatory files declaration")
    readme = located_file(root, "README.md").read_bytes()
    require(len(readme) <= 2048 and readme.isascii() and
            all(byte >= 32 or byte in (10, 13) for byte in readme) and
            not any(line.lstrip().startswith(("#", "*", "`")) for line in readme.decode("ascii").splitlines()),
            "package README must be <=2 KiB printable ASCII plain text")
    details = located_file(root, "DETAILS.md").read_bytes()
    require(0 < len(details) <= 12 * 1024, "DETAILS.md must be present and at most 12 KiB")
    try:
        require(bool(details.decode("utf-8").strip()), "DETAILS.md cannot be empty")
    except UnicodeDecodeError as exc:
        raise ThemeError("DETAILS.md must be valid UTF-8") from exc
    require(all(not p.endswith((".py", ".sh", ".js")) for p in files),
            "cannot install developer tools as theme runtime files")
    size = 0
    for filename in files:
        file = located_file(root, filename)
        size += file.stat().st_size
        require(size <= MAX_PACKAGE_BYTES, "theme total install bytes exceed budget")

    resource_paths = set()
    font_paths = set()
    primitive_count = 0
    region_count = 0
    for entry in themes:
        tid = entry["id"]
        spec = read_json(located_file(root, entry["path"]))
        exact_keys(spec, {"schema_version", "base", "reference", "metrics", "styles",
                          "assets", "regions", "fonts"},
                   {"schema_version", "base", "reference", "metrics", "styles",
                    "assets", "regions"}, "theme")
        require(type(spec["schema_version"]) is int and spec["schema_version"] == 1,
                "unsupported theme schema")
        require(spec["base"] in ("classic",), "unknown base layout")
        ref = spec["reference"]
        exact_keys(ref, {"width", "height", "adapt"}, {"width", "height", "adapt"}, "reference")
        require(type(ref["width"]) is int and type(ref["height"]) is int and
                1 <= ref["width"] <= MAX_WIDTH and 1 <= ref["height"] <= MAX_HEIGHT,
                "invalid theme reference dimensions")
        require(ref["adapt"] in ("center-crop", "scale-to-fit"), "invalid adaptive rule")
        check_metrics(spec["metrics"])
        styles = spec["styles"]
        exact_keys(styles, {"header_background", "header_foreground", "selection",
                            "row_separators", "corners", "chamfer_cut", "settings_navigation",
                            "chamfer_card_cut", "chamfer_row_cut", "chamfer_hint_cut",
                             "menu_double_outline", "menu_footer_asset", "menu_footer_touch_asset", "header_back_style"},
                   {"header_background", "header_foreground", "selection",
                    "row_separators", "corners", "chamfer_cut"}, "styles")
        require(styles["header_background"] in PALETTE and
                styles["header_foreground"] in PALETTE, "invalid palette")
        require(styles["selection"] in ("invert", "underline", "pill", "triangle"),
                "invalid selection")
        require(type(styles["row_separators"]) is bool, "row_separators must be boolean")
        require(styles["corners"] in ("square", "rounded", "chamfer"), "unknown corner shape")
        require(styles.get("settings_navigation", "list") in ("list", "tabs"),
                "settings_navigation must be list or tabs")
        require(("settings_navigation" in styles) == ("theme.settings-navigation.v1" in entry["requires"]),
                "settings navigation capability must match theme preference")
        require(styles["row_separators"] == spec["metrics"].get("listSeparators", styles["row_separators"]),
                "conflicting list separator settings")
        selection_map = {"invert": 0, "pill": 1, "underline": 2, "triangle": 3}
        require(spec["metrics"].get("listSelectionStyle", selection_map[styles["selection"]]) ==
                selection_map[styles["selection"]], "conflicting list selection settings")
        for cut in ("chamfer_cut", "chamfer_card_cut", "chamfer_row_cut", "chamfer_hint_cut"):
            if cut in styles:
                require(type(styles[cut]) is int and 0 <= styles[cut] <= 32,
                        "invalid chamfer size for " + cut)
        if "menu_double_outline" in styles:
            require(type(styles["menu_double_outline"]) is bool, "menu outline must be boolean")
        if "menu_footer_asset" in styles:
            require(isinstance(styles["menu_footer_asset"], str) and
                    styles["menu_footer_asset"] == "home_footer", "invalid menu footer role")
        if "menu_footer_touch_asset" in styles:
            require(styles.get("menu_footer_asset") == "home_footer" and
                    styles["menu_footer_touch_asset"] == "home_footer_touch",
                    "touch footer requires the normal footer asset")
        if "header_back_style" in styles:
            require(styles["header_back_style"] in ("arrow", "emblem", "both"),
                    "invalid header back style")
        require(("header_back_style" in styles) == ("theme.header-back.v1" in entry["requires"]),
                "header back capability must match theme style")
        has_menu_decoration = bool(styles.get("menu_double_outline", False) or
                                   styles.get("menu_footer_asset"))
        require(has_menu_decoration == ("theme.menu-decoration.v1" in entry["requires"]),
                "menu decoration capability must match styles")
        if has_menu_decoration:
            require(styles.get("chamfer_row_cut", 0) > 0,
                    "menu decoration requires chamfer_row_cut")
        fonts = spec.get("fonts", {})
        require(isinstance(fonts, dict) and
                (not fonts or set(fonts) == {"ui"} or
                 set(fonts) == {"ui_small", "ui_regular", "ui_large", "display"}),
                "invalid font role set")
        if isinstance(fonts.get("ui"), dict):
            variants = fonts["ui"]
            require(set(variants) == {"small", "regular", "large", "display"},
                    "invalid UI font family variants")
            font_files = variants.values()
        else:
            font_files = fonts.values()
        for path in font_files:
            require(isinstance(path, str) and
                    path.startswith("themes/" + tid + "/fonts/") and path.endswith(".cpfont"),
                    "invalid font path")
            require(path in files, "font missing from manifest files")
            file = located_file(root, path)
            require(64 <= file.stat().st_size <= 200 * 1024,
                    "font file exceeds per-role budget")
            verify_cpfont(file)
            resource_paths.add(path)
            font_paths.add(path)
        if isinstance(fonts.get("ui"), dict):
            ordered_paths = [fonts["ui"][role] for role in ("small", "regular", "large", "display")]
            require(len(set(ordered_paths)) == 4, "font family variants must use four distinct files")
            heights = []
            for path in ordered_paths:
                blob = located_file(root, path).read_bytes()
                # verify_cpfont() above guarantees a regular style (role 0).
                count = blob[12]
                regular = next(i for i in range(count) if blob[32 + i * 32] == 0)
                heights.append(blob[32 + regular * 32 + 12])
            require(all(a < b for a, b in zip(heights, heights[1:])),
                    "four-size font family must increase from small to display")
        require((set(fonts) == {"ui"}) == ("theme.font-family.v1" in entry["requires"]),
                "font family capability must match UI family declaration")
        require(bool(fonts) == ("theme.fonts.v1" in entry["requires"]),
                "font capability must match theme font payload")
        assets = spec["assets"]
        require(isinstance(assets, dict) and set(assets).issubset(ASSET_ROLES),
                "unsupported asset role")
        for role, val in assets.items():
            if role == "sleep_art":
                require(isinstance(val, str) and val == "themes/" + tid + "/sleep",
                        "sleep_art must name the theme-local sleep directory")
                sleep_dir = root / val
                require(sleep_dir.is_dir(), "missing sleep image directory")
                sleep_images = sorted(sleep_dir.iterdir())
                require(sleep_images, "theme sleep directory must contain CPB files")
                for image in sleep_images:
                    rel = image.relative_to(root).as_posix()
                    safe_path(rel)
                    require(image.is_file() and image.suffix == ".cpb", "invalid theme sleep gallery entry")
                    blob = image.read_bytes()
                    require(len(blob) <= 8 * 1024 * 1024, "sleep bitmap exceeds individual file budget")
                    decode_cpb(blob)
                    size += len(blob)
                    require(size <= MAX_PACKAGE_BYTES, "sleep gallery exceeds package byte budget")
                    resource_paths.add(rel)
                continue
            paths = val if isinstance(val, list) else [val]
            require(isinstance(val, str), "non-sleep theme assets must be scalar bitmap paths")
            require(len(paths) == 1 and isinstance(paths[0], str), "invalid bitmap path")
            for path in paths:
                safe_path(path)
                require(path.startswith("themes/" + tid + "/assets/") or
                        path.startswith("shared/assets/"),
                        "theme asset must belong to this theme or shared assets")
                require(path.endswith(".cpb") and path in files, "undeclared bitmap: " + path)
                decode_cpb(located_file(root, path).read_bytes())
                resource_paths.add(path)
        if "menu_footer_asset" in styles:
            require(styles["menu_footer_asset"] in assets,
                    "menu footer image must be declared")
        if "menu_footer_touch_asset" in styles:
            require(styles["menu_footer_touch_asset"] in assets,
                    "touch footer image must be declared")
        for role in assets:
            if role.endswith("_touch"):
                require(role[:-6] in assets, "touch asset requires base asset")
                require(role != "sleep_art_touch" and isinstance(assets[role], str),
                        "device-sized sleep galleries must use the sleep directory")
        if "screen_touch_art" in assets:
            require(isinstance(assets["screen_touch_art"], str), "touch variant must be one bitmap path")
        if "screen_touch_art" in assets:
            require("screen_art" in assets and "theme.screen-decoration.v1" in entry["requires"],
                    "touch screen footer requires ordinary screen decoration")
        regions = spec["regions"]
        require(isinstance(regions, dict) and set(regions).issubset(REGIONS),
                "unsupported region")
        required_capabilities = {"theme.sd.v1"}
        if spec["metrics"]:
            required_capabilities.add("theme.metrics.v1")
        if assets:
            required_capabilities.add("theme.images.v1")
        if "sleep_art" in assets:
            required_capabilities.add("theme.sleep-gallery.v1")
        if any(regions.values()):
            required_capabilities.add("theme.composition.v1")
        if "screen" in regions and regions["screen"]:
            require(len(regions["screen"]) == 1, "screen decoration requires one bitmap")
            screen = regions["screen"][0]
            require(screen.get("op") == "bitmap" and screen.get("paint") == "ink-only" and
                    screen.get("asset") == "screen_art" and
                    1 <= screen.get("max_height", 0) <= 128,
                    "invalid screen decoration: must use bounded ink-only bitmap")
            required_capabilities.add("theme.screen-decoration.v1")
        require(bool(regions.get("screen")) == ("theme.screen-decoration.v1" in entry["requires"]),
                "screen decoration capability must match screen region")
        if "screen_background" in regions and regions["screen_background"]:
            require(len(regions["screen_background"]) == 1, "screen background requires one bitmap")
            bg = regions["screen_background"][0]
            require(bg.get("op") == "bitmap" and bg.get("paint") == "ink-only" and
                    bg.get("asset") == "screen_background_art" and
                    1 <= bg.get("max_height", 0) <= 1024,
                    "invalid screen background: requires bounded ink-only bitmap")
            required_capabilities.add("theme.screen-background.v1")
        require(bool(regions.get("screen_background")) ==
                ("theme.screen-background.v1" in entry["requires"]),
                "screen background capability must match background region")
        # The USB screen is fully painted before the computer takes ownership
        # of the SD filesystem; reject every operation that could depend on UI
        # fonts, dynamic strings, or non-full-frame artwork.
        if regions.get("usb"):
            require(len(regions["usb"]) == 1, "USB scene requires exactly one image")
            op = regions["usb"][0]
            require(op.get("op") == "bitmap" and op.get("asset") == "usb_art" and
                    op.get("paint", "opaque") == "opaque" and
                    not any(k in op for k in ("offset", "max_width", "max_height")),
                    "USB scene must use one full-frame opaque bitmap")
            required_capabilities.add("theme.usb-scene.v1")
        require(bool(regions.get("usb")) == ("theme.usb-scene.v1" in entry["requires"]) ==
                ("usb_art" in assets), "USB scene, artwork and capability must match")
        if any(op.get("op") == "book-card" and op.get("variant") == "cover"
               for ops in regions.values() for op in ops):
            required_capabilities.add("theme.book-cover.v1")
        require(required_capabilities.issubset(set(entry["requires"])),
                "theme requires missing feature capability")
        for key, ops in regions.items():
            require(isinstance(ops, list) and len(ops) <= 16, "too many region primitives")
            for i, op in enumerate(ops):
                check_region_op(op, assets, key, i)
        count = sum(map(len, regions.values()))
        require(count <= 48, "too many primitives")
        primitive_count += count
        region_count += len(regions)
    allowed_resources = {"manifest.json", "README.md", "DETAILS.md"} | theme_paths | resource_paths
    require(set(files).issubset(allowed_resources),
            "manifest includes unreferenced files or unsupported resource")
    return {"name": name, "version": manifest["version"], "themes": len(themes),
            "theme_ids": sorted(ids), "files": len(files) + len(resource_paths - set(files)), "bytes": size,
            "bitmaps": len(resource_paths - font_paths), "fonts": len(font_paths), "regions": region_count,
            "primitives": primitive_count}



def image_to_bits(image) -> tuple[int, int, bytes]:
    # Pillow mode '1' exports MSB-first 1=white; invert to 1=ink.
    w, h = image.size
    monochrome = image.convert("1")
    white_bits = monochrome.tobytes()
    stride = (w + 7) // 8
    result = bytearray(len(white_bits))
    valid = (0xFF << (8 - (w % 8))) & 0xFF if w % 8 else 0xFF
    for y in range(h):
        for x in range(stride):
            b = (~white_bits[y * stride + x]) & 0xFF
            result[y * stride + x] = b & (valid if x == stride - 1 else 0xFF)
    return w, h, bytes(result)


def convert_image(source: Path, destination: Path, width: int, height: int,
                  fit: str, focus_x: float, focus_y: float, dither: str):
    from PIL import Image, ImageOps

    require(1 <= width <= MAX_WIDTH and 1 <= height <= MAX_HEIGHT, "invalid target dimensions")
    require(0 <= focus_x <= 1 and 0 <= focus_y <= 1, "focus must be between 0 and 1")
    with Image.open(source) as original:
        original.verify()
    with Image.open(source) as source_image:
        source_image = ImageOps.exif_transpose(source_image).convert("RGB")
        require(source_image.width * source_image.height <= 20_000_000,
                "source image has too many pixels")
        if fit == "cover":
            image = ImageOps.fit(source_image, (width, height),
                                 method=Image.Resampling.LANCZOS, centering=(focus_x, focus_y))
        elif fit == "contain":
            image = ImageOps.pad(source_image, (width, height), color="white",
                                 method=Image.Resampling.LANCZOS, centering=(focus_x, focus_y))
        else:
            raise ThemeError("unsupported image fit")
        require(dither in ("fs", "threshold"), "unsupported image dithering")
        image = image.convert("L")
        image = image.convert("1", dither=Image.Dither.FLOYDSTEINBERG
                              if dither == "fs" else Image.Dither.NONE)
        w, h, bits = image_to_bits(image)
    blob = encode_cpb(bits, w, h)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(blob)
    return {"width": w, "height": h, "bytes": len(blob)}


def preview_cpb(source: Path, destination: Path):
    from PIL import Image

    width, height, bits = decode_cpb(source.read_bytes())
    stride = (width + 7) // 8
    image = Image.new("1", (width, height), 1)
    px = image.load()
    for y in range(height):
        for x in range(width):
            px[x, y] = 0 if (bits[y * stride + x // 8] & (0x80 >> (x % 8))) else 1
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)
    return {"width": width, "height": height}


def pack_theme(root: Path, destination: Path):
    root = resolve_theme_root(root)  # ZIP root is always the payload folder name.
    summary = validate(root)
    manifest = read_json(root / "manifest.json")
    require(destination.suffix.lower() == ".zip", "output must have .zip extension")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Reproducible sorted ZIP; no developer files, timestamps, symlinks or parent traversal.
    sleep_files = sorted(
        path for entry in manifest["themes"]
        for path in (
            "themes/" + entry["id"] + "/sleep/" + image.name
            for image in (root / "themes" / entry["id"] / "sleep").glob("*.cpb")
        )
    )
    install_files = sorted(set(manifest["files"]) | set(sleep_files))
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".zip", delete=False) as temp:
        temporary = Path(temp.name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED) as archive:
            for rel in install_files:
                info = zipfile.ZipInfo(root.name + "/" + rel, (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, located_file(root, rel).read_bytes())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    summary["archive"] = str(destination)
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate", help="Validate theme payload (or its parent repository)")
    check.add_argument("--root", type=Path, default=Path("."))
    pack = sub.add_parser("pack", help="Validate and create deterministic install-only ZIP")
    pack.add_argument("--root", type=Path, default=Path("."))
    pack.add_argument("--output", type=Path, required=True)
    convert = sub.add_parser("convert", help="Convert owned/licensed image to 1-bit .cpb")
    convert.add_argument("--input", type=Path, required=True)
    convert.add_argument("--output", type=Path, required=True)
    convert.add_argument("--width", type=int, required=True)
    convert.add_argument("--height", type=int, required=True)
    convert.add_argument("--fit", choices=("cover", "contain"), default="cover")
    convert.add_argument("--focus-x", type=float, default=0.5)
    convert.add_argument("--focus-y", type=float, default=0.5)
    convert.add_argument("--dither", choices=("fs", "threshold"), default="fs")
    preview = sub.add_parser("preview", help="Write a PNG preview of a .cpb")
    preview.add_argument("--input", type=Path, required=True)
    preview.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            result = validate(args.root)
        elif args.command == "pack":
            result = pack_theme(args.root, args.output)
        elif args.command == "convert":
            result = convert_image(args.input, args.output, args.width, args.height,
                                   args.fit, args.focus_x, args.focus_y, args.dither)
        else:
            result = preview_cpb(args.input, args.output)
    except (ThemeError, OSError, ValueError, ImportError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
