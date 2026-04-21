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
