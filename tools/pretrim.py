#!/usr/bin/env python3
"""pretrim.py — apply an EDL to the source and remap the transcript onto the
new timeline.

    python3 tools/pretrim.py TAKE.mp4 --edl edl.json --words words.json \
        --outdir projects/foo/work

Produces:
  trimmed.mp4    only the kept ranges, concatenated
  timeline.json  source<->output time mapping
  words.json     the surviving words, re-timed to the trimmed video

The remap is the part that matters. Whisper's timestamps refer to the original
take; once ranges are removed every one of them is wrong. Captions are driven
off these timestamps, so they must be rebased or every word lands late.
"""
import argparse
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (duration_of, emit, ffprobe_json, load_json,
                    main_guard, need, run)


def build_segments(src, keeps, tmp, hw, crf):
    """Cut each keep range to its own file, re-encoding for frame accuracy.

    Stream copying cannot cut at arbitrary points (it snaps to keyframes), so a
    re-encode is required; the intermediate is kept visually lossless because
    the renderer encodes again afterwards.
    """
    need("ffmpeg")
    parts = []
    for i, k in enumerate(keeps):
        dest = os.path.join(tmp, f"seg{i:04d}.mp4")
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            # -ss before -i seeks fast; -copyts is avoided so each segment
            # starts cleanly at zero.
            "-ss", f"{k['start']:.3f}",
            "-to", f"{k['end']:.3f}",
            "-i", src,
        ]
        if hw:
            cmd += ["-c:v", "h264_videotoolbox", "-b:v", "12M"]
        else:
            cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf)]
        cmd += [
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-avoid_negative_ts", "make_zero",
            dest,
        ]
        run(cmd, quiet=True)
        # The encoder snaps cuts to frame boundaries, so a segment is almost
        # always a few tens of milliseconds longer than requested. Measuring
        # the result instead of trusting the request keeps the caption timeline
        # exact -- the error is small per segment but strictly accumulates.
        actual = duration_of(ffprobe_json(dest))
        parts.append({"path": dest, "dur": round(actual, 4), "keep": k})
        drift = actual - k["dur"]
        print(f"  segment {i+1}/{len(keeps)}  {k['dur']}s "
              f"(actual {actual:.3f}s, {drift:+.3f}s)", file=sys.stderr)
    return parts


def concat(parts, dest, tmp):
    listing = os.path.join(tmp, "concat.txt")
    with open(listing, "w") as fh:
        for p in parts:
            fh.write(f"file '{p['path']}'\n")
    run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "concat", "-safe", "0", "-i", listing,
        "-c", "copy",
        dest,
    ], quiet=True)
    return dest


def make_timeline(parts):
    """source->output offset table, in output order.

    Uses each segment's measured duration so downstream word timings match the
    file that actually exists rather than the one that was requested.
    """
    timeline, cursor = [], 0.0
    for p in parts:
        k, dur = p["keep"], p["dur"]
        timeline.append({
            "src_start": k["start"],
            "src_end": k["end"],
            "out_start": round(cursor, 4),
            "out_end": round(cursor + dur, 4),
            "dur": dur,
            "requested_dur": k["dur"],
            "drift": round(dur - k["dur"], 4),
        })
        cursor += dur
    return timeline, round(cursor, 4)


def remap_words(words, timeline):
    """Re-time surviving words; words inside a removed range are dropped.

    A word straddling a cut boundary is clamped into the kept part rather than
    discarded, so a caption never loses a word that was actually spoken.
    """
    out = []
    for w in words:
        for seg in timeline:
            if w["start"] < seg["src_end"] and w["end"] > seg["src_start"]:
                start = max(w["start"], seg["src_start"])
                end = min(w["end"], seg["src_end"])
                if end - start < 0.02:
                    continue
                # Map proportionally across the segment: the encoded segment
                # is fractionally longer than the source range it came from,
                # so a flat shift would drift within long segments too.
                src_span = seg["src_end"] - seg["src_start"]
                scale = (seg["dur"] / src_span) if src_span > 0 else 1.0
                out.append({
                    **w,
                    "i": len(out),
                    "start": round(seg["out_start"]
                                   + (start - seg["src_start"]) * scale, 3),
                    "end": round(seg["out_start"]
                                 + (end - seg["src_start"]) * scale, 3),
                    "src_start": w["start"],
                })
                break
    return out


def cli():
    ap = argparse.ArgumentParser(description="Apply an EDL and remap the transcript.")
    ap.add_argument("video")
    ap.add_argument("--edl", required=True)
    ap.add_argument("--words", help="words.json to remap onto the new timeline")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--hw", action="store_true",
                    help="encode with h264_videotoolbox (faster, Apple silicon)")
    ap.add_argument("--crf", type=int, default=18,
                    help="libx264 quality for the intermediate (default 18)")
    args = ap.parse_args()

    edl = load_json(args.edl)
    keeps = edl.get("keep", [])
    if not keeps:
        raise RuntimeError("EDL contains no keep ranges")

    os.makedirs(args.outdir, exist_ok=True)
    trimmed = os.path.join(args.outdir, "trimmed.mp4")

    with tempfile.TemporaryDirectory(prefix="vs-pretrim-") as tmp:
        parts = build_segments(args.video, keeps, tmp, args.hw, args.crf)
        if len(parts) == 1:
            shutil.copy2(parts[0]["path"], trimmed)
        else:
            concat(parts, trimmed, tmp)
        timeline, total = make_timeline(parts)
    tl_path = os.path.join(args.outdir, "timeline.json")
    emit({
        "source": os.path.abspath(args.video),
        "trimmed": os.path.abspath(trimmed),
        "expected_duration_sec": total,
        "segments": timeline,
    }, tl_path)

    if args.words:
        wdoc = load_json(args.words)
        remapped = remap_words(wdoc["words"], timeline)
        out_words = os.path.join(args.outdir, "words.json")
        emit({
            **wdoc,
            "source": os.path.abspath(trimmed),
            "remapped_from": os.path.abspath(args.words),
            "word_count": len(remapped),
            "words": remapped,
        }, out_words)
        print(f"remapped {len(remapped)}/{len(wdoc['words'])} words",
              file=sys.stderr)

    print(f"\ntrimmed -> {trimmed}  (expected {total}s)", file=sys.stderr)


if __name__ == "__main__":
    main_guard(cli)
