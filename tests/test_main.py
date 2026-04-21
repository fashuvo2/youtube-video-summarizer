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
