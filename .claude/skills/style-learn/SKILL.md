---
name: style-learn
description: Analyze reference videos (links or screen recordings) and build a reusable style profile. Use when the user provides reference videos, wants to teach the system a style, or says "learn this style".
---

# style-learn

Turns reference videos into `styles/<name>/profile.json` — the artifact every
later step reads.

## 1. Collect the references

Ask for a style name if the user has not given one. Then ingest each reference:

```bash
python3 tools/ingest.py "<url-or-path>" --outdir media/refs/<name>
```

Links may fail: Instagram and TikTok routinely block anonymous downloads.
`ingest.py` retries with Chrome cookies automatically. If it still fails, say
so plainly and ask for a screen recording instead — do not keep retrying.

Three to five references is the useful range. One is not enough to tell a
consistent style from a one-off choice; beyond five the analysis cost stops
buying accuracy.

## 2. Analyze each reference in parallel

Launch **one `video-style-analyst` agent per reference video, all in a single
message** so they run concurrently. Give each one its video path and its own
output directory (`styles/<name>/work/<i>/`).

This is the one place in the pipeline where subagents genuinely pay off: the
work is independent per video, it is vision-heavy, and the fan-out is real.

## 3. Merge the fragments

Read every `fragment.json`, then reconcile them yourself:

- **Numbers** (wpm, shot length, cuts/min, LUFS, sizePct, yPct) — use the
  median, not the mean. One outlier reference should not drag the profile.
- **Categorical choices** (caption mode, font, case, colours) — use the most
  common value. If the references genuinely disagree, that is a real finding:
  tell the user and ask which one they want, rather than averaging two styles
  into one that resembles neither.
- **Chrome** — anything a fragment listed in `chrome_regions` is discarded.
  Never let platform UI reach the profile.
- **Hooks and CTAs** — keep every verbatim example. The script writer needs
  several to imitate a pattern rather than copy one line.

Write `styles/<name>/profile.json` matching the schema in
`styles/default/profile.json`, plus `styles/<name>/style-notes.md`: a readable
description of the style, the evidence behind each choice, and the
disagreements you resolved.

## 4. Show your work

Show the user `style-notes.md` alongside a couple of reference contact sheets
and ask whether it actually describes their style. Getting this wrong is
expensive — every future script and edit inherits the error — so confirm
before moving on.

Note that `styles/<name>/frames/` is gitignored: the frames are stills from
third-party videos and this repo is public. The profile and notes are yours and
are committed.
