# YouTube Watch Later Summarizer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a GitHub Actions workflow that reads a YouTube Watch Later playlist, summarizes new videos in Bengali using Claude, and posts them to a public Telegram channel.

**Architecture:** A Python script runs inside a `workflow_dispatch`-triggered GitHub Actions job. It loads seen video IDs from `seen_videos.json`, fetches the Watch Later playlist via YouTube Data API v3 (OAuth refresh token), fetches transcripts via `youtube-transcript-api`, summarizes with Claude Haiku, posts to Telegram, and commits the updated `seen_videos.json` back to the repo.

**Tech Stack:** Python 3.12, `google-api-python-client`, `google-auth-oauthlib`, `youtube-transcript-api`, `anthropic`, `requests`, `pytest`

---

## File Map

| File | Responsibility |
|---|---|
| `src/youtube_client.py` | Authenticate via OAuth refresh token; fetch Watch Later playlist items |
| `src/transcript_fetcher.py` | Fetch transcript for a video ID; prefer manual captions, fall back to auto |
| `src/summarizer.py` | Call Claude Haiku to generate a 3–5 sentence Bengali summary |
| `src/telegram_client.py` | Post a formatted HTML message to a Telegram channel; retry once on failure |
| `src/main.py` | Orchestrate: load state → filter new → process → save state |
| `auth/get_refresh_token.py` | One-time local script to generate Google OAuth refresh token |
| `.github/workflows/summarize.yml` | `workflow_dispatch` trigger; run `main.py`; commit `seen_videos.json` |
| `tests/conftest.py` | Shared `autouse` fixture that injects all required env vars |
| `tests/test_youtube_client.py` | Unit tests for `get_watch_later_videos` |
| `tests/test_transcript_fetcher.py` | Unit tests for `fetch_transcript` |
| `tests/test_summarizer.py` | Unit tests for `summarize_in_bengali` |
| `tests/test_telegram_client.py` | Unit tests for `send_message` |
| `tests/test_main.py` | Unit tests for orchestration logic |
| `requirements.txt` | All runtime + test dependencies |
| `.env.example` | Documents required environment variables |
| `seen_videos.json` | Initial empty state: `[]` |

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `seen_videos.json`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create requirements.txt**

```
google-api-python-client>=2.0.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.2.0
youtube-transcript-api>=0.6.0
anthropic>=0.40.0
requests>=2.31.0
pytest>=8.0.0
```

- [ ] **Step 2: Create .env.example**

```
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REFRESH_TOKEN=your_google_refresh_token
ANTHROPIC_API_KEY=your_anthropic_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHANNEL_USERNAME=@your_channel_username
```

- [ ] **Step 3: Create seen_videos.json**

```json
[]
```

- [ ] **Step 4: Create src/__init__.py and tests/__init__.py**

Both files are empty.

- [ ] **Step 5: Create tests/conftest.py**

```python
import pytest


@pytest.fixture(autouse=True)
def env_vars(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "test_refresh_token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_api_key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ")
    monkeypatch.setenv("TELEGRAM_CHANNEL_USERNAME", "@testchannel")
```

- [ ] **Step 6: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: All packages install without errors.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example seen_videos.json src/__init__.py tests/__init__.py tests/conftest.py
git commit -m "chore: project scaffold"
```

---

## Task 2: YouTube Client

**Files:**
- Create: `src/youtube_client.py`
- Create: `tests/test_youtube_client.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_youtube_client.py`:

```python
from unittest.mock import MagicMock, patch
from src.youtube_client import get_watch_later_videos


@patch("src.youtube_client.get_youtube_service")
def test_get_watch_later_videos_returns_video_list(mock_get_service):
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service

    mock_service.channels.return_value.list.return_value.execute.return_value = {
        "items": [{"contentDetails": {"relatedPlaylists": {"watchLater": "WLxyz"}}}]
    }
    mock_service.playlistItems.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "snippet": {
                    "resourceId": {"videoId": "abc123"},
                    "title": "Test Video",
                    "videoOwnerChannelTitle": "Test Channel",
                }
            }
        ]
    }

    videos = get_watch_later_videos()

    assert videos == [{"id": "abc123", "title": "Test Video", "channel": "Test Channel"}]


@patch("src.youtube_client.get_youtube_service")
def test_get_watch_later_videos_handles_pagination(mock_get_service):
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service

    mock_service.channels.return_value.list.return_value.execute.return_value = {
        "items": [{"contentDetails": {"relatedPlaylists": {"watchLater": "WLxyz"}}}]
    }

    def playlist_side_effect(**kwargs):
        mock = MagicMock()
        if kwargs.get("pageToken") == "page2":
            mock.execute.return_value = {
                "items": [
                    {
                        "snippet": {
                            "resourceId": {"videoId": "vid2"},
                            "title": "Video 2",
                            "videoOwnerChannelTitle": "Channel 2",
                        }
                    }
                ]
            }
        else:
            mock.execute.return_value = {
                "items": [
                    {
                        "snippet": {
                            "resourceId": {"videoId": "vid1"},
                            "title": "Video 1",
                            "videoOwnerChannelTitle": "Channel 1",
                        }
                    }
                ],
                "nextPageToken": "page2",
            }
        return mock

    mock_service.playlistItems.return_value.list.side_effect = playlist_side_effect

    videos = get_watch_later_videos()

    assert len(videos) == 2
    assert videos[0]["id"] == "vid1"
    assert videos[1]["id"] == "vid2"


@patch("src.youtube_client.get_youtube_service")
def test_get_watch_later_videos_handles_missing_channel_title(mock_get_service):
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service

    mock_service.channels.return_value.list.return_value.execute.return_value = {
        "items": [{"contentDetails": {"relatedPlaylists": {"watchLater": "WLxyz"}}}]
    }
    mock_service.playlistItems.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "snippet": {
                    "resourceId": {"videoId": "del1"},
                    "title": "Deleted video",
                    # videoOwnerChannelTitle is absent for deleted videos
                }
            }
        ]
    }

    videos = get_watch_later_videos()

    assert videos[0]["channel"] == "Unknown Channel"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_youtube_client.py -v`
Expected: FAIL with `ImportError` or `ModuleNotFoundError`

- [ ] **Step 3: Implement src/youtube_client.py**

```python
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


def get_youtube_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def get_watch_later_videos() -> list[dict]:
    service = get_youtube_service()

    channels_resp = service.channels().list(part="contentDetails", mine=True).execute()
    playlist_id = channels_resp["items"][0]["contentDetails"]["relatedPlaylists"]["watchLater"]

    videos = []
    page_token = None

    while True:
        kwargs = {"part": "snippet", "playlistId": playlist_id, "maxResults": 50}
        if page_token:
            kwargs["pageToken"] = page_token

        resp = service.playlistItems().list(**kwargs).execute()

        for item in resp.get("items", []):
            snippet = item["snippet"]
            videos.append({
                "id": snippet["resourceId"]["videoId"],
                "title": snippet.get("title", "Unknown Title"),
                "channel": snippet.get("videoOwnerChannelTitle", "Unknown Channel"),
            })

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return videos
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_youtube_client.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/youtube_client.py tests/test_youtube_client.py
git commit -m "feat: add YouTube Watch Later client"
```

---

## Task 3: Transcript Fetcher

**Files:**
- Create: `src/transcript_fetcher.py`
- Create: `tests/test_transcript_fetcher.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_transcript_fetcher.py`:

```python
from unittest.mock import MagicMock, patch
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled
from src.transcript_fetcher import fetch_transcript


@patch("src.transcript_fetcher.YouTubeTranscriptApi.list_transcripts")
def test_fetch_transcript_returns_joined_text(mock_list):
    mock_transcript = MagicMock()
    mock_transcript.is_generated = False
    mock_transcript.fetch.return_value = [
        {"text": "Hello", "start": 0.0, "duration": 1.0},
        {"text": "World", "start": 1.0, "duration": 1.0},
    ]
    mock_list.return_value = [mock_transcript]

    result = fetch_transcript("abc123")

    assert result == "Hello World"


@patch("src.transcript_fetcher.YouTubeTranscriptApi.list_transcripts")
def test_fetch_transcript_prefers_manual_over_auto(mock_list):
    manual = MagicMock()
    manual.is_generated = False
    manual.fetch.return_value = [{"text": "Manual", "start": 0.0, "duration": 1.0}]

    auto = MagicMock()
    auto.is_generated = True
    auto.fetch.return_value = [{"text": "Auto", "start": 0.0, "duration": 1.0}]

    mock_list.return_value = [auto, manual]

    result = fetch_transcript("abc123")

    assert result == "Manual"


@patch("src.transcript_fetcher.YouTubeTranscriptApi.list_transcripts")
def test_fetch_transcript_falls_back_to_auto_captions(mock_list):
    auto = MagicMock()
    auto.is_generated = True
    auto.fetch.return_value = [{"text": "Auto caption text", "start": 0.0, "duration": 2.0}]
    mock_list.return_value = [auto]

    result = fetch_transcript("abc123")

    assert result == "Auto caption text"


@patch("src.transcript_fetcher.YouTubeTranscriptApi.list_transcripts")
def test_fetch_transcript_returns_none_when_disabled(mock_list):
    mock_list.side_effect = TranscriptsDisabled("abc123")

    result = fetch_transcript("abc123")

    assert result is None


@patch("src.transcript_fetcher.YouTubeTranscriptApi.list_transcripts")
def test_fetch_transcript_returns_none_when_not_found(mock_list):
    mock_list.side_effect = NoTranscriptFound("abc123", [], [])

    result = fetch_transcript("abc123")

    assert result is None


@patch("src.transcript_fetcher.YouTubeTranscriptApi.list_transcripts")
def test_fetch_transcript_returns_none_on_unexpected_error(mock_list):
    mock_list.side_effect = Exception("network error")

    result = fetch_transcript("abc123")

    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_transcript_fetcher.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement src/transcript_fetcher.py**

```python
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled


def fetch_transcript(video_id: str) -> str | None:
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        manual = [t for t in transcript_list if not t.is_generated]
        auto = [t for t in transcript_list if t.is_generated]

        transcript = next(iter(manual or auto), None)
        if transcript is None:
            return None

        entries = transcript.fetch()
        return " ".join(entry["text"] for entry in entries)

    except (NoTranscriptFound, TranscriptsDisabled, Exception):
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_transcript_fetcher.py -v`
Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/transcript_fetcher.py tests/test_transcript_fetcher.py
git commit -m "feat: add transcript fetcher with manual/auto fallback"
```

---

## Task 4: Bengali Summarizer

**Files:**
- Create: `src/summarizer.py`
- Create: `tests/test_summarizer.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_summarizer.py`:

```python
from unittest.mock import MagicMock, patch
from src.summarizer import summarize_in_bengali


@patch("src.summarizer.get_client")
def test_summarize_in_bengali_returns_summary_text(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="এটি একটি বাংলা সারসংক্ষেপ।")]
    )

    result = summarize_in_bengali("Test Title", "Test Channel", "This is transcript text.")

    assert result == "এটি একটি বাংলা সারসংক্ষেপ।"


@patch("src.summarizer.get_client")
def test_summarize_calls_correct_model(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="সারসংক্ষেপ")]
    )

    summarize_in_bengali("Title", "Channel", "transcript")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
    assert call_kwargs["max_tokens"] == 512


@patch("src.summarizer.get_client")
def test_summarize_truncates_long_transcript_to_8000_chars(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="সারসংক্ষেপ")]
    )

    long_transcript = "word " * 5000  # ~25000 chars

    summarize_in_bengali("Title", "Channel", long_transcript)

    prompt = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
    # The transcript slice passed to the API must be at most 8000 chars
    assert long_transcript[8000:] not in prompt
    assert long_transcript[:100] in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_summarizer.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement src/summarizer.py**

```python
import os
import anthropic


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def summarize_in_bengali(title: str, channel: str, transcript: str) -> str:
    client = get_client()

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": (
                    "নিচের YouTube ভিডিওর একটি সংক্ষিপ্ত বাংলা সারসংক্ষেপ লিখুন। "
                    "সারসংক্ষেপটি ৩-৫ বাক্যের মধ্যে হতে হবে (প্রায় ৮০-১২০ শব্দ)।\n\n"
                    f"ভিডিও শিরোনাম: {title}\n"
                    f"চ্যানেল: {channel}\n\n"
                    f"প্রতিলিপি:\n{transcript[:8000]}\n\n"
                    "শুধুমাত্র বাংলায় সারসংক্ষেপ লিখুন।"
                ),
            }
        ],
    )

    return message.content[0].text
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_summarizer.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/summarizer.py tests/test_summarizer.py
git commit -m "feat: add Bengali summarizer using Claude Haiku"
```

---

## Task 5: Telegram Client

**Files:**
- Create: `src/telegram_client.py`
- Create: `tests/test_telegram_client.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_telegram_client.py`:

```python
from unittest.mock import MagicMock, patch
from src.telegram_client import send_message


@patch("src.telegram_client.requests.post")
def test_send_message_returns_true_on_success(mock_post):
    mock_post.return_value = MagicMock(ok=True)

    result = send_message("Test message")

    assert result is True
    mock_post.assert_called_once()


@patch("src.telegram_client.requests.post")
def test_send_message_retries_once_on_failure(mock_post):
    mock_post.side_effect = [MagicMock(ok=False), MagicMock(ok=True)]

    result = send_message("Test message")

    assert result is True
    assert mock_post.call_count == 2


@patch("src.telegram_client.requests.post")
def test_send_message_returns_false_after_two_failures(mock_post):
    mock_post.return_value = MagicMock(ok=False)

    result = send_message("Test message")

    assert result is False
    assert mock_post.call_count == 2


@patch("src.telegram_client.requests.post")
def test_send_message_uses_html_parse_mode(mock_post):
    mock_post.return_value = MagicMock(ok=True)

    send_message("Test")

    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"]["parse_mode"] == "HTML"


@patch("src.telegram_client.requests.post")
def test_send_message_posts_to_correct_channel(mock_post, monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHANNEL_USERNAME", "@mychannel")
    mock_post.return_value = MagicMock(ok=True)

    send_message("Test")

    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"]["chat_id"] == "@mychannel"


@patch("src.telegram_client.requests.post")
def test_send_message_handles_network_exception(mock_post):
    import requests as req
    mock_post.side_effect = req.RequestException("timeout")

    result = send_message("Test")

    assert result is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_telegram_client.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement src/telegram_client.py**

```python
import os
import requests


def send_message(text: str) -> bool:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel = os.environ["TELEGRAM_CHANNEL_USERNAME"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": channel, "text": text, "parse_mode": "HTML"}

    for _ in range(2):
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.ok:
                return True
        except requests.RequestException:
            continue

    return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_telegram_client.py -v`
Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/telegram_client.py tests/test_telegram_client.py
git commit -m "feat: add Telegram client with retry logic"
```

---

## Task 6: Orchestrator (main.py)

**Files:**
- Create: `src/main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_main.py`:

```python
import json
from unittest.mock import MagicMock, patch
import pytest
from src.main import load_seen_videos, save_seen_videos, format_message, main


def test_load_seen_videos_returns_set_from_file(tmp_path, monkeypatch):
    seen_file = tmp_path / "seen_videos.json"
    seen_file.write_text('["abc", "def"]')
    monkeypatch.chdir(tmp_path)

    result = load_seen_videos()

    assert result == {"abc", "def"}


def test_load_seen_videos_returns_empty_set_if_file_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = load_seen_videos()

    assert result == set()


def test_save_seen_videos_writes_sorted_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    save_seen_videos({"zzz", "aaa", "mmm"})

    content = json.loads((tmp_path / "seen_videos.json").read_text())
    assert content == ["aaa", "mmm", "zzz"]


def test_format_message_escapes_html_special_chars():
    video = {"id": "abc123", "title": "A & B <test>", "channel": "Channel"}
    result = format_message(video, "সারসংক্ষেপ")

    assert "A &amp; B &lt;test&gt;" in result
    assert "https://youtu.be/abc123" in result
    assert "সারসংক্ষেপ" in result


def test_format_message_contains_all_fields():
    video = {"id": "xyz", "title": "My Video", "channel": "My Channel"}
    result = format_message(video, "বাংলা সারসংক্ষেপ")

    assert "My Video" in result
    assert "My Channel" in result
    assert "বাংলা সারসংক্ষেপ" in result
    assert "https://youtu.be/xyz" in result


@patch("src.main.get_watch_later_videos")
@patch("src.main.fetch_transcript")
@patch("src.main.summarize_in_bengali")
@patch("src.main.send_message")
@patch("src.main.load_seen_videos")
@patch("src.main.save_seen_videos")
def test_main_skips_already_seen_videos(
    mock_save, mock_load, mock_send, mock_summarize, mock_transcript, mock_videos
):
    mock_load.return_value = {"old_id"}
    mock_videos.return_value = [
        {"id": "old_id", "title": "Old", "channel": "Ch"},
        {"id": "new_id", "title": "New", "channel": "Ch"},
    ]
    mock_transcript.return_value = "transcript"
    mock_summarize.return_value = "সারসংক্ষেপ"
    mock_send.return_value = True

    main()

    mock_transcript.assert_called_once_with("new_id")
    mock_send.assert_called_once()


@patch("src.main.get_watch_later_videos")
@patch("src.main.fetch_transcript")
@patch("src.main.summarize_in_bengali")
@patch("src.main.send_message")
@patch("src.main.load_seen_videos")
@patch("src.main.save_seen_videos")
def test_main_adds_to_seen_only_on_successful_send(
    mock_save, mock_load, mock_send, mock_summarize, mock_transcript, mock_videos
):
    mock_load.return_value = set()
    mock_videos.return_value = [{"id": "vid1", "title": "Video", "channel": "Ch"}]
    mock_transcript.return_value = "transcript"
    mock_summarize.return_value = "সারসংক্ষেপ"
    mock_send.return_value = True

    main()

    mock_save.assert_called_once_with({"vid1"})


@patch("src.main.get_watch_later_videos")
@patch("src.main.fetch_transcript")
@patch("src.main.send_message")
@patch("src.main.load_seen_videos")
@patch("src.main.save_seen_videos")
def test_main_does_not_add_to_seen_when_send_fails(
    mock_save, mock_load, mock_send, mock_transcript, mock_videos
):
    mock_load.return_value = set()
    mock_videos.return_value = [{"id": "vid1", "title": "Video", "channel": "Ch"}]
    mock_transcript.return_value = None
    mock_send.return_value = False

    main()

    mock_save.assert_called_once_with(set())


@patch("src.main.get_watch_later_videos")
@patch("src.main.fetch_transcript")
@patch("src.main.send_message")
@patch("src.main.load_seen_videos")
@patch("src.main.save_seen_videos")
def test_main_uses_fallback_message_when_no_transcript(
    mock_save, mock_load, mock_send, mock_transcript, mock_videos
):
    mock_load.return_value = set()
    mock_videos.return_value = [{"id": "vid1", "title": "Video", "channel": "Ch"}]
    mock_transcript.return_value = None
    mock_send.return_value = True

    main()

    sent_text = mock_send.call_args.args[0]
    assert "প্রতিলিপি পাওয়া যায়নি" in sent_text


@patch("src.main.get_watch_later_videos")
@patch("src.main.load_seen_videos")
@patch("src.main.save_seen_videos")
def test_main_exits_early_with_no_new_videos(mock_save, mock_load, mock_videos):
    mock_load.return_value = {"vid1"}
    mock_videos.return_value = [{"id": "vid1", "title": "Video", "channel": "Ch"}]

    main()

    mock_save.assert_not_called()


@patch("src.main.get_watch_later_videos")
@patch("src.main.fetch_transcript")
@patch("src.main.summarize_in_bengali")
@patch("src.main.send_message")
@patch("src.main.load_seen_videos")
@patch("src.main.save_seen_videos")
def test_main_continues_after_single_video_error(
    mock_save, mock_load, mock_send, mock_summarize, mock_transcript, mock_videos
):
    mock_load.return_value = set()
    mock_videos.return_value = [
        {"id": "vid1", "title": "Video 1", "channel": "Ch"},
        {"id": "vid2", "title": "Video 2", "channel": "Ch"},
    ]
    mock_transcript.side_effect = [Exception("API error"), "transcript for vid2"]
    mock_summarize.return_value = "সারসংক্ষেপ"
    mock_send.return_value = True

    main()

    # vid1 errored, vid2 succeeded
    mock_save.assert_called_once_with({"vid2"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_main.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement src/main.py**

```python
import json
import os

from src.youtube_client import get_watch_later_videos
from src.transcript_fetcher import fetch_transcript
from src.summarizer import summarize_in_bengali
from src.telegram_client import send_message

SEEN_VIDEOS_PATH = "seen_videos.json"


def load_seen_videos() -> set:
    if os.path.exists(SEEN_VIDEOS_PATH):
        with open(SEEN_VIDEOS_PATH) as f:
            return set(json.load(f))
    return set()


def save_seen_videos(seen: set) -> None:
    with open(SEEN_VIDEOS_PATH, "w") as f:
        json.dump(sorted(seen), f, indent=2)


def format_message(video: dict, summary: str) -> str:
    title = video["title"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    channel = video["channel"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f"🎬 <b>{title}</b>\n"
        f"📺 {channel}\n\n"
        f"{summary}\n\n"
        f"🔗 https://youtu.be/{video['id']}"
    )


def main():
    seen = load_seen_videos()
    videos = get_watch_later_videos()
    new_videos = [v for v in videos if v["id"] not in seen]

    if not new_videos:
        print("No new videos found.")
        return

    for video in new_videos:
        try:
            transcript = fetch_transcript(video["id"])

            if transcript:
                summary = summarize_in_bengali(video["title"], video["channel"], transcript)
            else:
                summary = "প্রতিলিপি পাওয়া যায়নি।"

            message = format_message(video, summary)
            success = send_message(message)

            if success:
                seen.add(video["id"])
                print(f"✓ Posted: {video['title']}")
            else:
                print(f"✗ Failed to post: {video['title']}")

        except Exception as e:
            print(f"✗ Error processing '{video['title']}': {e}")

    save_seen_videos(seen)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `pytest -v`
Expected: All tests PASS (green)

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: add main orchestrator"
```

---

## Task 7: OAuth Refresh Token Script

**Files:**
- Create: `auth/__init__.py`
- Create: `auth/get_refresh_token.py`

This script is run locally once by the user. No automated tests — it requires a browser and real Google credentials.

- [ ] **Step 1: Create auth/__init__.py**

Empty file.

- [ ] **Step 2: Create auth/get_refresh_token.py**

```python
"""
One-time script to generate a Google OAuth refresh token.

Run locally: python auth/get_refresh_token.py

Requirements:
  1. A Google Cloud project with YouTube Data API v3 enabled
  2. OAuth 2.0 credentials (Desktop app type) downloaded from Google Cloud Console

The script will open your browser for Google sign-in, then print the refresh token.
Copy the token into your GitHub repository as the secret GOOGLE_REFRESH_TOKEN.
"""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


def main():
    client_id = input("Enter your Google OAuth Client ID: ").strip()
    client_secret = input("Enter your Google OAuth Client Secret: ").strip()

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        },
        scopes=SCOPES,
    )

    creds = flow.run_local_server(port=0)

    print("\n" + "=" * 60)
    print("SUCCESS! Copy this value to GitHub Secrets.")
    print("Secret name: GOOGLE_REFRESH_TOKEN")
    print("=" * 60)
    print(creds.refresh_token)
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add auth/__init__.py auth/get_refresh_token.py
git commit -m "feat: add one-time OAuth refresh token script"
```

---

## Task 8: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/summarize.yml`

- [ ] **Step 1: Create .github/workflows/summarize.yml**

```bash
mkdir -p .github/workflows
```

Create `.github/workflows/summarize.yml`:

```yaml
name: Summarize New Watch Later Videos

on:
  workflow_dispatch:

jobs:
  summarize:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run summarizer
        run: python src/main.py
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

Note: `permissions: contents: write` is required for the bot to push the updated `seen_videos.json`.

- [ ] **Step 2: Run full test suite one final time**

Run: `pytest -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/summarize.yml
git commit -m "feat: add GitHub Actions workflow"
```

---

## Post-Implementation Setup Checklist

These steps are done manually by the user once the code is pushed to GitHub:

1. **Google Cloud setup:**
   - Go to https://console.cloud.google.com
   - Create a new project
   - Enable "YouTube Data API v3"
   - Go to Credentials → Create Credentials → OAuth 2.0 Client ID → Desktop app
   - Copy the Client ID and Client Secret

2. **Get refresh token:**
   - Run `python auth/get_refresh_token.py` locally
   - Sign in with the Google account that owns the Watch Later list
   - Copy the printed refresh token

3. **Telegram bot setup:**
   - Open Telegram → search for `@BotFather`
   - Send `/newbot` and follow prompts
   - Copy the bot token
   - Add the bot as an admin to your public channel

4. **Add GitHub Secrets:**
   - Go to repo Settings → Secrets and variables → Actions → New repository secret
   - Add all 6 secrets: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_USERNAME`

5. **Push to GitHub and test:**
   - Push the repo to GitHub
   - Go to Actions tab → "Summarize New Watch Later Videos" → Run workflow
