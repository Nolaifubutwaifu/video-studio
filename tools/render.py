#!/usr/bin/env python3
"""render.py — composite the cut take with captions and graphics.

    python3 tools/render.py --video projects/foo/work/trimmed.mp4 \
        --words projects/foo/work/words.json \
        --profile styles/mine/profile.json \
        --title "3 cold email mistakes" \
        --out projects/foo/out/final.mp4

Stages the take into public/, writes the props the Remotion composition reads,
renders, then normalises loudness to the profile's target.

The props file it writes is also what `npm run studio` opens, so the same
render can be reopened and hand-adjusted without re-running the cut. That is
the editable half of the deliverable.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (duration_of, ffprobe_json, load_json, main_guard, need,
                    run, video_stream)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROPS = os.path.join(ROOT, "remotion", "src", "default-props.json")
PUBLIC = os.path.join(ROOT, "public")


def stage(video):
    """Remotion serves media from public/; staticFile() cannot reach outside it."""
    os.makedirs(PUBLIC, exist_ok=True)
    dest = os.path.join(PUBLIC, "take.mp4")
    if os.path.abspath(video) != os.path.abspath(dest):
        shutil.copy2(video, dest)
    return "take.mp4"


def normalize_loudness(src, dest, lufs):
    """Second pass: bring the mix to the platform's expected level."""
    need("ffmpeg")
    run([
        "ffmpeg", "-y", "-v", "error",
        "-i", src,
        "-c:v", "copy",
        "-af", f"loudnorm=I={lufs}:TP=-1.5:LRA=11",
        "-c:a", "aac", "-b:a", "192k",
        dest,
    ], quiet=True)
    return dest


def cli():
    ap = argparse.ArgumentParser(description="Render the final video.")
    ap.add_argument("--video", required=True, help="the trimmed take")
    ap.add_argument("--words", required=True, help="words.json on the trimmed timeline")
    ap.add_argument("--profile", default="styles/default/profile.json")
    ap.add_argument("--title", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--props-only", action="store_true",
                    help="write props and stop, for use with `npm run studio`")
    ap.add_argument("--concurrency", default=None)
    args = ap.parse_args()

    profile = load_json(args.profile)
    words = load_json(args.words)["words"]
    if not words:
        raise RuntimeError("no words to caption")

    probe = ffprobe_json(args.video)
    dur = duration_of(probe)
    vs = video_stream(probe)
    fps = profile["format"]["fps"]

    # Match the composition to the source rather than the profile's nominal
    # size when they disagree -- a mismatch would letterbox or crop the take.
    src_w, src_h = int(vs.get("width", 0)), int(vs.get("height", 0))
    if src_w and (src_w, src_h) != (profile["format"]["width"],
                                    profile["format"]["height"]):
        print(f"note: take is {src_w}x{src_h}, profile says "
              f"{profile['format']['width']}x{profile['format']['height']}; "
              f"rendering at the take's size", file=sys.stderr)
        profile = {**profile, "format": {**profile["format"],
                                         "width": src_w, "height": src_h}}

    props = {
        "videoSrc": stage(args.video),
        "words": words,
        "profile": profile,
        "title": args.title,
        "durationInFrames": max(1, int(round(dur * fps))),
    }
    os.makedirs(os.path.dirname(PROPS), exist_ok=True)
    with open(PROPS, "w") as fh:
        json.dump(props, fh, indent=2)
    print(f"props -> {PROPS}  ({props['durationInFrames']} frames @ {fps}fps)",
          file=sys.stderr)

    if args.props_only:
        print("props written; run `npm run studio` to open the editor",
              file=sys.stderr)
        return

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    raw = os.path.join(os.path.dirname(os.path.abspath(args.out)), "_raw.mp4")

    cmd = ["npx", "remotion", "render", "remotion/src/index.ts", "Video", raw]
    if args.concurrency:
        cmd += ["--concurrency", str(args.concurrency)]
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        raise RuntimeError("remotion render failed")

    normalize_loudness(raw, args.out, profile["audio"]["lufs"])
    os.remove(raw)
    print(f"\nfinal -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main_guard(cli)
