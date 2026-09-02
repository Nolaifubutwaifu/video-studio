#!/usr/bin/env python3
"""probe.py — technical fingerprint of a video.

    python3 tools/probe.py VIDEO [--out probe.json]

Reports the numbers every later stage needs: dimensions, fps, duration, aspect,
and whether the file even has audio (a silent screen recording is a common and
otherwise very confusing failure).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (audio_stream, duration_of, emit, ffprobe_json, main_guard,
                    parse_fps, video_stream)

# Aspect buckets we care about, as (name, ratio).
_ASPECTS = [("9:16", 9 / 16), ("4:5", 4 / 5), ("1:1", 1.0),
            ("16:9", 16 / 9), ("4:3", 4 / 3)]


def classify_aspect(width, height):
    if not width or not height:
        return "unknown"
    ratio = width / height
    name, _ = min(_ASPECTS, key=lambda a: abs(a[1] - ratio))
    return name


def describe(path):
    probe = ffprobe_json(path)
    vs = video_stream(probe)
    aud = audio_stream(probe)
    width, height = int(vs.get("width", 0)), int(vs.get("height", 0))
    dur = duration_of(probe)

    return {
        "path": os.path.abspath(path),
        "filename": os.path.basename(path),
        "width": width,
        "height": height,
        "aspect": classify_aspect(width, height),
        "vertical": height > width,
        "fps": parse_fps(vs.get("avg_frame_rate")),
        "duration_sec": round(dur, 3),
        "video_codec": vs.get("codec_name"),
        "pix_fmt": vs.get("pix_fmt"),
        "bitrate_kbps": (
            round(int(probe["format"]["bit_rate"]) / 1000)
            if probe.get("format", {}).get("bit_rate") else None
        ),
        "size_mb": round(os.path.getsize(path) / 1e6, 2),
        "has_audio": aud is not None,
        "audio_codec": aud.get("codec_name") if aud else None,
        "audio_channels": aud.get("channels") if aud else None,
        "audio_sample_rate": (
            int(aud["sample_rate"]) if aud and aud.get("sample_rate") else None
        ),
    }


def cli():
    ap = argparse.ArgumentParser(description="Technical fingerprint of a video.")
    ap.add_argument("video")
    ap.add_argument("--out", help="also write JSON here")
    args = ap.parse_args()

    info = describe(args.video)
    if not info["has_audio"]:
        print("warning: no audio stream — transcription will not work",
              file=sys.stderr)
    emit(info, args.out)


if __name__ == "__main__":
    main_guard(cli)
