# AI agent: make your own CrossPoint SD theme

You can paste the block below into your AI coding assistant. The **authoritative v1 format** lives in [THEME_CONTRACT.md](THEME_CONTRACT.md) with worked steps in [CREATE_THEMES.md](CREATE_THEMES.md). HALO is a *sample*, not a required dependency.

> Act as a CrossPoint SD theme author. Read `docs/THEME_CONTRACT.md`, `docs/CREATE_THEMES.md`, `docs/SUPPORTED_FIRMWARE.md`, `docs/CATALOG_INTEGRATION.md`, and the current Python validator before touching assets. Inspect the source repo, preserve licenses and attribution, and create one direct-child `<collection-id>.crosspoint-theme/` containing `manifest.json`, an ASCII/plain-text `README.md` no larger than 2 KiB and a rich `DETAILS.md` declared in `files`, `themes/<theme-id>/theme.json`, plus only declared CPB/CPFONTS. Never generate `device.json`, `plugin.js`, arbitrary scripts or executable logic in the payload. Keep package `name` and theme IDs stable, keep `themes[].title` short and display-ready, and declare only actually needed capability identifiers. Implement styling using the exact v1 operations, text sources, regions, layout metrics and file size limits defined in the contract; do not invent firmware primitives. Run `python -m unittest discover -s tests -q`, `python tools/theme_tool.py validate --root .`, and `python tools/theme_tool.py pack --root . --output dist/<collection-id>-<version>.crosspoint-theme.zip`. Inspect the archive and the GitHub Release naming. Explain stock CrossPoint has no SD theme support and that Razor-Crest development firmware is currently the only known compatible implementation; actual compatibility is governed by `theme.*` capability tokens. Prepare a public GitHub repo with topic `crosspoint-theme` and a non-draft, non-prerelease release tag `v<version>`. Do not claim a published GitHub catalog implies stock firmware can install it. Do not commit, push, tag, or publish until the user explicitly authorizes it.

## Package contract summary

```text
mythemes.crosspoint-theme/           # repository root
  mythemes.crosspoint-theme/         # installable ZIP root
    manifest.json                     # kind: theme-pack, name, title, description,
                                      # author, version, license, themes, files
    README.md                         # plain ASCII, no Markdown/emoji, <= 2 KiB
    DETAILS.md                        # rich Markdown, declared and packaged for Plugin Hub
    themes/mytheme/theme.json         # declarative scene and metrics
    themes/mytheme/assets/*.cpb       # optional 1-bit monochrome v1 artwork
    themes/mytheme/fonts/*.cpfont     # optional v4 monochrome UI fonts
  docs/                               # developer-only
  tools/                              # Python author/validator, not installed
```

Theme entry `themes[].requires` must declare implemented primitives. Current Razor-Crest-supported capabilities are:

| Capability | Author-facing primitive |
| --- | --- |
| `theme.sd.v1` | SD theme registry, manifest validation, selector and Classic fallback |
| `theme.metrics.v1` | Bounded `ThemeMetrics` numeric/boolean overrides |
| `theme.images.v1` | CPB roles `header_emblem`, `home_hero`, `boot_art`, `sleep_art`, `sleep_emblem` |
| `theme.composition.v1` | Scene regions `header`, `home`, `boot`, `sleep`, `hints`; operations `fill`, `rect`, `bitmap`, `text`, `line`, `book-card`, `progress` |
| `theme.fonts.v1` | v4 monochrome `.cpfont` UI slots, stock font fallback |
| `theme.font-family.v1` | One shared `ui` font or four sizes: small, regular, large, display |
| `theme.settings-navigation.v1` | List/Tabs default preference; user's choice takes priority |

Style primitives: background/foreground, selection mode (`invert`, `underline`, `pill`, `triangle`), row separators, square/rounded/chamfer corners, bounded chamfer cuts, optional Settings navigation preference. Reference adaptation: `center-crop` or `scale-to-fit`. Allowed text sources: `screen_title`, `date`, `device_name`, `book_title`, `book_author`, `progress_percent`, `tagline`, `loading_percent`. Maximum 16 themes, 64 files / 2 MiB per collection, 8 sleep-art entries, 16 operations per region and 48 per theme (host validation). The [full contract](THEME_CONTRACT.md) and `theme_tool.py` are definitive about bounds.

Themes do **not** include wallpaper.packs.v1; that capability manages independent BMP Custom sleep pools and timed refresh. Theme sleep galleries apply to Dark/Light regular sleep entries only.

## Firmware compatibility / publication

| Firmware | Theme status |
| --- | --- |
| [Razor-Crest](https://github.com/jadehawk/Razor-Crest) development `razor-crest` | Known compatible SD-theme implementation, tested on X3, HALO rendering also tested on X4 Pro; verify exact build and capability tokens |
| [Upstream CrossPoint](https://github.com/crosspoint-reader/crosspoint-reader) | SD themes **not implemented** in current upstream firmware; plugin support does not imply theme support |

This is informative, **not an allowlist**. Publishing: add topic `crosspoint-theme`; pass host validator and tests; issue matching stable release `vMAJOR.MINOR.PATCH` with **`<name>-<version>.crosspoint-theme.zip`** containing exactly one validated package directory; wait for Plugin Hub's three-hour refresh (or manual dispatch). See [Plugin Hub publication guide](https://github.com/crosspoint-reader/crosspoint-plugin-hub/blob/main/docs/BUILD_AND_PUBLISH_EXTENSIONS.md). Catalog availability alone does not guarantee the currently installed firmware can consume the catalog.
