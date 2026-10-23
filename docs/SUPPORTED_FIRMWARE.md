# Supported firmware — SD themes (capability-led)

This neutral list records **known implementations**, not endorsements, minimum fork names or guarantees that every release of a firmware supports themes.

As of **2026-10-22**, the only established theme-capable firmware is the development **Razor-Crest** fork. HALO was tested on a physical X3 and rendered on an X4 Pro; catalog integration is still undergoing device tests. Current upstream CrossPoint does **not** expose the SD theme loader. Do not assume that every tagged Razor-Crest release includes these capabilities.

| Firmware / source | Status | Verified device | Compatibility |
|---|---|---|---|
| [Razor-Crest](https://github.com/jadehawk/Razor-Crest) — SD theme integration | **On the `razor-crest` development branch; check exact build** | X3, X4 Pro (HALO UI rendered) | SD theme and standalone BMP wallpaper capabilities in source; v2 catalog installer under testing |
| [CrossPoint upstream](https://github.com/crosspoint-reader/crosspoint-reader) | Theme support not in current upstream firmware | — | Does **not** yet load SD theme packs |

**Do not interpret this table as a firmware allow-list.** A future CrossPoint fork should appear when it implements the contract, and a catalog must prefer **runtime capabilities** rather than comparing firmware names.

## Capabilities required by this HALO pack

These are declared under `themes[].requires` in `halo.crosspoint-theme/manifest.json`:

- `theme.sd.v1` — find, validate and select SD theme collections.
- `theme.metrics.v1` — apply theme metrics.
- `theme.images.v1` — draw theme CPB bitmaps.
- `theme.composition.v1` — render declarative scenes and sleep wallpapers.
- `theme.fonts.v1` — use optional UI fonts and restore stock font fallback.
- `theme.font-family.v1` — one shared UI font or four role sizes: small, regular, large, display.
- `theme.settings-navigation.v1` — apply theme's default List/Tabs preference when user has not overridden it.

For wallpaper packs, Razor-Crest also exposes **`wallpaper.packs.v1`** (named Custom sleep collection selection, BMP validation, random selection and existing timed wake refresh). The per-theme capabilities in the manifest are the **installation requirements**. A standalone BMP wallpaper pack is a separate package kind requiring `wallpaper.packs.v1`; it is not a subset of UI theme capabilities.

## Firmware surfaces / paths (not HTTP endpoints)

| Surface | Contract |
|---|---|
| Theme collection root | `/.crosspoint/themes/<id>.crosspoint-theme/` |
| Collection manifest | `manifest.json` with `kind: "theme-pack"` |
| Per-theme definition | `themes/<id>/theme.json` |
| Selection UI | **Settings → Display → UI Theme** |
| Navigation preference | **Settings → System → Settings navigation** (Follow theme / List / Tabs) |
| Fallback | Built-in Classic theme when a theme is missing or invalid |
| Plugin independence | Themes remain available independently of Plugin System toggle |

Compatible development firmware advertises theme and wallpaper capabilities in the comma-separated `pluginCapabilities` field from **`GET /api/status`** while File Transfer or Calibre Wireless service is running. The native plugin catalog receives `{plugin_capabilities}`. No dedicated theme HTTP endpoint is needed.

Catalogs must wait for an authoritative runtime capability signal before displaying/installing a theme. See [Catalog Integration](CATALOG_INTEGRATION.md). The companion machine-readable list is [`supported-firmware.json`](../supported-firmware.json).

## Tests and reporting support

A firmware should not be added to the known-compatible list based solely on an open PR. Verify actual SD discovery, theme selection, boot/home/sleep rendering, fonts, missing collection fallback, and memory behavior on a specific device. Record exact firmware build/release when available and the capabilities it exposes. Firmware-agnostic implementation is the goal.
