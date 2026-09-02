#!/usr/bin/env python3
"""audio.py — pause rhythm and loudness measurement.

    python3 tools/audio.py REF.mp4 --out audio.json

Two things come out of this:
  * pause statistics — how much dead air a reference tolerates, which becomes
    the editor's `max_silence_sec` threshold.
  * integrated loudness — so the final render can be normalized to the same
    perceived level the platform expects (-14 LUFS is the usual target).
"""
import argparse
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (duration_of, emit, ffprobe_json, main_guard, need, run, ts)

# -30 dB below full scale reliably separates speech from room tone without
# clipping the quiet tail of a word.
NOISE_FLOOR_DB = -30.0
MIN_SILENCE_SEC = 0.25


def detect_silences(path, noise_db, min_sec):
    need("ffmpeg")
    proc = run([
        "ffmpeg", "-v", "info", "-nostats",
        "-i", path,
        "-af", f"silencedetect=noise={noise_db}dB:d={min_sec}",
        "-f", "null", "-",
    ], check=False)
    err = proc.stderr or ""

    starts = [float(m) for m in re.findall(r"silence_start:\s*(-?[0-9.]+)", err)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*(-?[0-9.]+)", err)]

    spans = []
    for i, s in enumerate(starts):
        e = ends[i] if i < len(ends) else None
        if e is None or e <= s:
            continue
        spans.append({"start": round(s, 3), "end": round(e, 3),
                      "dur": round(e - s, 3)})
    return spans


def measure_loudness(path):
    """Two-pass loudnorm's measurement pass — returns EBU R128 figures."""
    need("ffmpeg")
    proc = run([
        "ffmpeg", "-v", "info", "-nostats",
        "-i", path,
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
        "-f", "null", "-",
    ], check=False)

    # The JSON block is the last {...} ffmpeg prints on stderr.
    blocks = re.findall(r"\{[^{}]*\}", proc.stderr or "", re.S)
    for block in reversed(blocks):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if "input_i" in data:
            def num(key):
                try:
                    return round(float(data[key]), 2)
                except (KeyError, TypeError, ValueError):
                    return None
            return {
                "integrated_lufs": num("input_i"),
                "true_peak_db": num("input_tp"),
                "lra": num("input_lra"),
                "threshold": num("input_thresh"),
            }
    return {}


def summarize(path, noise_db, min_sec):
    probe = ffprobe_json(path)
    dur = duration_of(probe)
    spans = detect_silences(path, noise_db, min_sec)
    silent = sum(s["dur"] for s in spans)
    durs = [s["dur"] for s in spans]

    return {
        "source": os.path.abspath(path),
        "duration_sec": round(dur, 3),
        "noise_floor_db": noise_db,
        "min_silence_sec": min_sec,
        "silence_count": len(spans),
        "silence_total_sec": round(silent, 3),
        "silence_pct": round(100 * silent / dur, 1) if dur else 0,
        "speech_pct": round(100 * (1 - silent / dur), 1) if dur else 0,
        "pause": {
            "avg_sec": round(statistics.fmean(durs), 3) if durs else None,
            "median_sec": round(statistics.median(durs), 3) if durs else None,
            "max_sec": round(max(durs), 3) if durs else None,
        },
        "loudness": measure_loudness(path),
        "silences": spans,
        "silences_human": [f"{ts(s['start'])}-{ts(s['end'])} ({s['dur']}s)"
                           for s in spans],
    }


def cli():
    ap = argparse.ArgumentParser(description="Pause rhythm + loudness.")
    ap.add_argument("media")
    ap.add_argument("--out")
    ap.add_argument("--noise-db", type=float, default=NOISE_FLOOR_DB)
    ap.add_argument("--min-silence", type=float, default=MIN_SILENCE_SEC)
    args = ap.parse_args()

    result = summarize(args.media, args.noise_db, args.min_silence)
    print(f"{result['silence_count']} pauses, {result['silence_pct']}% silent, "
          f"{result['loudness'].get('integrated_lufs')} LUFS", file=sys.stderr)
    emit(result, args.out)


if __name__ == "__main__":
    main_guard(cli)
