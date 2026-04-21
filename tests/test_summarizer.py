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
