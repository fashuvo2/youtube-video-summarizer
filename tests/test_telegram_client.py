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
