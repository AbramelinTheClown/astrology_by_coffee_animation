import os
from dotenv import load_dotenv
import time
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
#from tiktok_uploader import upload_video

load_dotenv()

YOUTUBE_CLIENT_SECRETS = os.getenv("ASTROLOGYBYCOFFEE_GOOGLE_CREDENTIALS")

# Configuration
VIDEO_DIR = "D:\\AI\\astrology_by_coffee_v1\\content\\" # Directory with video files

#TIKTOK_SESSION_ID = "your_tiktok_session_id_here"  # Replace with your session ID
UPLOAD_INTERVAL = 3600  # Seconds between uploads (e.g., 1 hour)

# YouTube API Setup
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
def get_youtube_service():
    flow = InstalledAppFlow.from_client_secrets_file(YOUTUBE_CLIENT_SECRETS, SCOPES)
    credentials = flow.run_local_server(port=0)
    return build("youtube", "v3", credentials=credentials)

# YouTube Upload Function
def upload_to_youtube(file_path, title, description, tags):
    youtube = get_youtube_service()
    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22"  # People & Blogs
        },
        "status": {
            "privacyStatus": "public"  # or "private", "unlisted"
        }
    }
    media = MediaFileUpload(file_path)
    response = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    ).execute()
    print(f"Uploaded to YouTube: {response['id']}")
    return response['id']

# TikTok Upload Function
#def upload_to_tiktok(file_path, title, tags):
   # try:
   #     upload_video(
   #         session_id=TIKTOK_SESSION_ID,
   #         file_path=file_path,
   #         title=title,
   #         tags=tags
   #     )
   #     print(f"Uploaded to TikTok: {title}")
   # except Exception as e:
   #     print(f"TikTok upload failed: {e}")

# Orchestrator Loop
def orchestrator():
    while True:
        # Scan video directory
        for file_name in os.listdir(VIDEO_DIR):
            if file_name.endswith(".mp4"):  # Process only .mp4 files
                file_path = os.path.join(VIDEO_DIR, file_name)
                title = f"Astrology by Coffee: {file_name.replace('.mp4', '')}"
                description = "Daily astrology insights with a coffee twist! #astrology #horoscope"
                tags = ["astrology", "horoscope", "coffee", "daily"]

                print(f"Processing: {file_name}")
                # Upload to YouTube
                try:
                    upload_to_youtube(file_path, title, description, tags)
                except Exception as e:
                    print(f"YouTube upload failed: {e}")

                # Upload to TikTok
                #upload_to_tiktok(file_path, title, tags)

                # Move or delete file after upload
                os.rename(file_path, file_path.replace("media", "media\\uploaded"))  # Move to uploaded folder
                # Alternatively: os.remove(file_path) to delete

        print(f"Waiting {UPLOAD_INTERVAL} seconds before next cycle...")
        time.sleep(UPLOAD_INTERVAL)

if __name__ == "__main__":
    # Ensure uploaded folder exists
    os.makedirs(os.path.join(VIDEO_DIR, "uploaded"), exist_ok=True)
    orchestrator()