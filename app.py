import streamlit as st
import os
import re
import json
import requests
from pytube import Channel
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from bs4 import BeautifulSoup

api_key = st.secrets["api_key"]
client = OpenAI(api_key=api_key)
NOTION_URL = "https://thevcfellowship.notion.site/Founder-Fit-and-Outreach-d044466772c340e7b9bced2c2042089d"
TRANSCRIPTS_DIR = 'transcripts'

def channel_handle_to_id_url(handle_url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/119.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(handle_url, headers=headers)
    print(f"Status: {resp.status_code}")
    # Uncomment to debug unexpected HTML with:
    # with open("yt_debug.html", "w", encoding="utf-8") as f:
    #     f.write(resp.text)

    if resp.status_code != 200:
        raise Exception("Failed to load handle URL.")
    html = resp.text

    match = re.search(r'"channelId":"(UC[0-9A-Za-z_-]+)"', html)
    if not match:
        match = re.search(r'"browseId":"(UC[0-9A-Za-z_-]+)"', html)
    if not match:
        match = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[0-9A-Za-z_-]+)"', html)
    if not match:
        raise Exception("Channel ID not found.\nPreview HTML:\n" + html[:500])
    channel_id = match.group(1)
    return f"https://www.youtube.com/channel/{channel_id}"

def extract_video_id(url):
    patterns = [r'v=([^&?/]+)', r'youtu\.be/([^?&]+)', r'/([A-Za-z0-9_-]{11})(?:[/?&]|$)']
    for pat in patterns:
        match = re.search(pat, url)
        if match:
            return match.group(1)
    return None

def fetch_channel_transcripts(orig_channel_url, output_dir=TRANSCRIPTS_DIR):
    if '/channel/' in orig_channel_url:
        channel_url = orig_channel_url
    else:
        channel_url = channel_handle_to_id_url(orig_channel_url)
    os.makedirs(output_dir, exist_ok=True)
    c = Channel(channel_url)
    downloaded, failed = 0, 0
    for video_url in c.video_urls:
        video_id = extract_video_id(video_url)
        if not video_id:
            continue
        path = os.path.join(output_dir, f'{video_id}.json')
        if os.path.exists(path):
            continue
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(transcript, f)
            downloaded += 1
        except Exception as e:
            print(f"Failed for {video_id}: {e}")
            failed += 1
    return downloaded, failed

def load_all_transcripts(transcript_dir=TRANSCRIPTS_DIR):
    data = []
    for fname in os.listdir(transcript_dir):
        if fname.endswith('.json'):
            with open(os.path.join(transcript_dir, fname), encoding='utf-8') as f:
                transcript = json.load(f)
                transcript_text = "\n".join([entry['text'] for entry in transcript])
                data.append({'video_id': fname[:-5], 'text': transcript_text})
    return data

def fetch_notion_content(url):
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        return soup.get_text(separator='\n')[:6000]
    except Exception as e:
        return f"Could not fetch Notion context: {e}"

def ask_unified_bot(question, notion_url, all_transcripts):
    notion_context = fetch_notion_content(notion_url)
    if not notion_context or "Could not fetch" in notion_context:
        notion_context = ""
    transcript_context = ""
    for t in all_transcripts:
        transcript_context += f"--- VIDEO {t['video_id']} ---\n{t['text']}\n"
    transcript_context = transcript_context[:12000]  # cap context for efficiency
    prompt = f"""
Answer the user's VC/startup questions using ONLY the following knowledge sources:

[From Notion doc:]
{notion_context}

[From YouTube video transcripts:]
{transcript_context}

User question: {question}
"""
    response = client.completions.create(
        model="gpt-4o-mini",
        prompt=prompt,
        max_tokens=400,
        temperature=0.3,
    )
    return response.choices[0].text.strip()

# -------- Streamlit UI --------
st.title("VC Knowledge Bot (Notion + Bulk YouTube Channel Q&A)")

with st.expander("🔄 (Optional) Load YouTube Channel Transcripts"):
    channel_url = st.text_input("Enter YouTube Channel URL (@handle or /channel/UC...):", value="https://www.youtube.com/@bridger_pennington")
    fetch_btn = st.button("Fetch/Update Channel Transcripts")
    if fetch_btn and channel_url:
        with st.spinner("Fetching transcripts..."):
            try:
                ok, fail = fetch_channel_transcripts(channel_url)
                st.success(f"New transcripts downloaded: {ok}. Videos with errors: {fail}.")
            except Exception as e:
                st.error(f"Error: {e}")

if "history" not in st.session_state:
    st.session_state.history = []

if not os.path.exists(TRANSCRIPTS_DIR):
    os.makedirs(TRANSCRIPTS_DIR)
all_transcripts = load_all_transcripts()

q = st.text_input("Ask your VC/startup/video question (answers use Notion doc, & downloaded YouTube transcripts):")
ask = st.button("Ask the bot")
if ask and q:
    ans = ask_unified_bot(q, NOTION_URL, all_transcripts)
    st.session_state.history.append((q, ans))

for _q, _a in reversed(st.session_state.history):
    st.markdown(f"**You:** {_q}")
    st.markdown(f"**Bot:** {_a}")

st.markdown("---")
st.markdown(f"Transcripts loaded: {len(all_transcripts)}")
st.markdown(f"Notion doc source: [link]({NOTION_URL})")
