from __future__ import annotations

from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled


def fetch_transcript(video_id: str) -> str | None:
    try:
        api = YouTubeTranscriptApi()
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
