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

    # Watch Later playlist ID is always "WL" for the authenticated user.
    # The YouTube Data API no longer exposes it via channels().list() relatedPlaylists.
    playlist_id = "WL"

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
