# Create a CrossPoint SD theme

This guide describes the experimental **declarative** theme system. It is not an upstream firmware API guarantee. Read the [Theme Contract](THEME_CONTRACT.md) for field-level constraints and [Supported Firmware](SUPPORTED_FIRMWARE.md) before sharing a collection.

## 1. Choose the theme's scope

- **Standalone Custom sleep wallpaper pack**: use the independent BMP collection contract. It preserves the active UI theme. See [wallpaper packs vs theme galleries](WALLPAPER_PACKS.md). A theme may still supply an internal Dark/Light `sleep_art` gallery.
- **UI restyle**: override bounded `metrics` and `styles` and add composition regions for `header`, `home`, `boot`, `sleep`.
- **Fonts**: optionally bundle four `cpfont` v4 UI font roles. These are not reader/book font settings.
- **Collection**: bundle one or more themes in the same pack, each with its own ID and `requires`.

Themes only describe **appearance and layout**. They cannot handle button events, define plugin actions, access network services, or modify the reader's navigation logic. Those belong to firmware/plugins.

## 2. Prepare a standalone repository

```text
my-theme.crosspoint-theme/
├── my-theme.crosspoint-theme/
│   ├── manifest.json
│   ├── README.md
│   └── themes/
│       └── my-theme/
│           ├── theme.json
│           └── assets/
│               └── home.cpb
├── docs/                           ← source docs, not installed
├── tools/                          ← developer tooling, not installed
└── README.md
```

Use lowercase letters, numbers and hyphens in collection and theme IDs. Every referenced asset belongs to the theme directory or a declared shared directory, and every runtime file must be enumerated in the manifest. Do not add `device.json` or `plugin.js`.

## 3. Convert images

Requires Python 3.10+ and Pillow for conversions (`python -m pip install Pillow`).

```powershell
python tools/theme_tool.py convert --input "cover.png" --output "my-theme.crosspoint-theme/themes/my-theme/assets/cover.cpb" --width 528 --height 400 --fit cover --dither fs
```

CPB is **one-bit monochrome**, 1=black pixel, streamed row by row by firmware. Inputs may be color/gray; conversion dithers them. Supported fits: `contain` or `cover`. The X3 reference is 528×792; artwork and UI composition need testing on each device resolution. Do not assume PNG/JPEG files can be listed directly in a theme manifest.

## 4. Create the manifest

The [Theme Contract](THEME_CONTRACT.md#manifest) gives the exact JSON structure, capabilities and required file list. `manifest.json` names the collection, included themes, semver, author, and license/attribution. Each `themes/<id>/theme.json` defines `base: "classic"`, the 528×792 reference, metrics, styles, assets, and regions.

At minimum, declare `theme.sd.v1` and `theme.metrics.v1`. If you use CPB images also declare `theme.images.v1` and `theme.composition.v1`. Optional UI fonts and Settings-tab preferences require their respective capabilities. The host validator rejects inconsistent capability declarations.

## 5. Validate, preview and package

```powershell
python tools/theme_tool.py validate --root .
python -m unittest discover -s tests -q
python tools/theme_tool.py pack --root . --output dist/my-theme-0.1.0.crosspoint-theme.zip
python tools/theme_tool.py preview --input "my-theme.crosspoint-theme/themes/my-theme/assets/cover.cpb" --output dist/preview.png
```

The ZIP contains only the declared payload folder, not repo development files. The packer uses deterministic timestamps/order.

## 6. Hardware test and publish

Copy the extracted `<id>.crosspoint-theme` folder to `/.crosspoint/themes/` on the SD card. Reboot, select it under **Settings → Display → UI Theme**, verify appearance, switching back to Classic, sleep precedence and theme removal/renaming recovery.

Create a public GitHub repository, topic `crosspoint-theme`, and a stable release tag matching `manifest.version` (e.g. `v0.1.0`). A catalog may discover such repositories **in future**, but current Plugin Hub has no production Community Themes catalog yet.

See [Catalog Integration](CATALOG_INTEGRATION.md) for how a compatible future host should filter the catalog by firmware capabilities. Do not claim general CrossPoint support until tested.
