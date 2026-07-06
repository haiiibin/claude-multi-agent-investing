"""
Transcribe a YouTube video using yt-dlp + Whisper.
Usage: python tools/transcribe.py <VIDEO_ID> [--model small|medium|large]

Output: prints transcript to stdout, saves to memory/short_term/audio_{VIDEO_ID}_transcript.txt
Audio file is deleted after transcription.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _ensure_ffmpeg_in_path():
    """Auto-detect ffmpeg from WinGet install location if not already on PATH."""
    import shutil
    if shutil.which("ffmpeg"):
        return
    winget_base = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    for pkg in winget_base.glob("Gyan.FFmpeg_*/ffmpeg-*/bin"):
        if (pkg / "ffmpeg.exe").exists():
            os.environ["PATH"] = str(pkg) + os.pathsep + os.environ.get("PATH", "")
            return


def transcribe(video_id: str, model_name: str = "small") -> str:
    _ensure_ffmpeg_in_path()
    import whisper

    base_dir = Path(__file__).parent.parent
    out_dir = base_dir / "memory" / "short_term"
    out_dir.mkdir(parents=True, exist_ok=True)

    audio_path = out_dir / f"audio_{video_id}.webm"
    transcript_path = out_dir / f"audio_{video_id}_transcript.txt"

    if transcript_path.exists():
        print(f"[cache] Using existing transcript: {transcript_path}", file=sys.stderr)
        return transcript_path.read_text(encoding="utf-8")

    # Download audio
    print(f"[yt-dlp] Downloading audio for {video_id}...", file=sys.stderr)
    result = subprocess.run(
        [
            "yt-dlp", "-x",
            "--no-update",
            "--extractor-args", "youtube:player_client=android",
            "--no-post-overwrites",
            "-o", str(out_dir / f"audio_{video_id}.%(ext)s"),
            f"https://www.youtube.com/watch?v={video_id}",
        ],
        capture_output=True, text=True
    )
    if result.returncode != 0 and not audio_path.exists():
        # find whatever was downloaded
        candidates = list(out_dir.glob(f"audio_{video_id}.*"))
        candidates = [f for f in candidates if f.suffix not in (".txt",)]
        if not candidates:
            raise RuntimeError(f"yt-dlp failed:\n{result.stderr}")
        audio_path = candidates[0]

    # Find downloaded file (may be .webm, .m4a, .opus, etc.)
    if not audio_path.exists():
        candidates = list(out_dir.glob(f"audio_{video_id}.*"))
        candidates = [f for f in candidates if f.suffix not in (".txt",)]
        if not candidates:
            raise RuntimeError("No audio file found after download")
        audio_path = candidates[0]

    print(f"[whisper] Loading model '{model_name}'...", file=sys.stderr)
    model = whisper.load_model(model_name)

    print(f"[whisper] Transcribing {audio_path.name} ({audio_path.stat().st_size // 1024 // 1024}MB)...", file=sys.stderr)
    transcription = model.transcribe(str(audio_path), language="zh", fp16=False)
    text = transcription["text"]

    transcript_path.write_text(text, encoding="utf-8")
    print(f"[done] Saved to {transcript_path}", file=sys.stderr)

    # Clean up audio
    audio_path.unlink(missing_ok=True)

    return text


def main():
    parser = argparse.ArgumentParser(description="Transcribe a YouTube video")
    parser.add_argument("video_id", help="YouTube video ID (e.g. lNbyi_hqSuc)")
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size (default: small)")
    args = parser.parse_args()

    text = transcribe(args.video_id, args.model)
    print(text)


if __name__ == "__main__":
    main()
