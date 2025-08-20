import streamlit as st
import os
import re
import json
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from bs4 import BeautifulSoup

api_key = st.secrets["api_key"]
client = OpenAI(api_key=api_key)
NOTION_URL = "https://thevcfellowship.notion.site/Founder-Fit-and-Outreach-d044466772c340e7b9bced2c2042089d"
TRANSCRIPTS_DIR = 'transcripts'

def extract_video_id(url):
    patterns = [r'v=([^&?/]+)', r'youtu\.be/([^?&]+)', r'/([A-Za-z0-9_-]{11})(?:[/?&]|$)']
    for pat in patterns:
        match = re.search(pat, url)
        if match:
            return match.group(1)
    return None

def fetch_video_transcript(video_url, output_dir=TRANSCRIPTS_DIR):
    os.makedirs(output_dir, exist_ok=True)
    video_id = extract_video_id(video_url)
    if not video_id:
        raise Exception("Could not extract video ID from the supplied URL.")
    path = os.path.join(output_dir, f'{video_id}.json')
    if os.path.exists(path):
        return 0, 0
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(transcript, f)
        return 1, 0
    except Exception as e:
        print(f"Failed for {video_id}: {e}")
        return 0, 1

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
st.title("VC Knowledge Bot (Notion + YouTube Video Q&A)")

with st.expander("🎬 (Optional) Add a YouTube Video by Link"):
    video_url = st.text_input("Enter YouTube Video URL (not a channel):", value="")
    fetch_btn = st.button("Fetch/Update Video Transcript")
    if fetch_btn and video_url:
        with st.spinner("Fetching transcript..."):
            try:
                ok, fail = fetch_video_transcript(video_url)
                st.success(f"Transcript saved." if ok else "Already downloaded. If you don't see it reflected, refresh this page.")
            except Exception as e:
                st.error(f"Error: {e}")

if "history" not in st.session_state:
    st.session_state.history = []

if not os.path.exists(TRANSCRIPTS_DIR):
    os.makedirs(TRANSCRIPTS_DIR)
all_transcripts = load_all_transcripts()

q = st.text_input("Ask your VC/startup/video question (answers use Notion doc and video transcripts):")
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
