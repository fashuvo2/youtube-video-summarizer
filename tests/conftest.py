import pytest


@pytest.fixture(autouse=True)
def env_vars(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "test_refresh_token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_api_key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ")
    monkeypatch.setenv("TELEGRAM_CHANNEL_USERNAME", "@testchannel")
