#!/usr/bin/env python3
"""
XII OS — Wallpaper Generator
wallpapers/generate-wallpaper.py

Converts xii-default.svg (and other XII SVG wallpapers) to
high-resolution PNG/JPEG for use with swaybg, hyprpaper, etc.

Requirements:
    pip install cairosvg Pillow
    OR: apt install python3-cairosvg python3-pil

Usage:
    python3 generate-wallpaper.py                  # Generate all SVG → PNG
    python3 generate-wallpaper.py --res 1920x1080  # Specific resolution
    python3 generate-wallpaper.py --input xii-default.svg
    python3 generate-wallpaper.py --list-presets
"""

import sys
import argparse
import os
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Preset resolutions
# ─────────────────────────────────────────────────────────────
PRESETS = {
    "fhd":   (1920, 1080,  "1920×1080 Full HD"),
    "qhd":   (2560, 1440,  "2560×1440 Quad HD"),
    "4k":    (3840, 2160,  "3840×2160 Ultra HD 4K"),
    "ultrawide": (3440, 1440, "3440×1440 Ultrawide QHD"),
    "laptop": (1366, 768,  "1366×768 Common Laptop"),
    "steam":  (1280, 800,  "1280×800 Steam Deck"),
}

WALLPAPER_DIR = Path(__file__).parent


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def check_deps():
    missing = []
    try:
        import cairosvg
    except ImportError:
        missing.append("cairosvg")
    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")
    if missing:
        print(f"\n  Missing dependencies: {', '.join(missing)}")
        print("  Install with:  pip install " + " ".join(missing))
        print("  Or (Debian):   sudo apt install python3-cairosvg python3-pil\n")
        sys.exit(1)


def generate(svg_path: Path, width: int, height: int, output_dir: Path) -> Path:
    import cairosvg
    from PIL import Image
    import io

    stem = svg_path.stem
    out_path = output_dir / f"{stem}-{width}x{height}.png"
    print(f"  Generating: {out_path.name} ({width}×{height}px)...", end=" ", flush=True)

    # Render SVG → PNG via cairosvg
    png_bytes = cairosvg.svg2png(
        url=str(svg_path),
        output_width=width,
        output_height=height,
        background_color=None,
        dpi=96,
    )

    # Write PNG
    with open(out_path, "wb") as f:
        f.write(png_bytes)

    size_kb = out_path.stat().st_size // 1024
    print(f"✓  ({size_kb} KB)")
    return out_path


def generate_jpeg(png_path: Path, quality: int = 92) -> Path:
    from PIL import Image
    jpg_path = png_path.with_suffix(".jpg")
    img = Image.open(png_path).convert("RGB")
    img.save(jpg_path, "JPEG", quality=quality, optimize=True)
    size_kb = jpg_path.stat().st_size // 1024
    print(f"  → JPEG: {jpg_path.name} ({size_kb} KB)")
    return jpg_path


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="XII OS Wallpaper Generator — SVG → PNG/JPEG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 generate-wallpaper.py                      # All SVGs, all presets
  python3 generate-wallpaper.py --preset qhd         # All SVGs, 1440p only
  python3 generate-wallpaper.py --res 1920x1080      # Custom resolution
  python3 generate-wallpaper.py --input xii-lite.svg # Specific SVG
  python3 generate-wallpaper.py --list-presets       # Show preset list
        """,
    )
    parser.add_argument("--input",  type=str, default=None,
                        help="Specific SVG input file (default: all *.svg)")
    parser.add_argument("--preset", type=str, default=None,
                        choices=PRESETS.keys(),
                        help="Named resolution preset")
    parser.add_argument("--res",    type=str, default=None,
                        help="Custom resolution e.g. 1920x1080")
    parser.add_argument("--output", type=str, default=None,
                        help="Output directory (default: same as input)")
    parser.add_argument("--jpeg",   action="store_true",
                        help="Also generate JPEG version")
    parser.add_argument("--list-presets", action="store_true")
    args = parser.parse_args()

    if args.list_presets:
        print("\nXII OS Wallpaper — Resolution Presets:")
        for k, (w, h, label) in PRESETS.items():
            print(f"  {k:<12} {w}×{h:<6}  {label}")
        print()
        return

    check_deps()

    # Determine resolution
    if args.preset:
        w, h, _ = PRESETS[args.preset]
    elif args.res:
        try:
            w, h = map(int, args.res.lower().split("x"))
        except Exception:
            print(f"  Error: Invalid resolution format '{args.res}'. Use WxH e.g. 1920x1080")
            sys.exit(1)
    else:
        # Default: generate all presets
        w, h = None, None

    # Determine input SVGs
    if args.input:
        svgs = [Path(args.input)]
        if not svgs[0].exists():
            print(f"  Error: File not found: {svgs[0]}")
            sys.exit(1)
    else:
        svgs = list(WALLPAPER_DIR.glob("*.svg"))
        if not svgs:
            print("  No SVG files found in wallpapers directory.")
            sys.exit(1)

    # Determine output dir
    out_dir = Path(args.output) if args.output else WALLPAPER_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nXII OS Wallpaper Generator")
    print(f"  SVGs found:   {len(svgs)}")
    print(f"  Output dir:   {out_dir}\n")

    for svg in svgs:
        print(f"─ {svg.name}")
        if w and h:
            # Single resolution
            png = generate(svg, w, h, out_dir)
            if args.jpeg:
                generate_jpeg(png)
        else:
            # All presets
            for preset_name, (pw, ph, label) in PRESETS.items():
                try:
                    png = generate(svg, pw, ph, out_dir)
                    if args.jpeg:
                        generate_jpeg(png)
                except Exception as e:
                    print(f"  ✗ Failed ({preset_name}): {e}")
        print()

    print("Done. Set wallpaper with:")
    print("  swaybg -i wallpapers/xii-default-1920x1080.png -m fill")
    print("  or configure Hyprland via hyprpaper.conf\n")


if __name__ == "__main__":
    main()
