from __future__ import annotations

import os
import http.cookiejar
import requests
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

COOKIES_PATH = os.environ.get("YOUTUBE_COOKIES_FILE", "")


def _make_api() -> YouTubeTranscriptApi:
    if COOKIES_PATH and os.path.exists(COOKIES_PATH):
        jar = http.cookiejar.MozillaCookieJar(COOKIES_PATH)
        jar.load(ignore_discard=True, ignore_expires=True)
        session = requests.Session()
        session.cookies = jar
        return YouTubeTranscriptApi(http_client=session)
    return YouTubeTranscriptApi()


def fetch_transcript(video_id: str) -> str | None:
    try:
        api = _make_api()
        transcript_list = api.list(video_id)

        manual = [t for t in transcript_list if not t.is_generated]
        auto = [t for t in transcript_list if t.is_generated]

        transcript = next(iter(manual or auto), None)
        if transcript is None:
            return None

        entries = transcript.fetch()
        return " ".join(entry.text for entry in entries)

    except (NoTranscriptFound, TranscriptsDisabled) as e:
        print(f"Transcript unavailable for {video_id}: {type(e).__name__}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error fetching transcript for {video_id}: {type(e).__name__}: {e}")
        return None
