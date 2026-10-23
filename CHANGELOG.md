# Changelog

## 0.1.2 — Device-friendly package metadata (unreleased)

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
