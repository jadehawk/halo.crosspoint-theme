# CrossPoint SD Theme Contract — v1 (experimental)

This document describes the **currently implemented SD-theme format** used by the Razor-Crest development firmware and the HALO theme pack. It is a **provisional community contract, not an upstream CrossPoint standard**. Other firmware implementations may adopt it by exposing the same capabilities and semantics.

A **theme** describes appearance. It does not supply executable code, register button actions, intercept input, or replace core reading/navigation behavior. The firmware renders the scene and owns all resource lifetimes and fallbacks.

## Distinguish theme collections from plugins

| Property | SD theme collection | CrossPoint plugin |
|---|---|---|
| Folder | `/.crosspoint/themes/<id>.crosspoint-theme/` | `/.crosspoint/plugins/<id>/` (or supported legacy roots) |
| Manifest | `kind: "theme-pack"` | Plugin manifest |
| UI | Declarative scene + metrics + optional bitmap/font assets | `device.json` and/or `plugin.js` |
| Actions | **Not supported** | May register supported plugin actions |
| Compatibility | `themes[].requires` capability identifiers | Plugin API / capability requirements |
| Installer | Manual folder copy today | Plugin Hub or manual installation |

**Do not invent a `device.json` or `plugin.js` for a theme.**

## Installable directory convention

Use one public GitHub repository per collection, containing **one direct-child** `<collection-id>.crosspoint-theme/` directory. This mirrors the plugin layout but uses a different folder suffix.

```text
my-themes.crosspoint-theme/                      ← GitHub repository
└── my-themes.crosspoint-theme/                  ← installable payload
    ├── manifest.json
    ├── README.md
    ├── DETAILS.md                 ← declared, packaged rich catalog description
    ├── themes/
    │   └── my-style/
    │       ├── theme.json
    │       ├── assets/
    │       │   └── sleep-1.cpb
    │       └── fonts/                            ← optional v4 CPFONT
    └── shared/assets/                            ← optional
```

The theme selector should display the publisher's short `themes[].title` directly. Keep package `title`, theme `title`, and `description` concise for small e-paper screens; do not encode branding twice. The installed payload `README.md` is presented as plain text by lightweight firmware readers: keep it printable ASCII, with no emoji, Markdown headings, or formatting markers, and ideally under 2 KiB. The richer repository-root README can remain Markdown. These display text rules are authoring guidance; firmware must not sanitize the README at runtime.

The collection ID, root folder name, manifest `name`, and theme IDs are stable identity keys. Firmware selects themes as `<collection-id>/<theme-id>`; renaming either is a breaking change. Each collection can contain multiple themes with distinct `requires`.

## Manifest

```json
{
  "kind": "theme-pack",
  "name": "my-themes",
  "title": "My Theme Collection",
  "description": "A small example collection",
  "author": "Theme Author",
  "version": "0.1.0",
  "license": "See included project attribution and license",
  "themes": [
    {
      "id": "my-style",
      "title": "My Style",
      "path": "themes/my-style/theme.json",
      "requires": [
        "theme.sd.v1",
        "theme.metrics.v1",
        "theme.images.v1",
        "theme.composition.v1"
      ]
    }
  ],
  "files": [
    "manifest.json",
    "README.md",
    "DETAILS.md",
    "themes/my-style/theme.json",
    "themes/my-style/assets/sleep-1.cpb"
  ]
}
```

The **exact manifest fields** are `kind`, `name`, `title`, `description`, `author`, `version`, `license`, `themes`, `files`. Unknown keys are rejected by the current host validator. Versions use `MAJOR.MINOR.PATCH`, without a `v` in the manifest. A release tag may use an initial `v`. Every core runtime file must be listed (the dedicated sleep gallery directory is separately scanned and verified), including `manifest.json`, the package README and the packaged rich `DETAILS.md`. All paths are relative to the payload root, never absolute or parent-traversing; symlinks are forbidden. The installer must not copy developer files or generated previews.

## Firmware capabilities currently recognized

| Capability | What it enables |
|---|---|
| `theme.sd.v1` | SD theme collection discovery, validation, selection and fallback |
| `theme.metrics.v1` | Bounded `ThemeMetrics` overrides |
| `theme.images.v1` | Validated, streamed monochrome CPB assets |
| `theme.composition.v1` | Declarative named UI rendering regions and operations |
| `theme.fonts.v1` | Four optional SD UI font roles with stock-font restoration |
| `theme.settings-navigation.v1` | Theme-preferred Settings list/tab presentation, subject to manual override |
| `theme.book-cover.v1` | Opt-in native Home thumbnail card with saved progress when available (development primitive; requires firmware support) |
| `theme.menu-decoration.v1` | Opt-in Home menu double outlines and decorative footer art drawn above button hints |
| `theme.screen-decoration.v1` | Reusable non-reading screen decoration within confirmed unused layout space; one declared, one-bit ink-only bitmap, maximum 128px tall |
| `theme.screen-background.v1` | Opt-in full-height one-bit ink-only background underlay for non-reading list and File Transfer screens, independently capability-gated |
| `theme.usb-scene.v1` | One validated full-screen opaque monochrome CPB displayed before USB Drive unmounts SD; graphics only, no SD reads or theme fonts during connection |

A minimal, firmware-agnostic declaration looks like:

```json
{
  "assets": {"screen_art": "themes/example/assets/screen-art.cpb"},
  "regions": {
    "screen": [{
      "op": "bitmap", "asset": "screen_art", "anchor": "bottom",
      "fit": "contain", "paint": "ink-only",
      "max_width": 528, "max_height": 84
    }]
  }
}
```

**Experimental full-screen underlay (opt-in):** A theme may declare a separate
`assets.screen_background_art` monochrome CPB and a single
`regions.screen_background` bitmap operation with
`paint: "ink-only"`, `fit: "contain"`, and `max_height` 1–1024.
The theme must additionally require `theme.screen-background.v1`. The
firmware draws this beneath the native list/File Transfer UI immediately
after clearing the buffer; it never alters button hitboxes or reading pages.
Native widgets may erase portions of the artwork as they draw opaque regions.
Keep the center nearly empty and use this primarily for corner/edge details.
This capability is an early hardware-testing primitive, not a guarantee that
artwork shows through every widget. At runtime, the firmware draws the full-height
underlay **only when physically installed PSRAM is available**; X3/X4-class
boards without PSRAM silently skip it for performance. The theme remains
installable and the declared firmware capability remains independent of device
memory. Do not list PSRAM or a firmware brand as a theme installation requirement.
The separate lower-band decoration remains available without PSRAM wherever the
native layout has confirmed spare space; Library position/status text and button
hints are always excluded from that band.

**USB Drive scene (opt-in):** Add a scalar `assets.usb_art` path pointing to a declared and CRC-validated `.cpb` asset and a single `regions.usb` operation: `{"op":"bitmap","asset":"usb_art","fit":"contain"}`. Add `theme.usb-scene.v1` to the selected theme's `manifest.themes[].requires`. The firmware draws the image once into its ordinary e-ink framebuffer before handing the SD card to the PC. The connected state intentionally contains no text, actions or translating strings. Missing art uses the firmware's transfer icon. Disconnect reboots directly into Home; other USB error handling stays native. Author separate 528×792 and 480×800 versions in their respective published resolution-specific ZIPs. Do not mix `theme.screen-decoration.v1` lower-band graphics with this full-page USB scene.

**Native grayscale USB art:** Retain `assets.usb_art` and the existing single-bitmap `regions.usb` as the firmware fallback. Add `assets.usb_gray_art` referencing a valid, declared 8-bit, four-tone (0, 85, 170, 255) grayscale BMP sized exactly for the target display, plus `theme.usb-grayscale.v1` in `manifest.themes[].requires`. The USB screen renders the gray planes fully before relinquishing the SD card to the PC. Include `usb-connected.bmp` (528×792 X3) or `usb-connected-touch.bmp` (480×800 X4+) in the matching release ZIP; never install both variants together.

**Device-sized ZIP variants (new publisher contract):** A theme author may retain both X3 and larger-display images in the source repository, but should publish one installable ZIP per target resolution. Each variant must contain a `target_resolution: {width, height}` manifest field, the same stable `name` and theme ID, and only CPBs for that resolution. Use filenames `<name>-x3-<version>.crosspoint-theme.zip` (528×792) and `<name>-x4plus-<version>.crosspoint-theme.zip` (480×800), both attached to one GitHub Release. Both archives must unpack under `<name>.crosspoint-theme/`, regardless of ZIP filename. Cantina groups these into one theme selection and firmware chooses by measured panel size, validating ZIP digest and matching manifest resolution. Theme version and installed settings identity remain stable. Do not package the unused device's images. The old paired asset conventions are authoring-time inputs, not required for runtime packages.\n\n**Paired-resolution bitmap assets:** Every scene bitmap role may have an optional `<role>_touch` asset in `assets`, referencing a separately authored `.cpb`. For example `header_emblem` / `header_emblem_touch`, `home_hero` / `home_hero_touch`, `boot_art` / `boot_art_touch`, and `sleep_art` / `sleep_art_touch`. Firmware selects the alternate asset when a device exposes touch or uses the matching 480 × 800 portrait canvas, when that role's variant exists; otherwise it uses the base image. Back-arrow display remains touch-only. Keep native text, row actions, and interactive controls in firmware. All variants must be explicitly declared in `manifest.files`, pass normal CPB bounds/CRC validation, and retain the base asset. The higher-resolution images should be composed at their target canvas rather than enlarging the X3 package bitmap. This is a capability-based design, not a hard-coded firmware name requirement.

**Touch Back icon style:** With the `theme.header-back.v1` capability, `styles.header_back_style` may be `arrow`, `emblem`, or `both`. `arrow` draws the firmware-owned arrow and suppresses the theme header emblem only on pushed touch screens; `emblem` keeps the historical emblem-only Back affordance; `both` draws the arrow first, then the emblem and shifted title without overlap. Button-device and root Home headers retain their original layout. All Back taps are routed through the existing firmware-owned input/hitbox; the theme does not implement actions. If this style is omitted, the historical emblem-only behavior remains.

**Optional taller touch-panel footer art:** A theme already using `theme.menu-decoration.v1` may add `assets.home_footer_touch` and `styles.menu_footer_touch_asset: "home_footer_touch"` alongside the normal `home_footer`. Firmware uses the original 46px Home footer on button devices and selects the taller art (up to 112px, constrained by free space) on touch panels. Similarly, `theme.screen-decoration.v1` themes may declare `assets.screen_touch_art` alongside `screen_art`; touch panels select that bitmap in the same lower safe-band region (maximum 128px), while button devices retain `screen_art`. These are optional variants of existing capabilities, not firmware-specific requirements. The original footer asset remains mandatory whenever its touch variant is declared. Full-screen underlays are clipped above a reserved footer band when both are displayed; text and input remain native.

**Non-reading screen decoration (opt-in):** declare `theme.screen-decoration.v1` in the theme's `requires`, a scalar `assets.screen_art` CPB path, and exactly one `regions.screen` bitmap operation using `paint: "ink-only"`, `anchor: "bottom"`, and `max_height` from 1 through 128. The firmware renders that decoration *after* native content and only when a lower content band is provably empty. This is reused across short Settings, Library, and Plugin-list screens and, where QR codes leave room, File Transfer. Long/scrolled lists, the Reader, Home and sleep screens do not receive a forced overlay. Themes must keep a white center and avoid fake buttons; actual text, controls, focus, selection and input stay firmware-owned. Older firmware rejects the new capability. This is **not** an arbitrary full-page wallpaper behind text.


These strings are recognized by **ThemePackRegistry** and advertised by compatible development firmware through `GET /api/status` → `pluginCapabilities` and native `{plugin_capabilities}` substitution. They remain a provisional community contract, not an upstream CrossPoint API. Catalogs should only claim runtime support after firmware advertises these values externally. Do not use the string `Razor-Crest` or version `2.0.0` as a substitute for capability negotiation.

## Theme definition

Each `themes/<id>/theme.json` has exact required fields:
`schema_version`, `base`, `reference`, `metrics`, `styles`, `assets`, `regions`; optional `fonts`.

```json
{
  "schema_version": 1,
  "base": "classic",
  "reference": { "width": 528, "height": 792, "adapt": "scale-to-fit" },
  "metrics": {},
  "styles": {
    "header_background": "white",
    "header_foreground": "black",
    "selection": "invert",
    "row_separators": false,
    "corners": "square",
    "chamfer_cut": 0
  },
  "assets": {
    "sleep_art": "themes/my-style/sleep"
  },
  "regions": {
    "sleep": [
      { "op": "fill", "color": "white" },
      { "op": "bitmap", "asset": "sleep_art", "anchor": "center", "fit": "native" }
    ]
  }
}
```

For **standalone Custom sleep wallpaper packs**, use the separate `wallpaper.packs.v1` BMP format; it preserves the currently selected UI theme. A UI theme with only a `sleep` region is still possible, but its other regions use **Classic**, not the previously selected theme.

### Reference and adaptation

The design reference is a bounded width/height (X3 reference is 528×792). The implemented `adapt` enum is `center-crop` or `scale-to-fit`. Confirm rendering on each target panel; a reference size does not guarantee pixel-perfect conversion on every device.

### Metrics and styling

`metrics` permits only known `ThemeMetrics` names, with bounded numeric and boolean values; the [validator](../tools/theme_tool.py) contains the current exact allow-list. Absent metrics take Classic defaults.

Required `styles`: `header_background` (`black|white`), `header_foreground` (`black|white`), `selection` (`invert|underline|pill|triangle`), `row_separators` (boolean), `corners` (`square|rounded|chamfer`), `chamfer_cut` (0–32).

Optional:
- `chamfer_card_cut`, `chamfer_row_cut`, `chamfer_hint_cut` (0–32): book-card, selected-menu, and button-hint corner cuts; inherit `chamfer_cut` when omitted.
- `settings_navigation: "list" | "tabs"`: a preference only, and requires `theme.settings-navigation.v1`. If no user override exists, the firmware follows the theme; otherwise the user's **List/Tabs** choice wins. If absent, List is the fallback. Tabs presents Display, Reader, Controls, System, with Library/Connectivity expandable under System.

### Assets and fonts

Artwork is referenced by named roles: `header_emblem`, `home_hero`, `boot_art`, `sleep_art`, `sleep_emblem`. Standard image roles point to `themes/<id>/assets/<filename>.cpb` or `shared/assets/<filename>.cpb` and appear in `manifest.files`. The **sleep_art** role instead uses a dedicated directory: `"sleep_art": "themes/<id>/sleep"`. Put any number of verified 1-bit CPBs in that folder, bounded only by the installer’s 32 MiB ZIP / 64 MiB expanded budget. Sleep files must be direct children (no nested directories); filenames and CRCs are checked. They do **not** appear individually in `manifest.files`, which lists only core files. The firmware counts candidates by scanning the directory on SD and selects one without holding all filenames in RAM. Theme sleep rotation advertises `theme.sleep-gallery.v1` and is independent of Custom wallpaper pools. Device-specific ZIPs each ship one dedicated sleep directory. Consecutive duplicates are avoided within a loaded scene; after reboot a repeat is possible.

When a theme needs custom UI typography, `fonts` can declare one UI **family with four raster-size variants**: `{"ui":{"small":"themes/<id>/fonts/ui-small.cpfont","regular":"themes/<id>/fonts/ui-regular.cpfont","large":"themes/<id>/fonts/ui-large.cpfont","display":"themes/<id>/fonts/display.cpfont"}}`. Each size retains its own glyph metrics, preserving the original typography across Home, Settings, Library, menus, and other UI screens. Variant-family activation uses a bounded font cache; the firmware may prewarm common UI glyphs and reclaim caches when network memory is tight. Developers must not assume glyph cache residency or force memory-intensive eager asset preloading. A single shared file (`{"ui":"themes/<id>/fonts/ui.cpfont"}`) remains supported for themes that intentionally use one raster size throughout. The legacy four-key form (`ui_small`, `ui_regular`, `ui_large`, `display`) remains compatible. All files must be listed in `manifest.files`, be v4 `.cpfont` assets within the theme's font directory, and require `theme.fonts.v1`. Both `fonts.ui` forms additionally require `theme.font-family.v1`, allowing older firmware to reject the extended format during discovery. Reader font families remain independent; theme deactivation safely restores stock UI fonts without deleting user-installed font files.

### Required font checks before publication

Font assets are **data**, not code. The validator and release workflow must reject a theme unless all of the following are true:

1. The collection declares **exactly one supported font mode**: no `fonts` (use stock fonts), legacy `ui_small/ui_regular/ui_large/display`, a single `fonts.ui` string, or a `fonts.ui` object with **exactly** `small/regular/large/display`. Never mix the modes or add unknown roles.
2. Every font lives under `themes/<id>/fonts/`, uses the exact `.cpfont` suffix, appears in `manifest.files`, is unique where the four-size family is requested, and is **64–204,800 bytes**. The declared core files remain bounded to 64; sleep CPBs are separately bounded by the archive byte limits. Paths may not escape the collection, redirect through symlinks, or load external resources.
3. Each font is a monochrome `.cpfont` **v4** with the correct eight-byte signature and 1–4 nonduplicate style IDs, including regular style 0. No 2-bit grayscale, kerning, or ligature tables in theme fonts. Every Unicode interval must be sorted, nonoverlapping, and map exactly onto the declared glyph count; glyph entries must have valid packed bitmap lengths and lie wholly inside the file's own style section.
4. The modern `fonts.ui` modes require **both** `theme.fonts.v1` and `theme.font-family.v1`; the legacy four-role mode requires `theme.fonts.v1` only. Firmware compatibility is determined by capabilities, **never by a branded firmware name**. When a four-size UI family is declared, the four files must be distinct and their regular-style line heights must strictly ascend: `small < regular < large < display`.
5. Theme fonts affect **UI chrome only**, never the book-reading font or user-selected reader font. Theme activation must revert to stock fonts on failure, and deactivation must not remove reader-owned fonts. Do not depend on theme-specific firmware patches or native executable plugins.

**Publication gate:** run `python -m unittest discover -s tests -q`, `python tools/theme_tool.py validate --root .`, and `python tools/theme_tool.py pack --root . --output dist/theme.crosspoint-theme.zip` successfully. The repository's GitHub validation workflow runs these checks on PRs, `main`, and `v*` tags and produces a verified ZIP artifact for matching release tags. **Only promote that verified tag artifact to a public release or catalog**; never upload a hand-assembled or unvalidated ZIP. Hardware review for every targeted display remains required for usability, clipping, memory, and touch tests; host validation cannot prove a theme looks right.

**Device defense:** firmware checks the manifest capability list, resource path, basic header/size and font-load constraints, and preserves the stock theme as fallback. The firmware currently does **not** exhaustively scan every glyph bitmap before a theme becomes selectable: it validates glyph entries when used. The host validator is intentionally stricter and is the pre-distribution enforcement point. Catalog maintainers must run the same validator on third-party submissions; a workflow in the Halo repo does not automatically protect other repositories.

### Declarative scene regions and operations

Regions: `header`, `home`, `boot`, `sleep`, `hints`. Current operations are `fill`, `rect`, `bitmap`, `text`, `line`, `book-card`, and `progress`. Ops accept only documented fields; the [host validator](../tools/theme_tool.py) is the detailed operation-property reference.

The `header` scene also renders on touch devices, including Settings, Library, and Plugin Catalog. Firmware owns the battery display and navigation actions. On pushed screens the leading **58-pixel header area is a Back touch target**, so theme authors should put a recognizable emblem or Back affordance there; Home does not have this Back target. Firmware preserves native trailing actions such as Library Search and Rebuild over the themed header. Avoid placing essential title artwork in those action areas.

- `fill`: fill region white or black.
- `rect`: anchored bounded solid rectangle (width/height 0 fills that dimension).
- `bitmap`: asset role with fit `native|contain|cover` and optional `ink-only` masking.
- `text`: a literal `value` or firmware-owned `source`, font role, spacing, and optional chamfered dark/light plate.
- `line`: horizontal or vertical rule.
- `book-card`: firmware-owned Continue Reading information; classic `outlined`/`filled` strip may reference an emblem. Optional `variant: "cover"` is a Home-only, firmware-rendered 166px card showing the current book thumbnail, title, author, and authentic saved progress bar/percentage when known. The cover variant cannot use `badge_asset`, requires `theme.book-cover.v1`, and does not replace any reader/menu input. Allow enough Home scene height beneath the art to avoid overlap. Firmware without this capability must reject the theme rather than silently lose its cover.
- `progress`: bounded firmware-provided progress value.

Text sources are restricted to `screen_title`, `date`, `device_name`, `book_title`, `book_author`, `progress_percent`, `tagline`, `loading_percent`. No arbitrary data lookup, shell, JavaScript, plugin callbacks, gesture bindings, or network access.

Scene operations are clipped to their region and preserve firmware-owned hitboxes. If an unsupported scene/capability fails validation, the firmware should reject it and safely fall back to Classic.

## Binary formats and bounds

**CPB v1**: 20-byte little-endian header, `CPTB` magic, version 1, flags 1, width/height, stride `ceil(width/8)`, payload length and CRC32, followed by 1-bit MSB-first scanlines (1=ink). The host tool converts RGB input to monochrome and validates the CRC.

**CPFONTS**: existing CrossPoint v4, 1-bit glyphs with bounded style tables and bitmap sections (max 200 KiB per file). These are UI-font resources, not book-font selections.

Current host limits: 1–16 themes/collection, up to 64 declared core files, ≤64 MiB expanded payload, ≤1024-pixel dimensions, ≤128 KiB per CPB bitmap, arbitrary sleep directory length within byte budgets, ≤16 operations per region and ≤48 per theme. Current X3 firmware registry also limits discovery to 8 packs, 16 choices, 64 files/pack and 12 KiB per JSON file. Limits may change as the contract evolves; loaders must enforce their own constraints.

## Sleep-screen priority and known limitations

- **Dark/Light** + a selected theme sleep scene: draw the theme's sleep gallery with overlays.
- **Dark/Light** without theme scene: built-in white/black CrossPoint logo screen.
- **Custom**: use `/.sleep` and `/sleep` regular wallpaper pool.
- **Cover/transparent modes**: retain their own firmware selection behavior.
- **Timed sleep-screen refresh**: still uses the ordinary SD wallpaper pool and **does not** rotate a theme's gallery during timed wakes.

A theme cannot pick a named `/.sleep` subcollection, invoke a plugin, or replace reader functionality. Firmware with the v2 capability-aware catalog consumer can install/update theme packs independently of the plugin-bundle installer; stock CrossPoint does not yet implement this.

## Author workflow and distribution

```powershell
python tools/theme_tool.py validate --root .
python -m unittest discover -s tests -q
python tools/theme_tool.py pack --root . --output dist/my-themes-0.1.0.crosspoint-theme.zip
```

A publisher uses the GitHub topic **`crosspoint-theme`** and one stable Release
matching manifest version. Attach both verified resolution-specific ZIP assets,
for example `<name>-x3-<version>.crosspoint-theme.zip` and
`<name>-x4plus-<version>.crosspoint-theme.zip`. Both retain the same internal
`<name>.crosspoint-theme/` directory, manifest name, theme IDs and version,
but declare their own `target_resolution` and package only their own image
set. The Cantina Store publishes one theme listing with resolution-scoped
`variants[]`; compatible firmware downloads exactly one matching ZIP.


See [author instructions](CREATE_THEMES.md), [wallpaper collections](WALLPAPER_PACKS.md), [firmware compatibility](SUPPORTED_FIRMWARE.md), and [catalog filtering](CATALOG_INTEGRATION.md).
