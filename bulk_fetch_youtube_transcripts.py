# bulk_fetch_youtube_transcripts.py

from youtube_transcript_api import YouTubeTranscriptApi
from pytube import Channel
import requests
import json
import os
import re

def channel_handle_to_id_url(handle_url):
    resp = requests.get(handle_url)
    match = re.search(r'"channelId":"(UC[-_A-Za-z0-9]+)"', resp.text)
    if match:
        channel_id = match.group(1)
        return f"https://www.youtube.com/channel/{channel_id}"
    else:
        raise Exception("Channel ID not found for: " + handle_url)

# --- User input: use either @handle or /channel/UCxxx ---
original_channel_url = 'https://www.youtube.com/@StartupClubTV'
if '/channel/' in original_channel_url:
    channel_url = original_channel_url
else:
    channel_url = channel_handle_to_id_url(original_channel_url)
print(f"Resolved channel URL: {channel_url}")

output_dir = 'transcripts'
os.makedirs(output_dir, exist_ok=True)

def extract_video_id(url):
    patterns = [r'v=([^&?/]+)', r'youtu\.be/([^?&]+)', r'/([A-Za-z0-9_-]{11})(?:[/?&]|$)']
    for pat in patterns:
        match = re.search(pat, url)
        if match:
            return match.group(1)
    return None

# --- Main transcript fetch logic ---
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
