---
name: script-write
description: Write a spoken script for a topic in a learned reference style. Use when the user picks a topic for a video, or asks for a script, hook, or teleprompter text.
---

# script-write

Writes a script the user will read aloud, shaped by a learned style profile.

## 1. Load the style

Read `styles/<name>/profile.json`. Its `script` block holds the hook formula,
structure beats, sentence length, CTA pattern and locale; `pacing.wpm` sets the
speaking rate. If no profile exists yet, say so and offer to run `/style-learn`
first — writing blind defeats the point.

## 2. Draft three variants in parallel

Launch three subagents in one message, each writing a complete script with a
different hook angle. Give every one of them the same hard constraints:

- Target duration in seconds → word budget = `wpm * seconds / 60`
- Average sentence length from the profile (short declaratives, usually)
- The structure beats, in order
- Verbatim hook and CTA examples from the profile, as patterns to imitate —
  not lines to reuse
- The locale (`en-AU` by default: Australian spelling and idiom)

## 3. Merge and write

Pick the strongest hook, and take the best sections from each draft. Do not
present three options and ask the user to choose unless they genuinely are
close — make the call, and say briefly why.

Write `projects/<slug>/script.md`:

```markdown
# <topic>

**Style:** <style name> · **Target:** 45s · **Budget:** ~124 words @ 165 wpm
**Actual:** 119 words → ~43s

## Teleprompter
<the script as one clean block of plain prose, no markup, no stage
directions — this is what gets read aloud>

## Beats
| Beat | Line | Est. | Shot note |
|------|------|------|-----------|
| Hook | ... | 0-4s | tight, straight to camera |

## B-roll shot list
- ...
```

The teleprompter block matters: it is read on camera, so anything that is not
spoken words does not belong in it.

## 4. Sanity-check the length

Compare the word count against the budget. Social video runs long far more
often than short — if the draft is over budget, cut it before handing it over
rather than letting the user discover it while recording.
