# Wallpaper packs and theme sleep galleries

There are now **two different ways to provide sleep artwork**.

| | Independent Custom wallpaper pack | A theme's own Dark/Light sleep gallery |
|---|---|---|
| Purpose | Wallpapers without changing UI theme | Wallpaper artwork that belongs to a full UI design |
| Install directory | `/.crosspoint/wallpapers/<id>.crosspoint-wallpaper/` | `/.crosspoint/themes/<id>.crosspoint-theme/` |
| Format | Ordinary BMP files | Bounded 1-bit CPB artwork |
| Firmware requirement | `wallpaper.packs.v1` | `theme.sd.v1`, `theme.images.v1`, `theme.composition.v1` and other declared capabilities |
| Selection | Sleep Screen = Custom → Wallpaper Collection | Settings → Display → UI Theme and Sleep Screen = Dark/Light |
| Changes current UI theme? | **No** | **Yes** |
| Timed wake rotation | Uses selected BMP collection | **Not yet**; the current timed path is separate |

To create a **standalone wallpaper pack**, start from the separate local
`crosspoint-wallpaper-template` repository and follow its
`docs/WALLPAPER_PACK_CONTRACT.md`. Each collection has its own repository,
version, README, BMP files and versioned install-only GitHub ZIP. Its collection
title appears in the scrollable Wallpaper Collection picker; choosing
**All wallpapers** retains the shared `/.sleep` and `/sleep` pool (and
normal `/sleep.bmp` priority).

A UI theme may optionally provide up to eight `sleep_art` CPB images. HALO
does this: each regular Dark/Light sleep transition chooses a random image
and composes themed text/emblems. Such a gallery is **part of the selected UI
theme** and falls back to its `classic` base, not another active theme.

Both kinds are declarative and firmware capability-gated. Neither is a plugin
nor runs JavaScript. Folder-named collections **inside** `/.sleep`, automatic
theme/wallpaper catalog installation, and timed refresh of a theme-internal
gallery are deferred, not implemented.

See [Theme Contract](THEME_CONTRACT.md) and
[Supported Firmware](SUPPORTED_FIRMWARE.md) before publishing.
