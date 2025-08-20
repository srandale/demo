from youtube_transcript_api import YouTubeTranscriptApi
from pytube import Channel
import json
import os
import re

# Use your target channel here:
channel_url = 'https://www.youtube.com/@StartupClubTV'
output_dir = 'transcripts'
os.makedirs(output_dir, exist_ok=True)

def extract_video_id(url):
    # Support both /watch?v= and /shorts/ and /live/ URLs
    patterns = [r'v=([^&?/]+)', r'youtu\.be/([^?&]+)', r'/([A-Za-z0-9_-]{11})(?:[/?&]|$)']
    for pat in patterns:
        match = re.search(pat, url)
        if match:
            return match.group(1)
    return None

c = Channel(channel_url)
for video_url in c.video_urls:
    video_id = extract_video_id(video_url)
    if not video_id:
        continue
    path = os.path.join(output_dir, f'{video_id}.json')
    if os.path.exists(path):
        print(f"Already have {video_id}")
        continue
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(transcript, f)
        print(f"Saved transcript for {video_id}")
    except Exception as e:
        print(f"Failed for {video_id}: {e}")
