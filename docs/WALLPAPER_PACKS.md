# Wallpaper-only SD theme collections

**Yes—an SD theme can be a set of sleep wallpapers without changing the theme's Home, header or boot scene.** It remains a **theme**, not an ordinary `/.sleep` folder, so it needs the SD theme capabilities and a user-selected theme.

The non-sleep UI follows the **Classic base**. It does not retain the user's previously selected Lyra/RoundedRaff/other theme while overlaying only its sleep scene.

## Create one from images

Gather **1 to 8** PNG, JPEG, WebP or BMP images in a folder, then run:

```powershell
python -m pip install Pillow
python tools/create_wallpaper_pack.py --images "C:\My Sleep Wallpapers" --out "dist\wallpaper-build" --id "my-wallpapers" --title "My Wallpapers" --author "Your Name"
```

The generator creates:

```text
dist/wallpaper-build/
├── my-wallpapers.crosspoint-theme/
│   ├── manifest.json
│   ├── README.md
│   └── themes/wallpapers/
│       ├── theme.json
│       └── assets/
│           ├── sleep-01.cpb
│           ├── sleep-02.cpb
│           └── ...
└── my-wallpapers-0.1.0.crosspoint-theme.zip
```

The script converts each image to the X3's 528×792 monochrome CPB format and runs the same validator/packer as HALO. Change `--width` and `--height` only when targeting a different board you have actually tested.

## Install and select

1. Copy the *folder*, not just the ZIP, to `/.crosspoint/themes/`.
2. On compatible firmware, select the new theme from **Settings → Display → UI Theme**.
3. Set **Sleep Screen → Dark** or **Light**.
4. Each normal sleep entry selects one image randomly. Repeats can occur.

## Limitations

- A wallpaper-only pack is **not** an addition to the Custom sleep wallpaper pool; it occupies a selectable theme entry.
- **Custom** mode still reads the firmware's ordinary `/.sleep`/`/sleep` wallpaper pool. **Cover** and transparent modes retain their original precedence.
- Timed sleep-screen refresh **does not yet use the theme's gallery**. It selects from the ordinary `/.sleep`/`/sleep` pool.
- Collection folders *inside* `/.sleep` with named-pool selection are a **deferred idea**, not implemented.
- No animation, full-color images, scripting, plugin actions, or new screen behaviors.
- Current limit: up to eight images per theme; 2 MiB total installed payload.
- Firmware without theme capabilities **cannot** read this pack. Stock CrossPoint currently falls in that category.

For the full file format, operations and runtime capability list, see [Theme Contract](THEME_CONTRACT.md).
