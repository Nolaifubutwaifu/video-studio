"""Shared helpers for the video-studio tools.

Deliberately stdlib-only: every tool here is a thin wrapper over the ffmpeg /
ffprobe / whisper / yt-dlp binaries that are already on the machine. Keeping the
dependency surface at zero means these keep working after a Python upgrade.
"""
import json
import os
import shutil
import subprocess
import sys


class ToolError(RuntimeError):
    pass


def need(binary):
    """Fail loudly and early if a required binary is missing."""
    path = shutil.which(binary)
    if not path:
        raise ToolError(
            f"required binary {binary!r} not found on PATH.\n"
            f"  ffmpeg/ffprobe: brew install ffmpeg\n"
            f"  yt-dlp:         pip install -U yt-dlp\n"
            f"  whisper:        pip install -U openai-whisper"
        )
    return path


def run(cmd, capture=True, check=True, quiet=False):
    """Run a command, raising ToolError with real stderr on failure."""
    if not quiet:
        print(f"$ {' '.join(str(c) for c in cmd)}", file=sys.stderr)
    proc = subprocess.run(
        [str(c) for c in cmd],
        capture_output=capture,
        text=True,
    )
    if check and proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-25:]
        raise ToolError(
            f"{cmd[0]} exited {proc.returncode}\n" + "\n".join(tail)
        )
    return proc


def ffprobe_json(path):
    need("ffprobe")
    proc = run([
        "ffprobe", "-v", "error",
        "-print_format", "json",
        "-show_format", "-show_streams",
        path,
    ], quiet=True)
    return json.loads(proc.stdout)


def video_stream(probe):
    for s in probe.get("streams", []):
        if s.get("codec_type") == "video":
            return s
    raise ToolError("no video stream found")


def audio_stream(probe):
    for s in probe.get("streams", []):
        if s.get("codec_type") == "audio":
            return s
    return None


def parse_fps(rate):
    """'30000/1001' -> 29.97"""
    if not rate:
        return None
    if "/" in str(rate):
        num, den = str(rate).split("/")
        den = float(den)
        return round(float(num) / den, 4) if den else None
    return float(rate)


def duration_of(probe):
    fmt = probe.get("format", {})
    if fmt.get("duration"):
        return float(fmt["duration"])
    for s in probe.get("streams", []):
        if s.get("duration"):
            return float(s["duration"])
    raise ToolError("could not determine duration")


def emit(obj, out=None):
    """Write JSON to a file if requested, and always print it to stdout."""
    text = json.dumps(obj, indent=2)
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w") as fh:
            fh.write(text + "\n")
        print(f"wrote {out}", file=sys.stderr)
    print(text)
    return obj


def load_json(path):
    with open(path) as fh:
        return json.load(fh)


def ts(seconds):
    """Seconds -> mm:ss.mmm, for human-readable summaries."""
    seconds = max(0.0, float(seconds))
    m, s = divmod(seconds, 60)
    return f"{int(m):02d}:{s:06.3f}"


def main_guard(fn):
    """Uniform error reporting for every tool's entrypoint."""
    try:
        fn()
    except ToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
