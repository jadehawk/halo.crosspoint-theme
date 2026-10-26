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

The **exact manifest fields** are `kind`, `name`, `title`, `description`, `author`, `version`, `license`, `themes`, `files`. Unknown keys are rejected by the current host validator. Versions use `MAJOR.MINOR.PATCH`, without a `v` in the manifest. A release tag may use an initial `v`. Every runtime file must be listed, including `manifest.json`, the package README and the packaged rich `DETAILS.md`. All paths are relative to the payload root, never absolute or parent-traversing; symlinks are forbidden. The installer must not copy developer files or generated previews.

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
artwork shows through every widget. The separate lower-band decoration remains
available for guaranteed visibility when there is empty space.

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
    "sleep_art": ["themes/my-style/assets/sleep-1.cpb"]
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

Artwork is referenced by named roles: `header_emblem`, `home_hero`, `boot_art`, `sleep_art`, `sleep_emblem`. A role points to `themes/<id>/assets/<filename>.cpb` or `shared/assets/<filename>.cpb`; assets must be in `files`. Only `sleep_art` may be a list (currently 1–8 images). The renderer chooses one at random per **regular sleep rendering**; repeats can occur.

When a theme needs custom UI typography, `fonts` can declare one UI **family with four raster-size variants**: `{"ui":{"small":"themes/<id>/fonts/ui-small.cpfont","regular":"themes/<id>/fonts/ui-regular.cpfont","large":"themes/<id>/fonts/ui-large.cpfont","display":"themes/<id>/fonts/display.cpfont"}}`. Each size retains its own glyph metrics, preserving the original typography across Home, Settings, Library, menus, and other UI screens. Variant-family activation uses a bounded font cache; the firmware may prewarm common UI glyphs and reclaim caches when network memory is tight. Developers must not assume glyph cache residency or force memory-intensive eager asset preloading. A single shared file (`{"ui":"themes/<id>/fonts/ui.cpfont"}`) remains supported for themes that intentionally use one raster size throughout. The legacy four-key form (`ui_small`, `ui_regular`, `ui_large`, `display`) remains compatible. All files must be listed in `manifest.files`, be v4 `.cpfont` assets within the theme's font directory, and require `theme.fonts.v1`. Both `fonts.ui` forms additionally require `theme.font-family.v1`, allowing older firmware to reject the extended format during discovery. Reader font families remain independent; theme deactivation safely restores stock UI fonts without deleting user-installed font files.

### Required font checks before publication

Font assets are **data**, not code. The validator and release workflow must reject a theme unless all of the following are true:

1. The collection declares **exactly one supported font mode**: no `fonts` (use stock fonts), legacy `ui_small/ui_regular/ui_large/display`, a single `fonts.ui` string, or a `fonts.ui` object with **exactly** `small/regular/large/display`. Never mix the modes or add unknown roles.
2. Every font lives under `themes/<id>/fonts/`, uses the exact `.cpfont` suffix, appears in `manifest.files`, is unique where the four-size family is requested, and is **64–204,800 bytes**. The entire pack remains subject to the existing 2 MiB / 64-file cap. Paths may not escape the collection, redirect through symlinks, or load external resources.
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

Current host limits: 1–16 themes/collection, up to 64 files, ≤2 MiB payload, ≤1024-pixel dimensions, ≤128 KiB per CPB bitmap, ≤8 images per sleep gallery, ≤16 operations per region and ≤48 per theme. Current X3 firmware registry also limits discovery to 8 packs, 16 choices, 64 files/pack and 12 KiB per JSON file. Limits may change as the contract evolves; loaders must enforce their own constraints.

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

A publisher must use the GitHub topic **`crosspoint-theme`**, maintain a stable non-draft, non-prerelease Release matching manifest `version`, and put only payload files in the verified `<name>-<version>.crosspoint-theme.zip`. Plugin Hub now discovers these for `community-themes.json`; stock firmware does not yet install them. See [copy/paste AI instructions](AI_AGENT_GUIDE.md) and [full publishing guide](https://github.com/crosspoint-reader/crosspoint-plugin-hub/blob/main/docs/BUILD_AND_PUBLISH_EXTENSIONS.md).

See [author instructions](CREATE_THEMES.md), [wallpaper collections](WALLPAPER_PACKS.md), [firmware compatibility](SUPPORTED_FIRMWARE.md), and [catalog filtering](CATALOG_INTEGRATION.md).
