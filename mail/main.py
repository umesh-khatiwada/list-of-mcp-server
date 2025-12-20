
import requests


def check_refresh_token():
    url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }

    response = requests.post(url, data=data)
    if response.status_code == 200:
        print("✅ Refresh token is valid.")
        print("Access token:", response.json().get("access_token"))
    else:
        print("❌ Refresh token is invalid or expired.")
        print("Response:", response.text)


if __name__ == "__main__":
    check_refresh_token()
