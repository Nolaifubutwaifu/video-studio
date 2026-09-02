---
name: edit-cut
description: Cut a raw recorded take - remove retakes, filler words and dead air - and produce an edit decision list. Use when the user hands over a recording to be edited.
---

# edit-cut

Turns a raw take into a tight cut, plus an EDL the user can adjust.

## 1. Transcribe and measure

```bash
P=projects/<slug>
python3 tools/transcribe.py TAKE.mp4 --model small.en --out $P/words.json
python3 tools/audio.py TAKE.mp4 --out $P/audio.json
```

Use `small.en`. `tiny.en` is roughly 5x realtime but mishears disfluencies —
it transcribed "um" as "Bum" and "uh" as "er" in testing, so the filler pass
silently misses them. `small.en` got both right.

## 2. Build the EDL

```bash
python3 tools/edl.py --words $P/words.json --audio $P/audio.json \
  --profile styles/<name>/profile.json --out $P/edl.json
```

It removes three things: **retakes** (a restarted phrase — the last attempt is
kept), **fillers** (um/uh/er), and **dead air** (pauses trimmed down to the
profile's tolerance, not deleted outright, because removing a beat entirely
sounds unnatural).

It is deliberately conservative. `like`, `basically`, `actually` and `so` are
left alone unless you pass `--aggressive`, because they are real words often
enough that stripping them unasked mangles honest sentences.

## 3. Get approval before rendering

`edl.py` prints a readable summary — every cut with its timestamp and reason.
**Show it to the user and get agreement before rendering anything.** A wrong
cut destroys a take; a missed one costs a second of runtime. The asymmetry is
the whole reason this step is a checkpoint.

If a cut is wrong, adjust and re-run rather than hand-editing `edl.json`:
- `--no-retakes` / `--no-fillers` to disable a whole pass
- `--max-silence 0.5` to keep more breathing room
- `--aggressive` to also strip discourse markers

## 4. Apply the cut

```bash
python3 tools/pretrim.py TAKE.mp4 --edl $P/edl.json --words $P/words.json \
  --outdir $P/work --hw
```

Produces `work/trimmed.mp4`, `work/timeline.json` and a **remapped**
`work/words.json`. The remap is not optional: whisper's timestamps refer to the
original take, and once ranges are removed every one of them is wrong. Always
pass `work/words.json` — not the original — to the renderer.

`--hw` uses `h264_videotoolbox`, which is much faster on Apple silicon. Drop it
if the intermediate looks soft.
