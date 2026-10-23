# Theme catalog integration (capability aware)

Plugin Hub already publishes the opt-in [v2 catalog schema](https://github.com/crosspoint-reader/crosspoint-plugin-hub/blob/main/docs/EXTENSION_CATALOG_SCHEMA.md) as:
- `catalog-lists-capabilities.json` (plugins, themes, wallpaper packs; each list has `kind`, `items`, `requires`)
- `community-themes.json` (one item per collection, `themes[].requires`, immutable ZIP `asset_url` and `sha256`)
- `community-wallpapers.json` (one item per artwork collection and screen-resolution variant)

Plugin Hub's legacy `catalog-lists.json` and plugin-only installer remain unchanged.

## Firmware status

**As of 2026-10-22, upstream CrossPoint does not yet expose an SD-theme loader or standalone wallpaper-pack loader.** [Razor-Crest](https://github.com/jadehawk/Razor-Crest) development firmware is the only known compatible implementation, and its capability-aware firmware catalog consumer is undergoing device validation. Not every release or device automatically has these features. The [known firmware table](SUPPORTED_FIRMWARE.md) is informational, not an allowlist.

Compatible firmware advertises these capabilities through `GET /api/status` -> `pluginCapabilities` and the native `{plugin_capabilities}` replacement, then filters index rows by `requires`. For each theme, it must also verify every `themes[].requires`. An unsupported firmware **must not show** the Themes catalog or install a theme under the plugin root.

The installed theme is under `/.crosspoint/themes/<collection>.crosspoint-theme/` with `manifest.json`, a plain-ASCII device README, `themes/<id>/theme.json` and declared CPB/CPFONTS. The firmware installs an immutable release ZIP after checksum/manifest/path/size checks and staged replacement, not from arbitrary repo branches. Active theme replacement/removal must not invalidate resources in use. Defaults fall back to Classic.

Themes are data, not executable plugins. Their full declared primitives are `theme.sd.v1`, `theme.metrics.v1`, `theme.images.v1`, `theme.composition.v1`, `theme.fonts.v1`, `theme.font-family.v1`, and `theme.settings-navigation.v1`. See [all regions, operations, font roles, styles and bounds](THEME_CONTRACT.md#theme-definition).

For publisher instructions and a reusable AI assistant prompt, use [AI Agent Guide](AI_AGENT_GUIDE.md). For GitHub topics, release asset naming, discovery and catalog publication requirements, see [Plugin Hub extension authoring](https://github.com/crosspoint-reader/crosspoint-plugin-hub/blob/main/docs/BUILD_AND_PUBLISH_EXTENSIONS.md). Do not invent catalog fields or create `device.json` for a theme.
