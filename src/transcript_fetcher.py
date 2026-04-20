from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled


def fetch_transcript(video_id: str) -> Optional[str]:
    try:
        transcript_list = YouTubeTranscriptApi.list(video_id)

        manual = [t for t in transcript_list if not t.is_generated]
        auto = [t for t in transcript_list if t.is_generated]

        transcript = next(iter(manual or auto), None)
        if transcript is None:
            return None

        entries = transcript.fetch()
        return " ".join(entry["text"] for entry in entries)

    except (NoTranscriptFound, TranscriptsDisabled, Exception):
        return None
