# video-studio

Make social videos that match a style you like: show it a few reference videos
once, then for each new video get a script, hand back your recording, and get a
finished cut with captions and graphics — plus an editable project to tweak.

## Requirements

macOS with `ffmpeg`, `yt-dlp`, `openai-whisper`, Node 20+, Python 3.9+.

```bash
npm install
```

## Use

```
/style-learn   # give it 3-5 reference videos (links or screen recordings)
/script        # pick a topic, get a script to read
   ...record yourself...
/edit          # hand back the take, review the cuts
/render        # get final.mp4 + the editable Remotion project
```

Or drive the tools directly:

```bash
# Learn a style
python3 tools/ingest.py "https://..." --outdir media/refs/mine
python3 tools/shots.py media/refs/mine/x.mp4 --out shots.json
python3 tools/frames.py media/refs/mine/x.mp4 --outdir frames --mode captions

# Cut a take
python3 tools/transcribe.py take.mp4 --model small.en --out words.json
python3 tools/audio.py take.mp4 --out audio.json
python3 tools/edl.py --words words.json --audio audio.json --out edl.json
python3 tools/pretrim.py take.mp4 --edl edl.json --words words.json --outdir work --hw

# Render
python3 tools/render.py --video work/trimmed.mp4 --words work/words.json \
  --profile styles/default/profile.json --out out/final.mp4

# Tweak by hand
npm run studio
```

## How the style works

Everything visual lives in `styles/<name>/profile.json` — caption font, size,
position, colours, stroke, chunk size, pacing targets, graphics toggles. Change
the data, not the code. `styles/default/profile.json` documents the schema.

## Notes

- All on-device: ffmpeg, whisper and Remotion. No API keys, nothing uploaded.
- Media is gitignored. Downloaded references are third-party copyrighted
  material kept locally for analysis only.
