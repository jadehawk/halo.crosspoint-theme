"""Resolution-scoped HALO releases share one stable theme identity."""
import json
import tempfile
import unittest
import zipfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import theme_tool
from pack_theme_variants import FULL_WIDTH, PREFIX, PROFILES, packages


class VariantPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.archives = packages(ROOT, Path(cls.temp.name) / "out")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_theme_id_manifest_and_artwork(self):
        source = ROOT / "halo.crosspoint-theme"
        original = theme_tool.read_json(source / "manifest.json")
        self.assertEqual(len(self.archives), 2)
        for variant, (width, height) in PROFILES.items():
            with self.subTest(variant=variant):
                archive_path = next(path for path in self.archives if f"-{variant}-" in path.name)
                with zipfile.ZipFile(archive_path) as archive:
                    manifest = json.loads(archive.read(PREFIX + "manifest.json"))
                    scene = json.loads(archive.read(PREFIX + "themes/halo/theme.json"))
                    self.assertEqual(manifest["name"], "halo")
                    self.assertEqual(manifest["author"], "Jadehawk + IOSDEC")
                    self.assertEqual(manifest["version"], original["version"])
                    self.assertEqual(manifest["target_resolution"], {"width": width, "height": height})
                    self.assertEqual((scene["reference"]["width"], scene["reference"]["height"]), (width, height))
                    self.assertEqual(set(archive.namelist()),
                                     {PREFIX + item for item in manifest["files"]} |
                                     {n for n in archive.namelist() if "/sleep/" in n})
                    self.assertEqual(len(manifest["files"]), 13)
                    self.assertEqual(scene["assets"]["sleep_art"], "themes/halo/sleep")
                    self.assertEqual(len([n for n in archive.namelist() if "/sleep/" in n]), 3)
                    for item in manifest["files"]:
                        if not item.endswith(".cpb"):
                            continue
                        payload = archive.read(PREFIX + item)
                        w, h, unused = theme_tool.decode_cpb(payload)
                        if Path(item).name in FULL_WIDTH:
                            self.assertEqual(w, width)
                            self.assertEqual(h, height if h >= 792 else 400)
                            if variant == "x3":
                                self.assertEqual(payload, (source / item).read_bytes())
                        else:
                            self.assertEqual(payload, (source / item).read_bytes())

    def test_each_archive_validates_independently(self):
        with tempfile.TemporaryDirectory() as temp:
            for archive_path in self.archives:
                location = Path(temp) / archive_path.stem
                with zipfile.ZipFile(archive_path) as archive:
                    archive.extractall(location)
                summary = theme_tool.validate(location)
                self.assertEqual(summary["name"], "halo")
                self.assertEqual(summary["themes"], 1)

    def test_reproducible_release_zips(self):
        first_bytes = [p.read_bytes() for p in self.archives]
        outputs = packages(ROOT, Path(self.temp.name) / "rebuild")
        self.assertEqual(first_bytes, [p.read_bytes() for p in outputs])


if __name__ == "__main__":
    unittest.main()
