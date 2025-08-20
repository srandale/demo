import streamlit as st
from openai import OpenAI
import requests
import os
import json
from bs4 import BeautifulSoup

# ------------ SETTINGS --------------
api_key = st.secrets["api_key"]
client = OpenAI(api_key=api_key)
NOTION_URL = "https://thevcfellowship.notion.site/Founder-Fit-and-Outreach-d044466772c340e7b9bced2c2042089d"
transcript_dir = 'transcripts'  # folder with YouTube transcripts (see bulk fetch code)
# -------------------------------------

def fetch_notion_content(url):
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        return soup.get_text(separator='\n')[:6000]
    except Exception as e:
        return f"Could not fetch Notion context: {e}"

def load_all_transcripts():
    data = []
    for fname in os.listdir(transcript_dir):
        if fname.endswith('.json'):
            with open(os.path.join(transcript_dir, fname), encoding='utf-8') as f:
                transcript = json.load(f)
                transcript_text = "\n".join([entry['text'] for entry in transcript])
                data.append({'video_id': fname[:-5], 'text': transcript_text})
    return data

def ask_unified_bot(question, notion_url, all_transcripts):
    notion_context = fetch_notion_content(notion_url)
    if not notion_context or "Could not fetch" in notion_context:
        notion_context = ""  # fail gracefully

    # (Optionally: limit number of transcript chars if your set is large)
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

# ---- Streamlit UI ----
st.title("VC Knowledge Bot (Notion + YouTube Bulk)")

if "history" not in st.session_state:
    st.session_state.history = []

all_transcripts = load_all_transcripts()

q = st.text_input("Ask your VC/startup/video question:")
ask = st.button("Ask")
if ask and q:
    ans = ask_unified_bot(q, NOTION_URL, all_transcripts)
    st.session_state.history.append((q, ans))

for _q, _a in reversed(st.session_state.history):
    st.markdown(f"**You:** {_q}")
    st.markdown(f"**Bot:** {_a}")

st.markdown("---")
st.markdown(f"Transcripts loaded: {len(all_transcripts)}")
st.markdown(f"Notion doc source: [link]({NOTION_URL})")
