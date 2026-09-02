#!/usr/bin/env python3
"""shots.py — cut detection and pacing statistics for a reference video.

    python3 tools/shots.py REF.mp4 --out shots.json

Answers "how fast does this creator cut?" The resulting cuts-per-minute and
shot-length distribution are what the editor targets when it decides how many
punch-ins to place in your take.
"""
import argparse
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (duration_of, emit, ffprobe_json, main_guard, need, run, ts)

# scdet reports a score 0-100; 10 is ffmpeg's default and is tuned for real
# scene changes. Social videos cut hard, so this catches them reliably while
# ignoring motion within a shot.
DEFAULT_THRESHOLD = 10.0


def detect_cuts(path, threshold):
    """Return timestamps (seconds) where a hard cut occurs."""
    need("ffmpeg")
    proc = run([
        "ffmpeg", "-v", "info", "-nostats",
        "-i", path,
        "-vf", f"scdet=threshold={threshold}",
        "-f", "null", "-",
    ], check=False)

    # ffmpeg prints: [Parsed_scdet_0 @ ...] lavfi.scd.score: 42.11, lavfi.scd.time: 3.5
    times = []
    for m in re.finditer(r"lavfi\.scd\.time:\s*([0-9.]+)", proc.stderr or ""):
        times.append(round(float(m.group(1)), 3))
    return sorted(set(times))


def summarize(path, threshold):
    probe = ffprobe_json(path)
    dur = duration_of(probe)
    cuts = [t for t in detect_cuts(path, threshold) if 0.05 < t < dur - 0.05]

    # Shot boundaries are the cuts plus the start and end of the file.
    bounds = [0.0] + cuts + [dur]
    lengths = [round(b - a, 3) for a, b in zip(bounds, bounds[1:]) if b > a]

    stats = {}
    if lengths:
        stats = {
            "avg_sec": round(statistics.fmean(lengths), 3),
            "median_sec": round(statistics.median(lengths), 3),
            "min_sec": round(min(lengths), 3),
            "max_sec": round(max(lengths), 3),
        }

    return {
        "source": os.path.abspath(path),
        "duration_sec": round(dur, 3),
        "threshold": threshold,
        "cut_count": len(cuts),
        "cuts_per_min": round(len(cuts) / (dur / 60.0), 2) if dur else 0,
        "shot_count": len(lengths),
        "shot_length": stats,
        "cuts": cuts,
        "cuts_human": [ts(c) for c in cuts],
        "shot_lengths": lengths,
    }


def cli():
    ap = argparse.ArgumentParser(description="Cut detection + pacing stats.")
    ap.add_argument("video")
    ap.add_argument("--out")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help=f"scdet sensitivity, lower = more cuts (default {DEFAULT_THRESHOLD})")
    args = ap.parse_args()

    result = summarize(args.video, args.threshold)
    print(f"{result['cut_count']} cuts, {result['cuts_per_min']}/min, "
          f"avg shot {result['shot_length'].get('avg_sec')}s", file=sys.stderr)
    emit(result, args.out)


if __name__ == "__main__":
    main_guard(cli)
