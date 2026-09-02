#!/usr/bin/env python3
"""frames.py — contact sheets for visual style analysis.

    python3 tools/frames.py REF.mp4 --outdir styles/mine/frames --mode grid
    python3 tools/frames.py REF.mp4 --outdir ... --mode shots --shots shots.json
    python3 tools/frames.py REF.mp4 --outdir ... --mode captions

These sheets are what the style analyst actually looks at, so every tile is
labelled with its timestamp — otherwise a finding like "the caption moves up
during the hook" cannot be tied back to a moment in the video.

ffmpeg in this environment has no drawtext filter, so composition and labelling
are done with Pillow instead.
"""
import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (duration_of, ffprobe_json, load_json, main_guard, need,
                    run, ts, video_stream)

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("error: Pillow is required (pip install pillow)", file=sys.stderr)
    raise

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial Bold.ttf",
]


def load_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def grab(src, when, dest, width=None):
    """Extract a single frame. -ss before -i seeks fast and is accurate enough
    for stills; frame-accurate seeking is not needed for a contact sheet."""
    need("ffmpeg")
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{when:.3f}", "-i", src,
           "-frames:v", "1"]
    if width:
        cmd += ["-vf", f"scale={width}:-2"]
    cmd += [dest]
    run(cmd, quiet=True)
    return dest if os.path.exists(dest) else None


def label(img, text, pad=6):
    """Stamp a timestamp badge in the top-left of a tile."""
    draw = ImageDraw.Draw(img, "RGBA")
    font = load_font(max(13, img.width // 18))
    box = draw.textbbox((0, 0), text, font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    draw.rectangle([0, 0, w + pad * 2, h + pad * 2], fill=(0, 0, 0, 190))
    draw.text((pad, pad - box[1]), text, font=font, fill=(255, 255, 0, 255))
    return img


def contact_sheet(paths, times, cols, tile_w, out_path):
    tiles = []
    for p, t in zip(paths, times):
        if not p or not os.path.exists(p):
            continue
        img = Image.open(p).convert("RGB")
        ratio = tile_w / img.width
        img = img.resize((tile_w, max(1, int(img.height * ratio))),
                         Image.LANCZOS)
        tiles.append(label(img, ts(t)))

    if not tiles:
        raise RuntimeError("no frames were extracted")

    tile_h = max(t.height for t in tiles)
    rows = (len(tiles) + cols - 1) // cols
    gap = 4
    sheet = Image.new(
        "RGB",
        (cols * tile_w + (cols + 1) * gap, rows * tile_h + (rows + 1) * gap),
        (24, 24, 27),
    )
    for i, tile in enumerate(tiles):
        r, c = divmod(i, cols)
        sheet.paste(tile, (gap + c * (tile_w + gap), gap + r * (tile_h + gap)))

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    sheet.save(out_path, quality=92)
    return out_path, len(tiles)


def pick_times(mode, dur, count, shots_json):
    if mode == "shots":
        if not shots_json:
            raise RuntimeError("--mode shots requires --shots shots.json")
        data = load_json(shots_json)
        bounds = [0.0] + list(data.get("cuts", [])) + [data["duration_sec"]]
        # Mid-shot is the most representative frame and avoids transition blur.
        return [round((a + b) / 2, 3) for a, b in zip(bounds, bounds[1:]) if b > a]
    # Evenly spaced, avoiding the very first and last frames.
    step = dur / (count + 1)
    return [round(step * (i + 1), 3) for i in range(count)]


def cli():
    ap = argparse.ArgumentParser(description="Contact sheets for style analysis.")
    ap.add_argument("video")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--mode", choices=["grid", "shots", "captions"],
                    default="grid")
    ap.add_argument("--count", type=int, default=12,
                    help="frames for grid mode (default 12)")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--tile-width", type=int, default=270)
    ap.add_argument("--shots", help="shots.json, for --mode shots")
    ap.add_argument("--keep-frames", action="store_true",
                    help="also keep the full-resolution stills")
    args = ap.parse_args()

    probe = ffprobe_json(args.video)
    dur = duration_of(probe)
    vs = video_stream(probe)
    height = int(vs.get("height", 0))
    stem = os.path.splitext(os.path.basename(args.video))[0]
    os.makedirs(args.outdir, exist_ok=True)

    times = pick_times(args.mode, dur, args.count, args.shots)
    if not times:
        raise RuntimeError("no timestamps to sample")

    frames_dir = (os.path.join(args.outdir, f"{stem}-stills")
                  if args.keep_frames else None)
    if frames_dir:
        os.makedirs(frames_dir, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="vs-frames-") as tmp:
        paths = []
        for i, t in enumerate(times):
            dest = os.path.join(frames_dir or tmp, f"{stem}-{i:03d}.jpg")
            paths.append(grab(args.video, t, dest))

        if args.mode == "captions":
            # Captions in vertical social video sit in the lower-middle band.
            # Cropping it and stacking one per row makes font weight, stroke
            # and highlight colour legible enough to name precisely.
            crops = []
            for p in paths:
                if not p or not os.path.exists(p):
                    continue
                img = Image.open(p).convert("RGB")
                top, bottom = int(img.height * 0.45), int(img.height * 0.88)
                crops.append(img.crop((0, top, img.width, bottom)))
            band = os.path.join(tmp, "band")
            os.makedirs(band, exist_ok=True)
            cpaths = []
            for i, c in enumerate(crops):
                cp = os.path.join(band, f"c{i:03d}.jpg")
                c.save(cp, quality=95)
                cpaths.append(cp)
            out = os.path.join(args.outdir, f"{stem}-captions.jpg")
            out, n = contact_sheet(cpaths, times, 2, 520, out)
        else:
            out = os.path.join(args.outdir, f"{stem}-{args.mode}.jpg")
            out, n = contact_sheet(paths, times, args.cols, args.tile_width, out)

    print(f"{n} frames -> {out}", file=sys.stderr)
    print(out)


if __name__ == "__main__":
    main_guard(cli)
