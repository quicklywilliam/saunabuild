#!/usr/bin/env python3
"""
Find the loop point in a video, trim to one loop, remove audio.
Usage: python3 make_loop.py <input_file>
Output: <input_stem>_loop.<ext>
"""

import json
import subprocess
import sys
from pathlib import Path

PROBE_WIDTH = 160


def run(cmd):
    subprocess.run(cmd, check=True)


def probe(input_path):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", str(input_path)],
        capture_output=True, text=True, check=True
    )
    data = json.loads(result.stdout)
    v = next(s for s in data["streams"] if s["codec_type"] == "video")
    num, den = v["avg_frame_rate"].split("/")
    fps = int(num) / int(den)
    return fps, int(v["nb_frames"]), int(v["width"]), int(v["height"])


def extract_frames_gray(input_path, probe_h):
    print(f"Extracting frames at {PROBE_WIDTH}x{probe_h} grayscale ...")
    result = subprocess.run([
        "ffmpeg", "-i", str(input_path),
        "-vf", f"scale={PROBE_WIDTH}:{probe_h}",
        "-f", "rawvideo", "-pix_fmt", "gray",
        "-vsync", "0", "-loglevel", "error", "pipe:1"
    ], capture_output=True, check=True)
    return result.stdout


def find_loop(frames_np):
    import numpy as np
    n = len(frames_np)
    results = []
    for L in range(2, n):
        diff = frames_np[:n - L].astype(np.int32) - frames_np[L:].astype(np.int32)
        avg_mse = float(np.mean(diff ** 2))
        results.append((avg_mse, L))
    results.sort()
    return results


def trim_and_mute(input_path, output_path, loop_frames, fps):
    duration_s = loop_frames / fps
    print(f"Trimming to {loop_frames} frames ({duration_s:.4f}s), removing audio ...")
    run([
        "ffmpeg", "-i", str(input_path),
        "-t", str(duration_s),
        "-an",
        "-c:v", "copy",
        "-y", str(output_path),
        "-loglevel", "error"
    ])
    print(f"Done -> {output_path}")


def main():
    try:
        import numpy as np
    except ImportError:
        sys.exit("numpy is required: pip install numpy")

    if len(sys.argv) < 2:
        sys.exit(f"Usage: {sys.argv[0]} <input_file>")

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        sys.exit(f"File not found: {input_path}")
    output_path = input_path.with_stem(input_path.stem + "_loop")

    fps, nb_frames, width, height = probe(input_path)
    probe_h = max(1, round(height * PROBE_WIDTH / width))
    frame_size = PROBE_WIDTH * probe_h

    print(f"Input: {nb_frames} frames @ {fps:.3f} fps  ({width}x{height})")

    raw = extract_frames_gray(input_path, probe_h)
    actual = len(raw) // frame_size
    print(f"Decoded {actual} frames")

    frames = np.frombuffer(raw, dtype=np.uint8).reshape(actual, frame_size)

    print("Searching for loop point ...")
    candidates = find_loop(frames)

    print("\nTop 10 loop candidates:")
    for mse, L in candidates[:10]:
        print(f"  L={L:4d} frames  ({L/fps:.3f}s)  avg_mse={mse:.2f}")

    best_mse, best_L = candidates[0]
    print(f"\nBest: {best_L} frames ({best_L/fps:.4f}s), avg_mse={best_mse:.2f}")

    confirm = input(f"\nUse L={best_L}? [y/N or enter a different frame count] ").strip()
    if confirm.lstrip("-").isdigit():
        best_L = int(confirm)
    elif confirm.lower() != "y":
        print("Aborted.")
        sys.exit(0)

    trim_and_mute(input_path, output_path, best_L, fps)


if __name__ == "__main__":
    main()
