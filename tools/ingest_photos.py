#!/usr/bin/env python3
"""
Compress images from the repo root and move them to photos/.
Usage: python3 tools/ingest_photos.py

- Resizes to 1200px wide (preserving aspect ratio), matching existing photos
- Converts to JPEG at quality 85
- Never overwrites: if photos/IMG_1234.jpeg exists, saves as IMG_1234_1.jpeg, etc.
- Removes the original from root after successful conversion
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
PHOTOS = REPO / "photos"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
TARGET_WIDTH = 1200
JPEG_QUALITY = "85"  # 2–31 ffmpeg scale (lower = better); 85 ≈ q:v 2 in libx264 terms
                      # For mjpeg: q:v 2 = ~95%, so use -qscale:v for fine control


def run(cmd):
    subprocess.run([str(c) for c in cmd], check=True)


def safe_dest(photos_dir: Path, stem: str, suffix: str = ".jpeg") -> Path:
    """Return a path in photos_dir that doesn't already exist."""
    candidate = photos_dir / f"{stem}{suffix}"
    counter = 1
    while candidate.exists():
        candidate = photos_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    return candidate


def compress(src: Path, dest: Path):
    run([
        "ffmpeg",
        "-i", src,
        "-vf", f"scale={TARGET_WIDTH}:-2",  # -2 ensures even height
        "-q:v", "3",                          # JPEG quality (~85%)
        "-update", "1",
        "-y", dest,
        "-loglevel", "error",
    ])


def main():
    PHOTOS.mkdir(exist_ok=True)

    candidates = sorted(
        f for f in REPO.iterdir()
        if f.is_file() and f.suffix.lower() in EXTENSIONS
    )

    if not candidates:
        print("No image files found in repo root.")
        return

    print(f"Found {len(candidates)} image(s) to ingest:\n")

    for src in candidates:
        dest = safe_dest(PHOTOS, src.stem)
        renamed = dest.stem != src.stem
        tag = f" (renamed → {dest.name})" if renamed else ""
        print(f"  {src.name}{tag}")

        try:
            compress(src, dest)
            src.unlink()
        except subprocess.CalledProcessError as e:
            print(f"    ERROR: ffmpeg failed — leaving {src.name} in place", file=sys.stderr)
            if dest.exists():
                dest.unlink()  # don't leave a partial file
            continue

        size_kb = dest.stat().st_size // 1024
        print(f"    → {dest.relative_to(REPO)}  ({size_kb} KB)")

    print("\nDone.")


if __name__ == "__main__":
    main()
