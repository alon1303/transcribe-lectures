"""Convert MP4 file(s) to MP3 using ffmpeg.

Usage:
    python mp4_to_mp3.py video.mp4
    python mp4_to_mp3.py video.mp4 -o audio.mp3
    python mp4_to_mp3.py folder_with_mp4s
    python mp4_to_mp3.py video.mp4 -b 320k
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def convert(src: Path, dst: Path, bitrate: str) -> bool:
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-vn",                      # drop video
        "-acodec", "libmp3lame",
        "-b:a", bitrate,
        str(dst),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed: {src}\n{result.stderr[-500:]}", file=sys.stderr)
        return False
    print(f"Done: {src} -> {dst}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert MP4 to MP3 with ffmpeg")
    parser.add_argument("input", type=Path, help="MP4 file or folder containing MP4 files")
    parser.add_argument("-o", "--output", type=Path, help="output MP3 path (single file only)")
    parser.add_argument("-b", "--bitrate", default="192k", help="MP3 bitrate (default: 192k)")
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None:
        print("ffmpeg not found in PATH.", file=sys.stderr)
        return 1

    if args.input.is_dir():
        files = sorted(args.input.glob("*.mp4"))
        if not files:
            print("No .mp4 files found.", file=sys.stderr)
            return 1
        results = [convert(f, f.with_suffix(".mp3"), args.bitrate) for f in files]
        return 0 if all(results) else 1

    if not args.input.is_file():
        print(f"File not found: {args.input}", file=sys.stderr)
        return 1
    dst = args.output or args.input.with_suffix(".mp3")
    return 0 if convert(args.input, dst, args.bitrate) else 1


if __name__ == "__main__":
    sys.exit(main())
