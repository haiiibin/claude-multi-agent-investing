"""Batch transcribe YouTube videos via yt-dlp (android client) + faster-whisper.
Usage: python tools/batch_transcribe.py ID1 ID2 ...
Skips IDs already having audio_{id}_transcript.txt.
"""
import sys, subprocess, time
from pathlib import Path

BASE = Path(__file__).parent.parent
OUT = BASE / "memory" / "short_term"
OUT.mkdir(parents=True, exist_ok=True)

def download(vid):
    subprocess.run([
        "yt-dlp", "-x", "--no-update",
        "--extractor-args", "youtube:player_client=android",
        "--no-post-overwrites",
        "-o", str(OUT / f"audio_{vid}.%(ext)s"),
        f"https://www.youtube.com/watch?v={vid}",
    ], capture_output=True, text=True)
    cands = [f for f in OUT.glob(f"audio_{vid}.*") if f.suffix != ".txt"]
    return cands[0] if cands else None

def main(ids):
    from faster_whisper import WhisperModel
    print("loading faster-whisper small (int8)...", flush=True)
    model = WhisperModel("small", device="cpu", compute_type="int8")
    for i, vid in enumerate(ids, 1):
        tp = OUT / f"audio_{vid}_transcript.txt"
        if tp.exists():
            print(f"[{i}/{len(ids)}] {vid} cached, skip", flush=True); continue
        t = time.time()
        print(f"[{i}/{len(ids)}] {vid} downloading...", flush=True)
        audio = download(vid)
        if not audio:
            print(f"[{i}/{len(ids)}] {vid} DOWNLOAD FAILED", flush=True); continue
        print(f"[{i}/{len(ids)}] {vid} transcribing {audio.stat().st_size//1024//1024}MB...", flush=True)
        segments, info = model.transcribe(str(audio), language="zh", vad_filter=True)
        text = "".join(s.text for s in segments)
        tp.write_text(text, encoding="utf-8")
        audio.unlink(missing_ok=True)
        print(f"[{i}/{len(ids)}] {vid} DONE {len(text)} chars in {round(time.time()-t)}s", flush=True)
    print("ALL DONE", flush=True)

if __name__ == "__main__":
    main(sys.argv[1:])
