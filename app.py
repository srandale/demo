import streamlit as st
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
import re

api_key = st.secrets["api_key"]
client = OpenAI(api_key=api_key)
NOTION_URL = "https://thevcfellowship.notion.site/Founder-Fit-and-Outreach-d044466772c340e7b9bced2c2042089d"

def fetch_notion_content(url):
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        return soup.get_text(separator='\n')[:6000]
    except Exception as e:
        return f"Error: {e}"

def ask_vc_bot(question, url=NOTION_URL):
    doc = fetch_notion_content(url)
    prompt = f"""
You are a VC-focused AI. ONLY answer using the following context:
{doc}
Question: {question}
"""
    response = client.completions.create(
        model="gpt-4o-mini", prompt=prompt, max_tokens=350, temperature=0.4
    )
    return response.choices[0].text.strip()

def get_youtube_video_id(url):
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    if match:
        return match.group(1)
    else:
        return None

# ---- UI ----

st.title("Shiv's VC Bot (Demo)")
st.write("Ask any VC/startup question—answers are based on this Notion doc.")

# Session history
if "history" not in st.session_state:
    st.session_state.history = []

# --- Voice Input (Browser JS) ---
st.markdown("""
<script>
let recognition;
let recognizing = false;
function startRecognition() {
  recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
  recognition.lang = 'en-US';
  recognizing = true;
  recognition.start();
  recognition.onresult = function(event) {
    let res = '';
    for(let i = event.resultIndex; i < event.results.length; ++i) {
      res += event.results[i].transcript;
    }
    document.querySelector('input[data-testid="stTextInput"]').value = res;
    let e = new Event('input', {bubbles:true});
    document.querySelector('input[data-testid="stTextInput"]').dispatchEvent(e);
  };
  recognition.onend = function() {
    recognizing = false;
    document.getElementById('mic-btn').innerText = "🎤 Voice";
  };
}
function toggleMic() {
  if (!recognizing) {
    startRecognition();
    document.getElementById('mic-btn').innerText = "🛑 Stop";
  } else {
    recognition.stop();
    recognizing = false;
    document.getElementById('mic-btn').innerText = "🎤 Voice";
  }
}
window.addEventListener('DOMContentLoaded', function() {
  setTimeout(()=>{
    let input=document.querySelector('input[data-testid="stTextInput"]');
    if (input && !document.getElementById('mic-btn')) {
      let btn=document.createElement('button');
      btn.id = 'mic-btn';
      btn.innerText = "🎤 Voice";
      btn.onclick = toggleMic;
      btn.style.marginLeft = "5px";
      input.parentElement.appendChild(btn);
    }
  }, 1000);
});
</script>
""", unsafe_allow_html=True)

# --- VC Bot Section ---
q = st.text_input("Your question:")
ask = st.button("Ask")
if ask and q:
    ans = ask_vc_bot(q)
    st.session_state.history.append((q, ans))
    st.markdown(f"""
    <script>
    window.speechSynthesis.speak(new SpeechSynthesisUtterance({repr(ans)}));
    </script>
    """, unsafe_allow_html=True)
for _q, _a in reversed(st.session_state.history):
    st.markdown(f"**You:** {_q}")
    st.markdown(f"**VC Bot:** {_a}")

# --- YouTube Transcript Extraction Section ---
st.markdown("---")
st.header("Extract YouTube Video Transcript")
youtube_url = st.text_input("Enter YouTube video link:")
if youtube_url:
    video_id = get_youtube_video_id(youtube_url)
    if video_id:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list.find_transcript(['en'])
            transcript_data = transcript.fetch()
            for entry in transcript_data:
                st.markdown(f"**{entry['start']:.2f}s–{entry['start']+entry['duration']:.2f}s:** {entry['text']}")
        except Exception as e:
            st.error(f"Error fetching transcript: {str(e)}")
    else:
        st.error("Invalid YouTube URL")
