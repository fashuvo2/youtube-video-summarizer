# YouTube Watch Later Summarizer — Design Spec
**Date:** 2026-04-20

## Overview

A GitHub Actions-based automation that detects new videos in a YouTube Watch Later playlist, generates short Bengali summaries using Claude, and posts them to a public Telegram channel. Triggered manually via `workflow_dispatch` from the GitHub mobile app or web UI.

---

## Architecture

```
GitHub Actions (manual trigger — workflow_dispatch)
        │
        ▼
  src/main.py (orchestrator)
        │
        ├── src/youtube_client.py     ──► fetch Watch Later playlist (YouTube Data API v3, OAuth)
        ├── seen_videos.json          ──► filter already-processed video IDs
        ├── src/transcript_fetcher.py ──► fetch transcript (manual captions → auto-captions → None)
        ├── src/summarizer.py         ──► generate Bengali summary via Claude API
        └── src/telegram_client.py   ──► post formatted message to public Telegram channel

After run: commit updated seen_videos.json back to repo with [skip ci]
```

---

## File Structure

```
youtube-video-summarizer/
├── .github/
│   └── workflows/
│       └── summarize.yml            # workflow_dispatch trigger
├── src/
│   ├── main.py                      # orchestrator
│   ├── youtube_client.py            # YouTube Data API v3 integration
│   ├── transcript_fetcher.py        # transcript fetching with fallback
│   ├── summarizer.py                # Claude API Bengali summarization
│   └── telegram_client.py          # Telegram Bot API integration
├── auth/
│   └── get_refresh_token.py         # one-time local script to obtain OAuth refresh token
├── seen_videos.json                 # persisted list of processed video IDs — format: ["id1", "id2", ...]
├── requirements.txt
└── .env.example                     # documents required env vars (no actual secrets)
```

---

## Components

### `src/youtube_client.py`
- Authenticates with Google OAuth using a stored refresh token (no browser re-auth needed after initial setup)
- Fetches the Watch Later playlist (`WL`) via YouTube Data API v3
- Returns a list of `{"id": str, "title": str, "channel": str}` dicts

### `src/transcript_fetcher.py`
- Uses `youtube-transcript-api` to fetch transcript for a given video ID
- Tries manually-uploaded captions first, then auto-generated captions
- Returns full transcript text as a single string, or `None` if neither is available

### `src/summarizer.py`
- Takes video metadata (`title`, `channel`) and transcript text
- Calls Claude API (`claude-haiku-4-5-20251001`) to generate a Bengali summary of 3–5 sentences (~80–120 words)
- Returns the Bengali summary string

### `src/telegram_client.py`
- Takes a formatted message string
- Posts to the configured public Telegram channel via Bot API
- Retries once on failure before giving up

### `src/main.py`
- Loads `seen_videos.json`
- Fetches Watch Later playlist and filters to unseen videos only
- For each new video:
  - Fetches transcript
  - If transcript found: generates Bengali summary via Claude
  - If no transcript: uses a fallback message ("প্রতিলিপি পাওয়া যায়নি")
  - Posts to Telegram
  - Adds video ID to seen list only on successful post
- Saves updated `seen_videos.json`

### `auth/get_refresh_token.py`
- One-time local script
- Launches browser OAuth flow using `google-auth-oauthlib`
- Prints the refresh token to stdout for the user to copy into GitHub Secrets

---

## Data Flow

```
1. Fetch all video IDs from Watch Later playlist
2. Load seen_videos.json → filter to unseen IDs only
3. For each new video:
   a. Fetch transcript
      → found:     send to Claude → Bengali summary
      → not found: use fallback text "প্রতিলিপি পাওয়া যায়নি"
   b. Post formatted message to Telegram channel
   c. On success: add video ID to seen list
4. Save updated seen_videos.json
5. Git commit seen_videos.json with "[skip ci]"
```

---

## Telegram Message Format

```
🎬 *Video Title*
📺 Channel Name

Bengali summary text here...

🔗 https://youtu.be/VIDEO_ID
```

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| YouTube API failure | Action fails loudly; GitHub emails the user |
| Single transcript fetch failure | Log error, skip video, continue with rest |
| Single Claude API failure | Log error, skip video, continue with rest |
| Telegram post failure | Retry once; if still failing, skip and log |
| `seen_videos.json` only updated for successfully posted videos | Failed videos are retried on next run |

---

## GitHub Actions Workflow

```yaml
name: Summarize New Watch Later Videos

on:
  workflow_dispatch:

jobs:
  summarize:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python src/main.py
        env:
          GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_ID }}
          GOOGLE_CLIENT_SECRET: ${{ secrets.GOOGLE_CLIENT_SECRET }}
          GOOGLE_REFRESH_TOKEN: ${{ secrets.GOOGLE_REFRESH_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHANNEL_USERNAME: ${{ secrets.TELEGRAM_CHANNEL_USERNAME }}
      - name: Commit updated seen_videos.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add seen_videos.json
          git diff --staged --quiet || git commit -m "chore: update seen videos [skip ci]"
          git push
```

---

## Required GitHub Secrets

| Secret | Purpose |
|---|---|
| `GOOGLE_CLIENT_ID` | YouTube Data API OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | YouTube Data API OAuth client secret |
| `GOOGLE_REFRESH_TOKEN` | Long-lived OAuth token (obtained via `auth/get_refresh_token.py`) |
| `ANTHROPIC_API_KEY` | Claude API key for Bengali summarization |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token (from BotFather) |
| `TELEGRAM_CHANNEL_USERNAME` | Public channel username e.g. `@mychannel` |

---

## Dependencies (`requirements.txt`)

```
google-api-python-client
google-auth-oauthlib
youtube-transcript-api
anthropic
requests
```

---

## One-Time Setup Steps

1. Create a Google Cloud project and enable YouTube Data API v3
2. Create OAuth 2.0 credentials (Desktop app type)
3. Run `python auth/get_refresh_token.py` locally → copy the printed refresh token
4. Create a Telegram bot via BotFather → copy the bot token
5. Add bot as admin to your public Telegram channel
6. Add all secrets to GitHub repository Settings → Secrets
