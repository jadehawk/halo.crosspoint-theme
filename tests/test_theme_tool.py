"""Regression checks for the publishable SD theme package and generic author tools."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "halo.crosspoint-theme"
sys.path.insert(0, str(ROOT / "tools"))
import theme_tool as tool
from create_wallpaper_pack import create


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)

    def copy_payload(self):
        dest = self.work / "halo.crosspoint-theme"
        shutil.copytree(PAYLOAD, dest)
        return dest

    def update_json(self, root, file, updater):
        path = root / file
        obj = json.loads(path.read_text(encoding="utf-8"))
        updater(obj)
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def test_release_payload_validates(self):
        summary = tool.validate(PAYLOAD)
        self.assertEqual(summary["name"], "halo")
        manifest = tool.read_json(PAYLOAD / "manifest.json")
        self.assertEqual(manifest["author"], "Jadehawk + IOSDEC")
        self.assertEqual(manifest["version"], "0.1.7")
        self.assertEqual(summary["themes"], 1)
        self.assertEqual(summary["bitmaps"], 9)
        self.assertEqual(summary["fonts"], 4)
        self.assertEqual(summary["files"], 17)

    def test_packaged_details_contract_is_required(self):
        root = self.copy_payload()
        details = root / "DETAILS.md"
        self.assertIn("Jadehawk + IOSDEC", details.read_text(encoding="utf-8"))
        details.unlink()
        with self.assertRaisesRegex(tool.ThemeError, "DETAILS.md"):
            tool.validate(root)

    def test_invalid_details_are_rejected(self):
        root = self.copy_payload()
        (root / "DETAILS.md").write_bytes(b"invalid" + bytes([255]))
        with self.assertRaisesRegex(tool.ThemeError, "UTF-8"):
            tool.validate(root)

    def test_repository_root_resolves_single_payload(self):
        self.assertEqual(tool.resolve_theme_root(ROOT), PAYLOAD.resolve())

    def test_manifest_lists_every_runtime_file(self):
        manifest = tool.read_json(PAYLOAD / "manifest.json")
        listed = set(manifest["files"])
        actual = {file.relative_to(PAYLOAD).as_posix()
                  for file in PAYLOAD.rglob("*") if file.is_file()}
        self.assertEqual(listed | {p for p in actual if p.startswith("themes/halo/sleep/")}, actual)
        self.assertTrue(all(not p.endswith((".py", ".png", ".jsonc")) for p in listed))

    def test_archive_is_deterministic_and_install_only(self):
        one, two = self.work / "one.zip", self.work / "two.zip"
        tool.pack_theme(ROOT, one)
        tool.pack_theme(ROOT, two)
        self.assertEqual(hashlib.sha256(one.read_bytes()).digest(), hashlib.sha256(two.read_bytes()).digest())
        with zipfile.ZipFile(one) as archive:
            names = archive.namelist()
            files = tool.read_json(PAYLOAD / "manifest.json")["files"]
            self.assertEqual(names, sorted("halo.crosspoint-theme/" + item for item in files + ["themes/halo/sleep/" + p.name for p in (PAYLOAD/"themes/halo/sleep").glob("*.cpb")]))
            released_manifest = json.loads(archive.read("halo.crosspoint-theme/manifest.json"))
            self.assertEqual(released_manifest["author"], "Jadehawk + IOSDEC")
            self.assertEqual(released_manifest["version"], "0.1.7")
            self.assertFalse(any("/tests/" in name or "/tools/" in name or "/docs/" in name for name in names))

    def test_required_capabilities_match_firmware_list(self):
        manifest = tool.read_json(PAYLOAD / "manifest.json")
        known = json.loads((ROOT / "supported-firmware.json").read_text(encoding="utf-8"))
        needed = set(manifest["themes"][0]["requires"])
        implementation = set(known["known_implementations"][0]["theme_capabilities_implemented"])
        self.assertTrue(needed.issubset(implementation))
        self.assertIn("theme.sd.v1", needed)
        self.assertIn("theme.fonts.v1", needed)

    def test_shared_ui_role_is_global_and_only_file_is_packaged(self):
        manifest = tool.read_json(PAYLOAD / "manifest.json")
        scene = tool.read_json(PAYLOAD / "themes/halo/theme.json")
        self.assertEqual(set(scene["fonts"]["ui"]), {"small", "regular", "large", "display"})
        self.assertEqual([p for p in manifest["files"] if p.endswith(".cpfont")],
                         list(scene["fonts"]["ui"].values()))

    def test_legacy_four_role_declaration_remains_valid(self):
        root = self.copy_payload()
        self.update_json(root, "themes/halo/theme.json",
                         lambda t: t.update(fonts={name: "themes/halo/fonts/" + filename
                                                  for name, filename in zip(("ui_small", "ui_regular", "ui_large", "display"),
                                                                           ("ui-small.cpfont", "ui-regular.cpfont", "ui-large.cpfont", "display.cpfont"))}))
        self.update_json(root, "manifest.json",
                         lambda m: m["themes"][0]["requires"].remove("theme.font-family.v1"))
        self.assertEqual(tool.validate(root)["fonts"], 4)

    def test_native_book_cover_variant_requires_capability(self):
        root = self.copy_payload()
        def cover(scene):
            card = next(op for op in scene["regions"]["home"] if op["op"] == "book-card")
            card["variant"] = "cover"
            card.pop("badge_asset", None)
        self.update_json(root, "themes/halo/theme.json", cover)
        with self.assertRaisesRegex(tool.ThemeError, "missing feature capability"):
            tool.validate(root)
        self.update_json(root, "manifest.json",
                         lambda m: m["themes"][0]["requires"].append("theme.book-cover.v1"))
        self.assertEqual(tool.validate(root)["themes"], 1)

    def test_menu_double_outline_requires_declared_capability(self):
        root = self.copy_payload()
        def decorate(scene):
            scene["styles"]["menu_double_outline"] = True
            scene["styles"]["chamfer_row_cut"] = 10
        self.update_json(root, "themes/halo/theme.json", decorate)
        with self.assertRaisesRegex(tool.ThemeError, "menu decoration capability"):
            tool.validate(root)
        self.update_json(root, "manifest.json",
                         lambda m: m["themes"][0]["requires"].append("theme.menu-decoration.v1"))
        self.assertEqual(tool.validate(root)["themes"], 1)

    def test_nonreading_screen_decoration_is_capability_gated(self):
        root = self.copy_payload()
        def decorate(scene):
            scene["assets"]["screen_art"] = scene["assets"]["home_hero"]
            scene["regions"]["screen"] = [{
                "op": "bitmap", "asset": "screen_art", "anchor": "bottom",
                "paint": "ink-only", "fit": "contain", "max_height": 84
            }]
        self.update_json(root, "themes/halo/theme.json", decorate)
        with self.assertRaisesRegex(tool.ThemeError, "screen decoration capability"):
            tool.validate(root)
        self.update_json(root, "manifest.json",
                         lambda m: m["themes"][0]["requires"].append("theme.screen-decoration.v1"))
        self.assertEqual(tool.validate(root)["themes"], 1)
        self.update_json(root, "themes/halo/theme.json",
                         lambda scene: scene["regions"]["screen"][0].update(paint="opaque"))
        with self.assertRaisesRegex(tool.ThemeError, "invalid screen decoration"):
            tool.validate(root)

    def test_optional_touch_footer_variants_require_base_decoration(self):
        root = self.copy_payload()
        def add_touch(scene):
            scene["assets"]["screen_touch_art"] = scene["assets"]["home_hero"]
        self.update_json(root, "themes/halo/theme.json", add_touch)
        with self.assertRaisesRegex(tool.ThemeError, "touch screen footer requires"):
            tool.validate(root)

        def add_base(scene):
            scene["assets"]["screen_art"] = scene["assets"]["home_hero"]
            scene["regions"]["screen"] = [{
                "op": "bitmap", "asset": "screen_art", "anchor": "bottom",
                "paint": "ink-only", "fit": "contain", "max_height": 84
            }]
        self.update_json(root, "themes/halo/theme.json", add_base)
        self.update_json(root, "manifest.json",
                         lambda m: m["themes"][0]["requires"].append("theme.screen-decoration.v1"))
        self.assertEqual(tool.validate(root)["themes"], 1)

    def test_sleep_gallery_discovers_many_files_without_json_arrays(self):
        root = self.copy_payload()
        directory = root/"themes/halo/sleep"
        original = (directory/"sleep-art-1.cpb").read_bytes()
        for i in range(4, 104):
            (directory/f"sleep-{i:05d}.cpb").write_bytes(original)
        self.assertEqual(tool.validate(root)["bitmaps"], 109)
        self.assertEqual(tool.validate(root)["files"], 117)
        # No sleep bitmap is enumerated in the JSON manifest.
        declared = tool.read_json(root/"manifest.json")["files"]
        self.assertFalse(any("/sleep/" in path for path in declared))
        self.update_json(root, "themes/halo/theme.json",
                         lambda theme: theme["assets"].update(sleep_art="themes/halo/other"))
        with self.assertRaisesRegex(tool.ThemeError, "sleep_art must name"):
            tool.validate(root)

    def test_touch_home_footer_requires_normal_footer(self):
        root = self.copy_payload()
        def add_touch(scene):
            scene["styles"]["menu_double_outline"] = True
            scene["styles"]["chamfer_row_cut"] = 10
            scene["styles"]["menu_footer_touch_asset"] = "home_footer_touch"
            scene["assets"]["home_footer_touch"] = scene["assets"]["home_hero"]
        self.update_json(root, "themes/halo/theme.json", add_touch)
        self.update_json(root, "manifest.json",
                         lambda m: m["themes"][0]["requires"].append("theme.menu-decoration.v1"))
        with self.assertRaisesRegex(tool.ThemeError, "touch footer requires"):
            tool.validate(root)

        def add_base(scene):
            scene["styles"]["menu_footer_asset"] = "home_footer"
            scene["assets"]["home_footer"] = scene["assets"]["home_hero"]
        self.update_json(root, "themes/halo/theme.json", add_base)
        self.assertEqual(tool.validate(root)["themes"], 1)

    def test_header_back_style_requires_capability_and_enum(self):
        root = self.copy_payload()
        self.update_json(root, "themes/halo/theme.json",
                         lambda scene: scene["styles"].update(header_back_style="both"))
        with self.assertRaisesRegex(tool.ThemeError, "header back capability"):
            tool.validate(root)
        self.update_json(root, "manifest.json",
                         lambda manifest: manifest["themes"][0]["requires"].append("theme.header-back.v1"))
        self.assertEqual(tool.validate(root)["themes"], 1)
        self.update_json(root, "themes/halo/theme.json",
                         lambda scene: scene["styles"].update(header_back_style="unrecognized"))
        with self.assertRaisesRegex(tool.ThemeError, "invalid header back style"):
            tool.validate(root)

    def test_touch_image_variant_requires_base_role(self):
        root = self.copy_payload()
        self.update_json(root, "themes/halo/theme.json",
                         lambda scene: scene["assets"].update(screen_art_touch=scene["assets"]["home_hero"]))
        with self.assertRaisesRegex(tool.ThemeError, "touch asset requires base"):
            tool.validate(root)
        self.update_json(root, "themes/halo/theme.json",
                         lambda scene: scene["assets"].update(screen_art=scene["assets"]["home_hero"]))
        self.assertEqual(tool.validate(root)["themes"], 1)
        self.update_json(root, "themes/halo/theme.json",
                         lambda scene: scene["assets"].update(screen_art_touch=[scene["assets"]["home_hero"]]))
        with self.assertRaisesRegex(tool.ThemeError, "non-sleep theme assets must be scalar bitmap paths"):
            tool.validate(root)

    def test_full_screen_background_is_optional_and_capability_gated(self):
        root = self.copy_payload()
        def decorate(scene):
            scene["assets"]["screen_background_art"] = scene["assets"]["home_hero"]
            scene["regions"]["screen_background"] = [{
                "op": "bitmap", "asset": "screen_background_art", "anchor": "center",
                "paint": "ink-only", "fit": "contain", "max_height": 792
            }]
        self.update_json(root, "themes/halo/theme.json", decorate)
        with self.assertRaisesRegex(tool.ThemeError, "screen background capability"):
            tool.validate(root)
        self.update_json(root, "manifest.json",
                         lambda m: m["themes"][0]["requires"].append("theme.screen-background.v1"))
        self.assertEqual(tool.validate(root)["themes"], 1)
        self.update_json(root, "themes/halo/theme.json",
                         lambda scene: scene["regions"]["screen_background"][0].update(paint="opaque"))
        with self.assertRaisesRegex(tool.ThemeError, "invalid screen background"):
            tool.validate(root)

    def test_unsupported_ui_role_is_rejected(self):
        root = self.copy_payload()
        self.update_json(root, "themes/halo/theme.json",
                         lambda t: t["fonts"].update(extra="themes/halo/fonts/ui-regular.cpfont"))
        with self.assertRaisesRegex(tool.ThemeError, "invalid font role set"):
            tool.validate(root)

    def test_incomplete_ui_family_is_rejected(self):
        root = self.copy_payload()
        self.update_json(root, "themes/halo/theme.json",
                         lambda t: t["fonts"]["ui"].pop("display"))
        with self.assertRaisesRegex(tool.ThemeError, "invalid UI font family variants"):
            tool.validate(root)

    def test_single_file_ui_role_remains_valid(self):
        root = self.copy_payload()
        self.update_json(root, "themes/halo/theme.json",
                         lambda t: t.update(fonts={"ui": "themes/halo/fonts/ui-regular.cpfont"}))
        self.update_json(root, "manifest.json",
                         lambda m: m.update(files=[p for p in m["files"]
                                                   if not p.endswith(".cpfont") or p.endswith("ui-regular.cpfont")]))
        self.assertEqual(tool.validate(root)["fonts"], 1)

    def test_missing_theme_file_fails(self):
        root = self.copy_payload()
        (root / "themes/halo/theme.json").unlink()
        with self.assertRaisesRegex(tool.ThemeError, "missing"):
            tool.validate(root)

    def test_traversal_in_manifest_fails(self):
        root = self.copy_payload()
        self.update_json(root, "manifest.json",
                         lambda m: m["files"].append("../outside.txt"))
        with self.assertRaises(tool.ThemeError):
            tool.validate(root)

    def test_undeclared_required_font_capability_fails(self):
        root = self.copy_payload()
        self.update_json(root, "manifest.json",
                         lambda m: m["themes"][0]["requires"].remove("theme.fonts.v1"))
        with self.assertRaisesRegex(tool.ThemeError, "font capability"):
            tool.validate(root)

    def test_invalid_chamfer_fails(self):
        root = self.copy_payload()
        self.update_json(root, "themes/halo/theme.json",
                         lambda m: m["styles"].update(chamfer_card_cut=38))
        with self.assertRaisesRegex(tool.ThemeError, "invalid chamfer"):
            tool.validate(root)

    def test_unknown_scene_operation_fails(self):
        root = self.copy_payload()
        self.update_json(root, "themes/halo/theme.json",
                         lambda m: m["regions"]["home"].append({"op": "execute"}))
        with self.assertRaises(tool.ThemeError):
            tool.validate(root)

    def test_corrupt_font_is_rejected(self):
        root = self.copy_payload()
        file = root / "themes/halo/fonts/ui-regular.cpfont"
        blob = bytearray(file.read_bytes())
        blob[0] = 0
        file.write_bytes(blob)
        with self.assertRaisesRegex(tool.ThemeError, "cpfont"):
            tool.validate(root)

    def test_cpfont_glyph_bitmap_overrun_is_rejected(self):
        root = self.copy_payload()
        file = root / "themes/halo/fonts/ui-small.cpfont"
        blob = bytearray(file.read_bytes())
        # Style 0 starts at the offset recorded in the v4 TOC.
        offset = int.from_bytes(blob[56:60], "little")
        intervals = int.from_bytes(blob[36:40], "little")
        first_glyph = offset + intervals * 12
        blob[first_glyph + 8:first_glyph + 10] = (65535).to_bytes(2, "little")
        file.write_bytes(blob)
        with self.assertRaisesRegex(tool.ThemeError, "glyph bitmap length"):
            tool.validate(root)

    def test_cpfont_invalid_unicode_intervals_are_rejected(self):
        root = self.copy_payload()
        file = root / "themes/halo/fonts/ui-small.cpfont"
        blob = bytearray(file.read_bytes())
        offset = int.from_bytes(blob[56:60], "little")
        blob[offset + 8:offset + 12] = (1).to_bytes(4, "little")
        file.write_bytes(blob)
        with self.assertRaisesRegex(tool.ThemeError, "glyph index/interval span"):
            tool.validate(root)

    def test_family_variants_must_have_distinct_increasing_sizes(self):
        root = self.copy_payload()
        self.update_json(root, "themes/halo/theme.json",
                         lambda t: t["fonts"]["ui"].update(
                             small="themes/halo/fonts/ui-large.cpfont"))
        with self.assertRaisesRegex(tool.ThemeError, "distinct files"):
            tool.validate(root)

        self.update_json(root, "themes/halo/theme.json",
                         lambda t: t["fonts"]["ui"].update(
                             small="themes/halo/fonts/ui-regular.cpfont",
                             regular="themes/halo/fonts/ui-small.cpfont"))
        with self.assertRaisesRegex(tool.ThemeError, "increase from small"):
            tool.validate(root)

    def test_cpfont_duplicate_style_is_rejected(self):
        root = self.copy_payload()
        file = root / "themes/halo/fonts/ui-regular.cpfont"
        blob = bytearray(file.read_bytes())
        self.assertGreaterEqual(blob[12], 2)
        blob[64] = blob[32]
        file.write_bytes(blob)
        with self.assertRaisesRegex(tool.ThemeError, "duplicate/invalid cpfont"):
            tool.validate(root)

    def test_corrupt_bitmap_is_rejected(self):
        root = self.copy_payload()
        file = root / "themes/halo/assets/home-hero.cpb"
        blob = bytearray(file.read_bytes())
        blob[-1] ^= 0xFF
        file.write_bytes(blob)
        with self.assertRaisesRegex(tool.ThemeError, "CRC"):
            tool.validate(root)

    def test_wallpaper_only_generator(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is optional outside preview/conversion tests")
        source = self.work / "images"
        source.mkdir()
        Image.new("RGB", (12, 16), "red").save(source / "one.png")
        Image.new("RGB", (12, 16), "blue").save(source / "two.png")
        result = create(source, self.work / "output", "my-wallpapers",
                        "My Wallpapers", "Author", "0.1.0", 528, 792)
        target = Path(result["folder"])
        self.assertEqual(tool.validate(target)["bitmaps"], 2)
        theme = tool.read_json(target / "themes/wallpapers/theme.json")
        self.assertEqual(sorted(theme["regions"]), ["sleep"])
        self.assertEqual(theme["metrics"], {})
        self.assertNotIn("fonts", theme)
        self.assertTrue(Path(result["zip"]).is_file())

    def test_wallpaper_generator_rejects_existing_destination(self):
        image_dir = self.work / "empty"
        image_dir.mkdir()
        with self.assertRaisesRegex(tool.ThemeError, "at least one image"):
            create(image_dir, self.work / "out", "pack", "Title", "Author", "0.1.0", 528, 792)


if __name__ == "__main__":
    unittest.main()
