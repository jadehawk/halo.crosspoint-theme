# HALO — CrossPoint Theme Collection

A complete **SD-loaded theme collection** for CrossPoint-based e-readers. This repository uses the standalone publishing layout familiar from CrossPoint plugins, but it is a **theme pack, not an executable plugin**.

> **Credit and inspiration:** This project is **100% inspired by the beautiful HALO firmware created by [iosdec](https://github.com/iosdec/crosspoint-halo)**. All credit for the original design, artwork treatment, typography, and overall HALO aesthetic goes to iosdec. See the [original HALO firmware release](https://github.com/iosdec/crosspoint-halo/releases/tag/v2.0.0rc-halo1). This collection adapts that experience to the separate, declarative SD-theme system.
>
> This is an unofficial fan-made HALO-themed project, not affiliated with or endorsed by Microsoft, Xbox, Halo Studios, iosdec, or the CrossPoint core maintainers. Trademarks and third-party media retain their respective owners' rights. See [Attribution](docs/ATTRIBUTION.md).

**Build your own theme with an AI assistant:** [AI Agent Guide](docs/AI_AGENT_GUIDE.md) | [Complete theme contract and primitives](docs/THEME_CONTRACT.md) | [Known compatible firmware](docs/SUPPORTED_FIRMWARE.md) | [Plugin Hub publishing](https://github.com/crosspoint-reader/crosspoint-plugin-hub/blob/main/docs/BUILD_AND_PUBLISH_EXTENSIONS.md).

**Firmware support:** stock upstream CrossPoint does **not** yet implement SD theme packs. The only established theme-capable firmware currently is the development `razor-crest` branch of [Razor-Crest](https://github.com/jadehawk/Razor-Crest), gated by advertised `theme.*` capabilities, not its name.

## What it includes

- HALO-inspired home wallpaper, date and tagline, themed Continue Reading card, menu rows, black UNSC header, boot art, and chamfered button hints.
- Three monochrome **sleep wallpapers bundled inside the theme**; each regular sleep transition picks a random image and draws theme overlays.
- Four **Chakra Petch UI font slots** (8/10/12/18 display sizes, including available bold styles). Book-reading fonts remain independently configurable.
- Theme-defined layout metrics, shared styling, and a **Settings navigation preference** (the shipped HALO pack prefers **List**, while a user can override it to Tabs).
- Theme artwork stored as bounded **`.cpb`** files and UI fonts as **`.cpfont`**. No script or plugin execution.

## Installation — compatible firmware required

**Stock CrossPoint does not currently support SD theme packs.** The theme renderer is under development in the [Razor-Crest](https://github.com/jadehawk/Razor-Crest) fork, initially verified on X3. Consult the neutral [supported-firmware list](docs/SUPPORTED_FIRMWARE.md) for the exact status and required capabilities; don't assume a public release contains them yet.

1. Obtain a firmware build exposing all [required theme capabilities](docs/SUPPORTED_FIRMWARE.md).
2. Copy the entire **`halo.crosspoint-theme`** folder from this repository into the SD card's `/.crosspoint/themes/` directory.
3. Confirm the resulting path is **`/.crosspoint/themes/halo.crosspoint-theme/manifest.json`** (not a second nested directory).
4. Reboot, open **Settings → Display → UI Theme**, and select **HALO**. Classic remains the firmware fallback.
5. To see HALO's rotating sleep gallery, select **Dark** or **Light** under Sleep Screen. A user-selected Custom or Cover sleep mode takes precedence.

The repository ZIP and release archive are different: the **release asset** `halo-x3-0.1.5.crosspoint-theme.zip` or `halo-x4plus-0.1.5.crosspoint-theme.zip` contains the installable folder only. Extract it onto your computer or SD card; placing the ZIP itself under `/.crosspoint/themes/` does not install the collection. Automatic installation through the capability-aware Plugin Hub catalog requires compatible firmware; otherwise use manual installation.

## Repository layout

```text
halo.crosspoint-theme/                    ← public GitHub repository
├── halo.crosspoint-theme/                ← only installable payload
│   ├── manifest.json                     ← theme-pack metadata, capabilities and files
│   ├── README.md
│   ├── DETAILS.md                   ← catalog-rich information; included in ZIP
│   └── themes/halo/
│       ├── theme.json                    ← appearance, layout and sleep scene
│       ├── assets/                       ← 7 .cpb bitmaps, including 3 sleep images
│       └── fonts/                        ← 4 .cpfont UI font files
├── docs/
│   ├── THEME_CONTRACT.md                 ← developer-facing format and capability contract
│   ├── CREATE_THEMES.md                  ← how to author other theme collections
│   ├── WALLPAPER_PACKS.md                ← wallpaper-focused theme collections
│   ├── SUPPORTED_FIRMWARE.md             ← neutral list of known implementations
│   ├── CATALOG_INTEGRATION.md            ← published v2 catalog and capability gating
│   └── ATTRIBUTION.md
├── tools/
│   ├── theme_tool.py                     ← validate / convert / preview / pack
├── tests/                                ← development validation, never installed
├── supported-firmware.json               ← catalog-friendly compatibility metadata
└── README.md
```

**Themes are not plugins.** A theme collection does not provide `plugin.js`, `device.json` or button actions. The firmware owns input, navigation, drawing and validation. All paths in the payload manifest are package-relative, and only those files are installed.

## What creators can do today

Create collections with one or more themes; customize bounded layout metrics, fonts, header, home, boot, and sleep compositions, monochrome artwork, text plates, row separators, corner cuts, and Settings list/tab preference. Multiple images in the `sleep_art` role give a **random** sleep image on each regular sleep entry (repeats are possible).

**For sleep wallpapers only, use a standalone BMP wallpaper pack instead of a UI theme.** Wallpaper packs do not change the selected UI theme and require no CPB conversion. The theme's Dark/Light gallery remains separate. See [wallpaper packs vs theme galleries](docs/WALLPAPER_PACKS.md).

### Current limits

- Monochrome CPB bitmaps only; no animated wallpaper, arbitrary scripting, user-defined hitboxes or plugin behavior.
- The active theme requires capability matching. Most community/stock firmware builds cannot load it today.
- The built-in Classic theme remains the fallback; a theme **cannot replace firmware functionality**.
- Sleep galleries currently have **up to 24 images** per theme. They are selected at regular sleep entry in Dark/Light modes; **timed sleep refresh still reads `/.sleep` and `/sleep`**, not theme assets.
- Custom sleep-wallpaper modes use the normal SD pool, not the theme gallery.
- The UI font loader has constrained sizes and bounded memory/cache behavior. Reader book fonts are not replaced.
- Theme catalog installation requires firmware implementing the capability-aware extension catalog; not every firmware exposes that consumer yet.
- Current images and layout were verified on X3; other devices need independent testing and may differ.

## Build and validate your collection (Python 3.10+)

```powershell
python -m unittest discover -s tests -q
python tools/theme_tool.py validate --root .
python tools/theme_tool.py pack --root . --output dist/halo-x3-0.1.5.crosspoint-theme.zip
python tools/theme_tool.py preview --input halo.crosspoint-theme/themes/halo/assets/home-hero.cpb --output dist/home-preview.png
```

The validator and packer use Python's standard library. Image conversion/preview requires Pillow:

```powershell
python -m pip install Pillow
python tools/theme_tool.py convert --input "my-image.png" --output "my-art.cpb" --width 528 --height 792 --fit cover --dither fs
```

See [the developer contract](docs/THEME_CONTRACT.md), [theme authoring guide](docs/CREATE_THEMES.md), and [wallpaper pack and theme gallery differences](docs/WALLPAPER_PACKS.md).

## Publishing and Plugin Hub

Use a **public GitHub repository**, one directly nested `<collection-id>.crosspoint-theme/` payload folder, topic **`crosspoint-theme`**, and a non-draft GitHub Release with a tag matching the manifest version (e.g. `v0.1.0`). This follows the standalone-plugin *publishing convention*, and capability-aware Plugin Hub catalogs discover themes. Installation still requires a compatible firmware consumer.

Theme catalogs must be hidden on firmware that does **not advertise theme support**, not merely when its product/version name is absent from a list. See [catalog integration](docs/CATALOG_INTEGRATION.md).

## Acknowledgments

**iosdec** — original HALO firmware author and designer. [Original release](https://github.com/iosdec/crosspoint-halo/releases/tag/v2.0.0rc-halo1). This project is a port/inspiration, not a claim of original authorship of the HALO visual concept.

CrossPoint and FreeInk maintainers — platform and underlying reader/graphics infrastructure.
