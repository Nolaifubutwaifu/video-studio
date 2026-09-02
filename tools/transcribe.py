#!/usr/bin/env python3
"""transcribe.py — word-level transcript of a video or audio file.

    python3 tools/transcribe.py TAKE.mp4 --out projects/foo/words.json

Word-level timestamps are the backbone of this whole pipeline: the editor uses
them to cut retakes and filler at word precision, and the renderer uses them to
drive word-by-word caption highlighting. Segment-level timing is not enough for
either, so --word_timestamps is always on.
"""
import argparse
import glob
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import emit, main_guard, need, run

# 16 kHz mono is what whisper resamples to internally; doing it up front with
# ffmpeg is faster and sidesteps odd container/codec combinations.
SAMPLE_RATE = 16000


def extract_audio(src, dest):
    need("ffmpeg")
    run([
        "ffmpeg", "-y", "-v", "error",
        "-i", src,
        "-vn",
        "-ac", "1",
        "-ar", str(SAMPLE_RATE),
        "-c:a", "pcm_s16le",
        dest,
    ])
    return dest


def run_whisper(wav, model, language, workdir):
    need("whisper")
    cmd = [
        "whisper", wav,
        "--model", model,
        "--word_timestamps", "True",
        "--output_format", "json",
        "--output_dir", workdir,
        "--verbose", "False",
    ]
    if language:
        cmd += ["--language", language]
    run(cmd, capture=True)

    hits = glob.glob(os.path.join(workdir, "*.json"))
    if not hits:
        raise RuntimeError(f"whisper produced no JSON in {workdir}")
    with open(hits[0]) as fh:
        return json.load(fh)


def normalize(raw, source, model):
    """Flatten whisper's segment tree into a flat, indexed word list."""
    words = []
    for seg in raw.get("segments", []):
        for w in seg.get("words", []):
            text = w.get("word", "")
            clean = text.strip()
            if not clean:
                continue
            words.append({
                "i": len(words),
                "word": clean,
                # Lowercased and stripped of punctuation — what the matching
                # logic in edl.py compares against.
                "key": re.sub(r"[^\w']", "", clean.lower()),
                "start": round(float(w["start"]), 3),
                "end": round(float(w["end"]), 3),
                "prob": round(float(w.get("probability", 0.0)), 3),
            })

    text = (raw.get("text") or "").strip()
    speech = sum(w["end"] - w["start"] for w in words)
    span = (words[-1]["end"] - words[0]["start"]) if words else 0.0

    return {
        "source": os.path.abspath(source),
        "model": model,
        "language": raw.get("language"),
        "text": text,
        "word_count": len(words),
        # Words per minute measured over the spoken span, not the file length —
        # this is the number the script writer matches against.
        "wpm": round(len(words) / (span / 60.0), 1) if span > 1 else None,
        "speech_sec": round(speech, 2),
        "span_sec": round(span, 2),
        "words": words,
    }


def cli():
    ap = argparse.ArgumentParser(description="Word-level transcript.")
    ap.add_argument("media")
    ap.add_argument("--out", help="write words.json here")
    ap.add_argument("--model", default="small.en",
                    help="whisper model (tiny.en/base.en/small.en/medium/large-v3). "
                         "small.en is the speed/accuracy sweet spot on Apple silicon.")
    ap.add_argument("--language", default=None,
                    help="force a language, e.g. en. Omit for auto-detect.")
    ap.add_argument("--keep-audio", metavar="PATH",
                    help="also keep the extracted 16k wav here")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory(prefix="vs-transcribe-") as tmp:
        wav = args.keep_audio or os.path.join(tmp, "audio.wav")
        if args.keep_audio:
            os.makedirs(os.path.dirname(os.path.abspath(wav)), exist_ok=True)
        extract_audio(args.media, wav)
        raw = run_whisper(wav, args.model, args.language, tmp)

    result = normalize(raw, args.media, args.model)
    if not result["words"]:
        print("warning: transcript is empty — is there speech in this file?",
              file=sys.stderr)
    print(f"{result['word_count']} words, {result['wpm']} wpm",
          file=sys.stderr)
    emit(result, args.out)


if __name__ == "__main__":
    main_guard(cli)
