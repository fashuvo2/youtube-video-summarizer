import os
import requests


def send_message(text: str) -> bool:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    channel = os.environ["TELEGRAM_CHANNEL_USERNAME"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": channel, "text": text, "parse_mode": "HTML"}

    for attempt in range(2):
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.ok:
                return True
            print(f"Telegram error (attempt {attempt + 1}): {response.status_code} {response.text}")
        except requests.RequestException as e:
            print(f"Telegram request exception (attempt {attempt + 1}): {e}")

    return False
