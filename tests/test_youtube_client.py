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
