#!/usr/bin/env python3
"""ingest.py — bring a reference video into the workspace.

    python3 tools/ingest.py "https://tiktok.com/@x/video/123" --outdir media/refs
    python3 tools/ingest.py ~/Desktop/screenrec.mov --outdir media/refs

Handles the two sources this pipeline supports:
  * links  — downloaded with yt-dlp, falling back to browser cookies when a
    platform refuses an anonymous request (routine for Instagram and TikTok).
  * screen recordings — analysed with cropdetect, because a phone screen
    recording is usually letterboxed inside a larger canvas and the black bars
    would otherwise skew every framing measurement downstream.

NOTE: downloaded references are third-party copyrighted material. They are
analysis input only and are kept out of git by .gitignore.
"""
import argparse
import glob
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (duration_of, emit, ffprobe_json, main_guard, need, run,
                    video_stream)

URL_RE = re.compile(r"^https?://", re.I)


def is_url(value):
    return bool(URL_RE.match(value))


def slugify(text, limit=60):
    slug = re.sub(r"[^\w\s-]", "", text).strip().lower()
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug[:limit] or "reference"


def download(url, outdir, cookies_browser=None):
    need("yt-dlp")
    os.makedirs(outdir, exist_ok=True)
    template = os.path.join(outdir, "%(id)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "-o", template,
        "--print", "after_move:filepath",
        url,
    ]
    if cookies_browser:
        cmd[1:1] = ["--cookies-from-browser", cookies_browser]

    proc = run(cmd, check=False)
    path = (proc.stdout or "").strip().splitlines()
    path = path[-1] if path else None

    if not path or not os.path.exists(path):
        if not cookies_browser:
            print("download failed; retrying with Chrome cookies…",
                  file=sys.stderr)
            return download(url, outdir, cookies_browser="chrome")
        raise RuntimeError(
            f"yt-dlp could not fetch {url}\n"
            f"{(proc.stderr or '').strip()[-800:]}\n\n"
            "Instagram/TikTok often block anonymous downloads. Falling back to a "
            "screen recording of the video is the reliable path."
        )
    return path


def detect_crop(path, dur):
    """Find the real content rectangle inside a possibly-letterboxed recording."""
    need("ffmpeg")
    # Sample from 20% in — intros are often black and would fool cropdetect.
    start = max(0.0, dur * 0.2)
    proc = run([
        "ffmpeg", "-v", "info", "-nostats",
        "-ss", f"{start:.2f}", "-i", path,
        "-t", "5",
        "-vf", "cropdetect=limit=24:round=2:reset=0",
        "-f", "null", "-",
    ], check=False)
    hits = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", proc.stderr or "")
    if not hits:
        return None
    w, h, x, y = (int(v) for v in hits[-1])
    return {"w": w, "h": h, "x": x, "y": y}


def cli():
    ap = argparse.ArgumentParser(description="Ingest a reference video.")
    ap.add_argument("source", help="URL or local file path")
    ap.add_argument("--outdir", default="media/refs")
    ap.add_argument("--name", help="override the stored filename stem")
    ap.add_argument("--cookies-from-browser", dest="cookies",
                    help="e.g. chrome, safari, firefox")
    ap.add_argument("--no-crop-detect", action="store_true")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    if is_url(args.source):
        path = download(args.source, args.outdir, args.cookies)
        origin = "download"
    else:
        src = os.path.expanduser(args.source)
        if not os.path.exists(src):
            raise RuntimeError(f"no such file: {src}")
        stem = slugify(args.name or os.path.splitext(os.path.basename(src))[0])
        path = os.path.join(args.outdir, stem + os.path.splitext(src)[1].lower())
        if os.path.abspath(src) != os.path.abspath(path):
            shutil.copy2(src, path)
        origin = "local"

    probe = ffprobe_json(path)
    vs = video_stream(probe)
    dur = duration_of(probe)
    width, height = int(vs.get("width", 0)), int(vs.get("height", 0))

    crop = None
    if not args.no_crop_detect:
        crop = detect_crop(path, dur)

    letterboxed = bool(
        crop and (crop["w"] < width - 4 or crop["h"] < height - 4)
    )

    result = {
        "source": args.source,
        "origin": origin,
        "path": os.path.abspath(path),
        "width": width,
        "height": height,
        "duration_sec": round(dur, 3),
        "content_crop": crop,
        "letterboxed": letterboxed,
        # A screen recording of a full-screen social video is the common case;
        # flagging it tells the style analyst to expect platform UI on top.
        "likely_screen_recording": origin == "local" and letterboxed,
    }
    if letterboxed:
        print(f"note: content is letterboxed -> crop={crop['w']}:{crop['h']}:"
              f"{crop['x']}:{crop['y']}", file=sys.stderr)
    emit(result)


if __name__ == "__main__":
    main_guard(cli)
