#!/usr/bin/env python3
"""edl.py — turn a raw take into an edit decision list.

    python3 tools/edl.py --words words.json --audio audio.json \
        --profile styles/mine/profile.json --out edl.json

Removes three things, all at word-timestamp precision:

  1. retakes  — a phrase restarted; the LAST clean attempt is the one kept
  2. fillers  — um / uh / er and friends
  3. dead air — pauses trimmed down to the reference's tolerance, not deleted
                outright, because removing a beat entirely sounds unnatural

Deliberately conservative. Anything it is unsure about is reported as a hint
for a human to judge rather than silently cut, because a wrong cut destroys a
take and a missed one costs nothing but a second of runtime.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import emit, load_json, main_guard, ts

# Unambiguous disfluencies. "like" and "you know" are NOT here: they are real
# words often enough that removing them by default mangles honest sentences.
# --aggressive opts into those.
FILLERS = {"um", "uh", "erm", "er", "ah", "uhh", "umm", "mm", "hmm"}
AGGRESSIVE_FILLERS = {"like", "basically", "literally", "actually", "so"}

# A repeated run this long, restarted almost immediately, is a retake.
MIN_RETAKE_RUN = 2
# How many words may sit between the two attempts before it stops looking like
# a restart and starts looking like natural repetition for emphasis.
RETAKE_GAP_WORDS = 4
# Keep a hair of silence around a cut so consonants are not clipped.
GUARD_SEC = 0.04


def find_retakes(words, min_run, gap):
    """Mark the earlier of two near-identical adjacent runs for removal."""
    keys = [w["key"] for w in words]
    n = len(keys)
    cuts = []
    i = 0
    while i < n:
        best = None
        # Longest match wins, so a 5-word restart is not mistaken for a 2-word one.
        for run in range(min(12, (n - i) // 2), min_run - 1, -1):
            first = keys[i:i + run]
            if not all(first):
                continue
            for j in range(i + run, min(i + run + gap + 1, n - run + 1)):
                if keys[j:j + run] == first:
                    best = (run, j)
                    break
            if best:
                break
        if best:
            run, j = best
            cuts.append({
                "start": words[i]["start"],
                "end": words[j]["start"],
                "reason": "retake",
                "detail": " ".join(w["word"] for w in words[i:i + run]),
                "words": [i, j - 1],
            })
            i = j
        else:
            i += 1
    return cuts


def find_fillers(words, aggressive):
    vocab = FILLERS | (AGGRESSIVE_FILLERS if aggressive else set())
    out = []
    for w in words:
        if w["key"] in vocab:
            out.append({
                "start": w["start"],
                "end": w["end"],
                "reason": "filler",
                "detail": w["word"],
                "words": [w["i"], w["i"]],
            })
    return out


def find_dead_air(silences, max_silence, duration):
    """Trim over-long pauses down to max_silence rather than deleting them."""
    out = []
    for s in silences:
        excess = s["dur"] - max_silence
        if excess <= 0.05:
            continue
        # Trim from the middle, leaving half the allowance on each side.
        keep_head = s["start"] + max_silence / 2.0
        keep_tail = s["end"] - max_silence / 2.0
        if keep_tail <= keep_head:
            continue
        # Never trim the trailing silence at the very end of the file here;
        # the tail is handled by the final keep-range clamp.
        if s["start"] >= duration - 0.2:
            continue
        out.append({
            "start": round(keep_head, 3),
            "end": round(keep_tail, 3),
            "reason": "dead_air",
            "detail": f"{s['dur']}s pause trimmed to {max_silence}s",
            "words": None,
        })
    return out


def merge(spans):
    """Union of possibly-overlapping cut spans."""
    if not spans:
        return []
    ordered = sorted(spans, key=lambda s: s["start"])
    out = [dict(ordered[0])]
    for s in ordered[1:]:
        if s["start"] <= out[-1]["end"] + 1e-6:
            if s["end"] > out[-1]["end"]:
                out[-1]["end"] = s["end"]
                out[-1]["reason"] = f"{out[-1]['reason']}+{s['reason']}"
        else:
            out.append(dict(s))
    return out


def invert(cuts, duration, guard):
    """Cut spans -> keep spans."""
    keeps = []
    cursor = 0.0
    for c in cuts:
        start = max(0.0, c["start"] - guard)
        if start - cursor > 0.08:      # drop slivers too short to be watchable
            keeps.append({"start": round(cursor, 3), "end": round(start, 3)})
        cursor = max(cursor, c["end"] + guard)
    if duration - cursor > 0.08:
        keeps.append({"start": round(cursor, 3), "end": round(duration, 3)})
    for k in keeps:
        k["dur"] = round(k["end"] - k["start"], 3)
    return keeps


def cli():
    ap = argparse.ArgumentParser(description="Build an edit decision list.")
    ap.add_argument("--words", required=True, help="words.json from transcribe.py")
    ap.add_argument("--audio", help="audio.json from audio.py (for dead air)")
    ap.add_argument("--profile", help="styles/<name>/profile.json")
    ap.add_argument("--out")
    ap.add_argument("--max-silence", type=float, default=None,
                    help="override the profile's dead-air tolerance (seconds)")
    ap.add_argument("--aggressive", action="store_true",
                    help="also strip like/basically/literally/actually/so")
    ap.add_argument("--no-retakes", action="store_true")
    ap.add_argument("--no-fillers", action="store_true")
    ap.add_argument("--guard", type=float, default=GUARD_SEC)
    args = ap.parse_args()

    wdoc = load_json(args.words)
    words = wdoc["words"]
    if not words:
        raise RuntimeError("transcript has no words")

    profile = load_json(args.profile) if args.profile else {}
    max_silence = args.max_silence
    if max_silence is None:
        max_silence = (profile.get("pacing", {}) or {}).get("max_silence_sec", 0.35)

    adoc = load_json(args.audio) if args.audio else {}
    duration = adoc.get("duration_sec") or (words[-1]["end"] + 0.5)

    cuts = []
    if not args.no_retakes:
        cuts += find_retakes(words, MIN_RETAKE_RUN, RETAKE_GAP_WORDS)
    if not args.no_fillers:
        cuts += find_fillers(words, args.aggressive)
    if adoc.get("silences"):
        cuts += find_dead_air(adoc["silences"], max_silence, duration)

    raw_cuts = sorted(cuts, key=lambda c: c["start"])
    merged = merge(raw_cuts)
    keeps = invert(merged, duration, args.guard)

    removed = sum(c["end"] - c["start"] for c in merged)
    out_dur = sum(k["dur"] for k in keeps)

    stats = {}
    for c in raw_cuts:
        stats[c["reason"]] = stats.get(c["reason"], 0) + 1

    result = {
        "source": wdoc.get("source"),
        "source_duration_sec": round(duration, 3),
        "output_duration_sec": round(out_dur, 3),
        "removed_sec": round(removed, 3),
        "removed_pct": round(100 * removed / duration, 1) if duration else 0,
        "params": {
            "max_silence_sec": max_silence,
            "aggressive_fillers": args.aggressive,
            "guard_sec": args.guard,
        },
        "stats": stats,
        "cuts": [
            {**c, "start": round(c["start"], 3), "end": round(c["end"], 3),
             "dur": round(c["end"] - c["start"], 3)}
            for c in raw_cuts
        ],
        "keep": keeps,
    }

    # Human-readable summary on stderr — this is what gets shown for approval
    # before anything is rendered.
    print(f"\n{'':-<66}", file=sys.stderr)
    print(f"{len(raw_cuts)} cuts, {result['removed_sec']}s removed "
          f"({result['removed_pct']}%)  "
          f"{round(duration,1)}s -> {result['output_duration_sec']}s",
          file=sys.stderr)
    print(f"{'':-<66}", file=sys.stderr)
    for c in raw_cuts:
        print(f"  {ts(c['start'])}-{ts(c['end'])}  {c['reason']:<9} "
              f"{c['detail']}", file=sys.stderr)
    print(f"{'':-<66}\n", file=sys.stderr)

    emit(result, args.out)


if __name__ == "__main__":
    main_guard(cli)
