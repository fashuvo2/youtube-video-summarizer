from unittest.mock import MagicMock, patch
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled
from src.transcript_fetcher import fetch_transcript


@patch("src.transcript_fetcher.YouTubeTranscriptApi.list")
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


@patch("src.transcript_fetcher.YouTubeTranscriptApi.list")
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


@patch("src.transcript_fetcher.YouTubeTranscriptApi.list")
def test_fetch_transcript_falls_back_to_auto_captions(mock_list):
    auto = MagicMock()
    auto.is_generated = True
    auto.fetch.return_value = [{"text": "Auto caption text", "start": 0.0, "duration": 2.0}]
    mock_list.return_value = [auto]

    result = fetch_transcript("abc123")

    assert result == "Auto caption text"


@patch("src.transcript_fetcher.YouTubeTranscriptApi.list")
def test_fetch_transcript_returns_none_when_disabled(mock_list):
    mock_list.side_effect = TranscriptsDisabled("abc123")

    result = fetch_transcript("abc123")

    assert result is None


@patch("src.transcript_fetcher.YouTubeTranscriptApi.list")
def test_fetch_transcript_returns_none_when_not_found(mock_list):
    mock_list.side_effect = NoTranscriptFound("abc123", [], [])

    result = fetch_transcript("abc123")

    assert result is None


@patch("src.transcript_fetcher.YouTubeTranscriptApi.list")
def test_fetch_transcript_returns_none_on_unexpected_error(mock_list):
    mock_list.side_effect = Exception("network error")

    result = fetch_transcript("abc123")

    assert result is None
