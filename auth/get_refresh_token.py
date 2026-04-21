"""
One-time script to generate a Google OAuth refresh token.

Run locally: python auth/get_refresh_token.py

Requirements:
  1. A Google Cloud project with YouTube Data API v3 enabled
  2. OAuth 2.0 credentials (Desktop app type) downloaded from Google Cloud Console

The script will open your browser for Google sign-in, then print the refresh token.
Copy the token into your GitHub repository as the secret GOOGLE_REFRESH_TOKEN.
"""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


def main():
    client_id = input("Enter your Google OAuth Client ID: ").strip()
    client_secret = input("Enter your Google OAuth Client Secret: ").strip()

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        },
        scopes=SCOPES,
    )

    creds = flow.run_local_server(port=0)

    print("\n" + "=" * 60)
    print("SUCCESS! Copy this value to GitHub Secrets.")
    print("Secret name: GOOGLE_REFRESH_TOKEN")
    print("=" * 60)
    print(creds.refresh_token)
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
