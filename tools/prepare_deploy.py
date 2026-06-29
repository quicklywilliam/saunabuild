#!/usr/bin/env python3
"""
Prepare a looped video for deployment.
Usage: python3 tools/prepare_deploy.py <looped_input.mov>

Outputs to movies/:
  fire.mp4         — desktop, full resolution, web-optimized H.264
  fire_mobile.mp4  — mobile, ~67% width, web-optimized H.264
  fire_poster.jpg  — first frame, full resolution JPEG
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
MOVIES = REPO / "movies"

# Mobile is ~67% of desktop width (matches existing fire_mobile.mp4 ratio)
MOBILE_SCALE = "iw*2/3:-2"

# H.264 encoding settings for web
H264_OPTS = [
    "-c:v", "libx264",
    "-preset", "slow",       # better compression
    "-crf", "23",            # quality (lower = better, 18-28 typical)
    "-pix_fmt", "yuv420p",   # broadest compatibility
    "-an",                   # no audio
    "-movflags", "+faststart",  # move moov atom to front for streaming
]


def run(cmd):
    print(" ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True)


def main():
    if len(sys.argv) < 2:
        sys.exit(f"Usage: {sys.argv[0]} <looped_input>")

    inp = Path(sys.argv[1])
    if not inp.exists():
        sys.exit(f"File not found: {inp}")

    MOVIES.mkdir(exist_ok=True)

    desktop = MOVIES / "fire.mp4"
    mobile = MOVIES / "fire_mobile.mp4"
    poster = MOVIES / "fire_poster.jpg"

    print(f"\n── Desktop: {desktop}")
    run([
        "ffmpeg", "-i", inp,
        *H264_OPTS,
        "-y", desktop,
    ])

    print(f"\n── Mobile: {mobile}")
    run([
        "ffmpeg", "-i", inp,
        "-vf", f"scale={MOBILE_SCALE}",
        *H264_OPTS,
        "-y", mobile,
    ])

    print(f"\n── Poster: {poster}")
    run([
        "ffmpeg", "-i", inp,
        "-frames:v", "1",
        "-update", "1",
        "-q:v", "2",          # JPEG quality (2 = near-lossless)
        "-y", poster,
    ])

    print("\nDone.")
    for f in (desktop, mobile, poster):
        size = f.stat().st_size
        print(f"  {f.name:25s}  {size/1024/1024:.1f} MB" if size > 1024*1024 else f"  {f.name:25s}  {size/1024:.0f} KB")


if __name__ == "__main__":
    main()
