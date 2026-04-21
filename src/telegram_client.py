import os
import requests


def send_message(text: str) -> bool:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel = os.environ["TELEGRAM_CHANNEL_USERNAME"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": channel, "text": text, "parse_mode": "HTML"}

    for _ in range(2):
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.ok:
                return True
        except requests.RequestException:
            continue

    return False
