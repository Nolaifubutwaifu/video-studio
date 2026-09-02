---
name: render
description: Render the final video with captions and graphics, and hand over the editable Remotion project. Use after a take has been cut, or when the user wants to re-render or tweak an existing edit.
---

# render

Composites the cut take with captions and graphics, then normalises loudness.

## 1. Render

```bash
P=projects/<slug>
python3 tools/render.py \
  --video $P/work/trimmed.mp4 \
  --words $P/work/words.json \
  --profile styles/<name>/profile.json \
  --title "<optional on-screen title>" \
  --out $P/out/final.mp4
```

Pass the **remapped** `work/words.json`, never the original transcript, or
every caption lands late by the amount that was cut before it.

All text is drawn by Remotion. The ffmpeg build here has no libass or drawtext,
so there is no burned-subtitle fallback — do not reach for `-vf subtitles=`.

## 2. Hand over the editable project

Run `--props-only` and then `npm run studio` to open the same render in
Remotion's editor, where the user can scrub, adjust a caption, or change
colours live and re-render in seconds:

```bash
python3 tools/render.py ... --props-only
npm run studio
```

This is half the deliverable — mention it, rather than only handing over the
MP4.

## 3. Check the result

Do not just report success. Verify:

```bash
python3 tools/frames.py $P/out/final.mp4 --outdir /tmp/check --mode grid --count 8
```

Read the contact sheet and confirm captions are present, correctly positioned,
and legible. To check sync precisely, sample a frame at a known word's midpoint
from `work/words.json` and confirm that word is the highlighted one.

## Adjusting the look

Everything visual comes from the profile, so a change is a data edit, not a
code change:

| Want | Change |
|---|---|
| Bigger captions | `captions.sizePct` (percent of frame height) |
| Move captions up | `captions.yPct` (lower = higher on screen) |
| Different highlight colour | `captions.highlight` |
| Highlight box behind the word | `captions.highlightBox` (null disables) |
| Fewer words on screen | `captions.maxWordsOnScreen` |
| Thicker outline | `captions.stroke.widthPct` |
| Title card / progress bar | `graphics.titleCard`, `graphics.progressBar` |

Fonts must be in the registry in `remotion/src/fonts.ts` (Inter, Montserrat,
Poppins, Anton, Bebas Neue). An unregistered name falls back to a system stack
rather than failing, so if a font silently looks wrong, check there first.
