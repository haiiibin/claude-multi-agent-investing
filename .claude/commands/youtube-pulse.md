---
description: Summarize latest videos from tracked YouTube channels and extract short-term investment signals relevant to current holdings. Run after /market-pulse for context, or standalone for a quick opinion check.
---

# /youtube-pulse -- YouTube Channel Digest

Pulls the latest content from tracked channels and extracts views relevant to your holdings.

## Arguments

- No argument → scan all channels below
- `$ARGUMENTS` = channel name/handle → scan only that channel (partial match OK, e.g. `美投` matches 美投君 + 美投News)

---

## Tracked channels (hardcoded -- do not read from file)

| Channel | Handle | Channel ID | RSS feed |
|---|---|---|---|
| 阳光财经 | @SUNNYFINANCE | UC2I5em6UyBpQiO-8ZW0nV3w | `https://www.youtube.com/feeds/videos.xml?channel_id=UC2I5em6UyBpQiO-8ZW0nV3w` |
| 视野环球财经 | @RhinoFinance | UCFQsi7WaF5X41tcuOryDk8w | `https://www.youtube.com/feeds/videos.xml?channel_id=UCFQsi7WaF5X41tcuOryDk8w` |
| 美投君 | @MeiTouJun | UCBUH38E0ngqvmTqdchWunwQ | `https://www.youtube.com/feeds/videos.xml?channel_id=UCBUH38E0ngqvmTqdchWunwQ` |
| 美投News | @MeiTouNews | UCGpj3DO_5_TUDCNUgS9mjiQ | `https://www.youtube.com/feeds/videos.xml?channel_id=UCGpj3DO_5_TUDCNUgS9mjiQ` |
| 贝拉聊财金 | @bellafinance | UCVomjkM_t0EcctTWSE1Jvxg | `https://www.youtube.com/feeds/videos.xml?channel_id=UCVomjkM_t0EcctTWSE1Jvxg` |

---

## Prerequisites (one-time setup)

These must be installed before the command works:
```
pip install yt-dlp openai-whisper youtube-transcript-api
winget install Gyan.FFmpeg
```

Verify: `ffmpeg -version` and `yt-dlp --version` both return output.

---

## Steps

### 1. Load holdings context

Read `portfolio/holdings.json` -- extract all `ticker` fields. Resolve CDRs to underlying (NVDA.NE → NVDA, COST.NE → COST). Build a watchlist of tickers and tags for cross-reference in Step 5.

### 2. Fetch RSS feeds (all channels in parallel)

For each channel, `WebFetch` its RSS URL with this prompt:

> "Extract video ID and title for all entries. Format: VIDEO_ID | YYYY-MM-DD | title. The video ID is in the <yt:videoId> tag."

**Why RSS:**
- `site:youtube.com` searches return sparse results and no dates
- Direct `WebFetch` on `youtube.com/watch?v=ID` only returns page footer (JavaScript-rendered -- useless)
- Video descriptions in RSS are pure boilerplate (membership promos, disclaimers) -- no investment content
- RSS feeds return exact dates + titles + IDs for the ~15 most recent videos reliably

Apply recency gate: keep only videos published in the last **14 days**. Note any channel with no recent videos as `[no new content since {last date}]`.

### 3. Transcribe each video (yt-dlp + Whisper)

**Why this approach:**
- All 5 tracked channels have disabled ALL subtitle options (manual CC + auto-generated captions)
- `youtube-transcript-api` returns `TranscriptsDisabled` for every video
- yt-dlp `--list-subs` confirms "no automatic captions, no subtitles"
- The only way to get these creators' actual opinions is audio transcription

For each video within the 14-day window, run this Python script:

```python
import subprocess, whisper, os, sys

video_id = sys.argv[1]
out_path = f"memory/short_term/audio_{video_id}"

# Step 1: download audio only (no video)
subprocess.run([
    "yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "5",
    "-o", f"{out_path}.%(ext)s",
    f"https://www.youtube.com/watch?v={video_id}"
], check=True)

# Step 2: transcribe with Whisper
model = whisper.load_model("small")  # 461MB, good accuracy for Chinese
result = model.transcribe(f"{out_path}.mp3", language="zh", fp16=False)
transcript = result["text"]

# Step 3: save transcript
with open(f"{out_path}_transcript.txt", "w", encoding="utf-8") as f:
    f.write(transcript)

# Step 4: clean up audio
os.remove(f"{out_path}.mp3")
print(transcript)
```

Run as: `python tools/transcribe.py {VIDEO_ID}`

Save this script to `tools/transcribe.py`.

**Model selection:**
- `small` (461MB): good for Chinese, fast enough on CPU (~2-4 min per 30-min video)
- `medium` (1.5GB): better accuracy, use if small produces errors
- `large` (2.9GB): highest accuracy, slow on CPU

**Batch processing:** For multiple videos in one pulse run, process sequentially (Whisper is CPU-intensive). Do not parallelize transcription jobs.

**Audio file size:** typical 30-min financial video = ~20-25MB webm. Download takes seconds on fast connection. Transcription takes 2-5 min on CPU. Delete audio after transcription.

### 4. Summarize each video

For each video produce a compact summary:
- **Main thesis** (1 sentence): the central claim or actionable takeaway
- **Tickers**: every ticker or company named, with directional signal (+/−/=)
- **Catalyst / timeframe**: what event or date the creator anchors on
- **Key numbers**: specific metrics, prices, %, capex figures cited
- **Content confidence**: `High` (article found) / `Medium` (search summary) / `Low` (title only)

Keep language dense. No filler sentences.

### 5. Cross-reference with holdings

After all channels are summarized, produce a **Holdings Relevance Map**:

For each holding in the watchlist, note which channels mentioned it and the sentiment:

```
NVDA    → 美投News (让位/bearish signal), 视野环球 (capex confirmed/bullish)
TSLA    → 视野环球 (FCF转负/bearish), 美投君 (大变动/bearish)
QQQ     → [via Nasdaq-100 theme]
```

Tickers with no coverage this cycle → note as **No coverage**.

### 6. Signal synthesis

Produce a **Signal Summary** table (max 12 rows, sorted by conviction):

```markdown
| Ticker / Theme | Signal | Source(s) | Timeframe | Action hint |
|---|---|---|---|---|
| NVDA | ⚠️ 分歧 | 美投News (让位) vs Rhino (capex+) | 近期 | Watch |
| TSLA | 偏空 | 视野环球 + 美投君 | 近期 | Review thesis |
| 大盘 | 谨慎 | 贝拉 + 视野 | 1–2周 | Watch |
```

**Action hint vocabulary** (use exactly):
- `Hold` -- thesis intact, no change needed
- `Hold / add on dip` -- bullish but wait for entry point
- `Watch` -- monitor closely, no action yet
- `Review thesis` -- creator raised concerns worth checking against your original thesis
- `Consider trim` -- bearish signal on a held position
- `No signal` -- not mentioned or neutral

### 7. Output format

```markdown
# 📺 YouTube Pulse -- {YYYY-MM-DD}

## 覆盖频道
- 阳光财经: 最新至 {date} [N条新视频 / 无新内容]
- 视野环球财经: N条新视频 [{date range}]
- 美投君: ...
- 美投News: ...
- 贝拉聊财金: ...

---

## 频道摘要

### 阳光财经 (@SUNNYFINANCE)

| 日期 | 标题 | 主要论点 | 关键数据 | 情绪 | 置信度 |
|---|---|---|---|---|---|
| {date} | {title} | {1句核心观点} | {具体数字/指标} | 看涨/看跌/中性 | High/Med/Low |

### 视野环球财经 (@RhinoFinance)
...

(repeat for all channels)

---

## 持仓关联图

| 持仓 | 提及频道 | 情绪 | 日期 |
|---|---|---|---|
| NVDA | 美投News, 视野环球 | 分歧 | 2026-05-02 |

---

## 信号汇总

| Ticker / 主题 | 信号 | 来源 | 时间框架 | Action hint |
|---|---|---|---|---|

---

## 数据质量
- 每个频道注明：RSS确认日期 + 内容置信度（High/Med/Low）
```

### 8. Save

Save output to `memory/short_term/{YYYY-MM-DD}-youtube-pulse.md`.

---

## Rules

- **Never fabricate video content.** If no third-party content found for a video, use title analysis only and mark `[content: title only]`.
- **Never WebFetch youtube.com/watch URLs** -- they only return page footer due to JS rendering. Use WebSearch + third-party article fetch instead.
- **RSS is the authoritative source for dates.** The RSS feed gives exact publish timestamps. Never guess or infer dates from search snippets.
- **CDR resolution**: NVDA.NE mentions of "NVIDIA" map to NVDA exposure. Always resolve to underlying ticker.
- **Output language**: Summaries in Chinese (matching the channels). Signal table in English for consistency with other commands.
- **Recency gate**: Only include videos published within the last 14 days. Older content → skip.
- **Unclear sentiment**: If title is ambiguous and no content found, mark sentiment as `[unclear]` -- never guess.
- **Cross-channel convergence matters**: When 2+ channels independently arrive at the same signal on the same ticker/theme, elevate conviction. Note convergence explicitly.
- **These are opinion signals from content creators, not investment advice.** Always cross-check with `/research TICKER` before acting.
