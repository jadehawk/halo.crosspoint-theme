# Theme catalog discovery and conditional visibility — proposed

This document is intentionally **firmware-neutral**. The current production Plugin Hub exposes **Community Plugins**, but does **not** yet have a production Themes catalog or automatic theme installer. Nothing in this repository makes Plugin Hub discover themes today.

## Publishing convention (analogous to standalone plugins)

1. One **public** GitHub repository per installable theme collection.
2. Exactly one direct child `<collection-id>.crosspoint-theme/` containing `manifest.json`, `README.md`, and all declared runtime assets.
3. Repository topic `crosspoint-theme`.
4. Non-draft, non-prerelease GitHub Release, tag matching manifest version (`v0.1.0` or `0.1.0`).
5. Package asset containing **only** the installable collection folder; no scripts, tests, docs, or developer artifacts.

Catalog publishing should derive an immutable URL from the release, validate the manifest, verify `files` against the asset, check duplicates, and preserve stable collection identity. This resembles the Plugin Hub convention but must be a separate theme kind so it cannot be installed under a plugin root.

## Hide Themes entirely on unsupported firmware

**Yes, it is possible, and preferable.** The catalog UI should first inspect **runtime capability advertisement**:

```text
if firmware advertises theme.sd.v1 and theme.metrics.v1:
    show the Themes catalog entry
    for each theme:
        show/enable only when every themes[].requires capability is present
else:
    do not render the Themes catalog entry at all
```

A theme gallery containing CPB artwork additionally needs `theme.images.v1` and `theme.composition.v1`; font-bearing themes need `theme.fonts.v1`. Catalog installation requires a firmware-supported theme installation operation/root, **not the existing plugin installer**.

A **Razor-Crest name check is not a substitute** for advertised capability support. Unsupported firmware should never show an install button that will write theme files into `/.crosspoint/plugins`.

## Current integration gap

The Razor-Crest development branch **advertises theme and wallpaper capabilities** through `GET /api/status` → `pluginCapabilities` and the existing native `{plugin_capabilities}` substitutions. A new HTTP endpoint is not needed. Plugin Hub's existing catalog views do not yet define a complete `kind: theme-pack` installer.

Thus a neutral data file (see [`supported-firmware.json`](../supported-firmware.json)) can record known implementations today, but it cannot on its own make visibility conditional in existing Plugin Hub.

Recommended next integration, when implementing Community Themes:

- Expose theme capabilities through an authoritative firmware capabilities response (ideally extend the existing capability mechanism; avoid an additional redundant endpoint).
- Let the Plugin Hub UI conditionally register/show **Community Themes** only when that capability is present.
- Apply per-theme `requires` filtering for selection/install.
- Add a **theme-specific, validated installation path** with staging/replacement/rollback; keep plugin installations independent.
- Hide unsupported catalog types entirely, and ensure manually sideloaded unsupported packs cannot crash the UI.
- Keep the neutral known-firmware list informative, never an allow-list preventing additional compatible forks.

**Proposed catalog gating contract, not a JSON schema already understood by current Plugin Hub:**

```json
{
  "catalog_kind": "themes",
  "title": "Community Themes",
  "visible_requires": ["theme.sd.v1", "theme.metrics.v1"],
  "install_kind": "theme-pack"
}
```

The real catalog implementation must negotiate capabilities with the firmware and validate theme payloads; do not copy these illustrative keys into existing `device.json` or plugin catalog JSON expecting them to work today.
