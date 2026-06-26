from curl_cffi import requests

CHANNEL = "clavicular"

API_URL = f"https://kick.com/api/v2/channels/{CHANNEL}/videos"
REFERER = f"https://kick.com/{CHANNEL}"

headers = {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "referer": REFERER,
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "x-app-platform": "web",
}

session = requests.Session(impersonate="chrome124")

# Warm up session by visiting the normal page first
session.get(REFERER, headers=headers)

response = session.get(API_URL, headers=headers)
print("status:", response.status_code)

response.raise_for_status()
data = response.json()

# Kick may return either a list directly or a dict containing data
if isinstance(data, dict):
    videos = data.get("data") or data.get("videos") or []
else:
    videos = data

for video in videos:
    title = video.get("session_title")
    risk_level = video.get("risk_level_id")
    url = video.get("url")
    print(f"{title}: {url}, risk level: {risk_level}")
