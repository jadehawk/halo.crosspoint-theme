# Changelog

## 0.1.5 — Device-specific theme release packages

- Publish independent 528 × 792 X3 and 480 × 800 X4+ HALO theme ZIPs under one stable `halo` identity.
- Keep the original X3 binary artwork and Chakra Petch fonts unchanged.
- Prepare the X4+ Home hero and three rotating sleep scenes on native-size canvases using lossless centered crop/pad, without stretching the HALO artwork.
- Declare each package's exact `target_resolution` for automatic selection by The Cantina Store and Razor-Crest.
- Retain `Jadehawk + IOSDEC` author credit and the original HALO design attribution.

## 0.1.4 — Unified extension publishing contract (development only)

- Package `DETAILS.md` within the declared theme payload, matching plugin publication.
- Keep manifest description and `Jadehawk + IOSDEC` attribution authoritative for the catalog.
- Add validation for the packaged details and keep release assets immutable.
- Do not tag or publish until firmware and Plugin Hub have been tested together.

## 0.1.3 — Correct HALO author attribution

- Credit **Jadehawk + IOSDEC** in the package metadata used by installed-theme details and Plugin Hub catalogs.
- Reissue the package so the immutable release asset contains the corrected author; v0.1.2 remains unchanged.
- Preserve all artwork, fonts, behavior, and capability requirements.

## 0.1.2 — Device-friendly package metadata

- Shorten the HALO pack display title without changing the stable `halo/halo` theme identity.
- Ship a concise plain-ASCII installation README for lightweight on-device Details rendering.
- Keep original designer credit and artwork unchanged; document the publisher-side text contract.

## 0.1.1 — Capability and authoring documentation

- Clarify the three independent SD extension types: plugins, themes, and BMP wallpaper packs.
- Document runtime capability discovery through the firmware status API, compatible X3 development builds, and catalog limitations.
- Improve independent theme creation guidance while preserving original HALO artwork and fonts.
- Continue to credit iosdec and the original HALO firmware release.
- No visual or binary asset changes.

## 0.1.0 — First SD theme collection release

- HALO-inspired, monochrome CrossPoint UI collection based on the visual work of **iosdec**.
- Declarative home, header, boot, and sleep scenes; HALO art, Chakra Petch UI fonts, selection/card styling.
- Three rotating HALO sleep backgrounds used on regular Dark/Light sleep entries.
- Separate theme manifest with six capability requirements, 14 runtime files, and precise installable folder layout.
- Generic theme contract and authoring/wallpaper-pack tools; firmware-neutral compatibility documentation.
- **Known limitations:** requires experimental theme-capable firmware, no Plugin Hub theme installer/catalog yet; timed sleep refresh continues to use `/.sleep` and `/sleep` rather than the theme gallery.
