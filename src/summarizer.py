import os
import anthropic


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def summarize_in_bengali(title: str, channel: str, transcript: str) -> str:
    client = get_client()

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": (
                    "নিচের YouTube ভিডিওর একটি সংক্ষিপ্ত বাংলা সারসংক্ষেপ লিখুন। "
                    "সারসংক্ষেপটি ৩-৫ বাক্যের মধ্যে হতে হবে (প্রায় ৮০-১২০ শব্দ)।\n\n"
                    f"ভিডিও শিরোনাম: {title}\n"
                    f"চ্যানেল: {channel}\n\n"
                    f"প্রতিলিপি:\n{transcript[:8000]}\n\n"
                    "শুধুমাত্র বাংলায় সারসংক্ষেপ লিখুন।"
                ),
            }
        ],
    )

    return message.content[0].text
