import streamlit as st
from openai import OpenAI
import requests
from bs4 import BeautifulSoup

api_key = st.secrets["api_key"]
client = OpenAI(api_key=api_key)

st.set_page_config(page_title="Perplexity-Style VC Bot", page_icon="🤖")


# ---- DATA SOURCES ----
if "data_sources" not in st.session_state:
    st.session_state.data_sources = {
        "Notion VC Doc": {
            "type": "notion",
            "url": "https://thevcfellowship.notion.site/Founder-Fit-and-Outreach-d044466772c340e7b9bced2c2042089d"
        },
        "YouTube: Example Startup": {
            "type": "youtube",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }
    }

# ---- HANDLERS ----
def fetch_notion_content(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    return soup.get_text(separator='\n')[:6000]

def fetch_youtube_transcript(url):
    from youtube_transcript_api import YouTubeTranscriptApi
    import re
    video_id = re.search(r'(?:v=|youtu\.be/)([^&/?]+)', url)
    if not video_id:
        return "Invalid YouTube URL"
    video_id = video_id.group(1)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        txt = "\n".join([x['text'] for x in transcript])
        return txt[:6000]
    except Exception as e:
        return f"Transcript not available: {e}"

def get_context(src):
    if src["type"] == "notion":
        return fetch_notion_content(src["url"])
    elif src["type"] == "youtube":
        return fetch_youtube_transcript(src["url"])
    return ""

def ask_vc_bot(question, context):
    prompt = f"""You are a VC-focused AI. ONLY answer using the following context:
{context}
Question: {question}"""
    response = client.completions.create(
        model="gpt-4o-mini", prompt=prompt, max_tokens=350, temperature=0.4
    )
    return response.choices[0].text.strip()

# ---- PAGE HEADER ----
st.markdown("""
<style>
/* Chat bubble styles */
.message-user {background: #e1ffc7; border-radius:16px 16px 4px 16px; margin:5px 0; padding:10px; max-width:66%;}
.message-ai   {background: #e7eaf6; border-radius:16px 16px 16px 4px; margin:5px 0 20px 18%; padding:10px; max-width:66%;}
.message-src  {color:#577eda; font-size:0.8em; margin-left: 5px;}
.input-row    {display:flex;align-items:center;gap:8px;}
.send-icon    {cursor:pointer;height:38px;width:38px;vertical-align:middle;}
</style>
<div style='font-size:2em;font-weight:bold;letter-spacing:-1px;'>
  🤖 Shiv's Perplexity-Style VC Bot
</div>
<small>Ask about VC/startup using selected sources below.</small>
""", unsafe_allow_html=True)

# ---- HISTORY ----
if "history" not in st.session_state:
    st.session_state.history = []

# ---- SOURCE SELECTION / ADD ----
source_names = list(st.session_state.data_sources.keys())
selected_src = st.radio(
    "Knowledge Source",
    source_names,
    index=0, 
    horizontal=True
)
with st.expander("+ Add custom source"):
    source_type = st.selectbox("Type:", ["notion", "youtube"])
    source_name = st.text_input("Source name")
    source_url = st.text_input("Source URL")
    if st.button("Add Source") and source_name and source_url:
        st.session_state.data_sources[source_name] = {"type": source_type, "url": source_url}
        st.success(f"Added source: {source_name}")

# ---- CHAT BUBBLES HISTORY ----
for msg in st.session_state.history:
    src_nm, q, a = msg["src"], msg["q"], msg["a"]
    st.markdown(f"<div class='message-user'><b>You</b>: {q}"
                f"<div class='message-src'>({src_nm})</div></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='message-ai'><b>VC Bot</b>: {a}</div>", unsafe_allow_html=True)

st.markdown("---")

# ---- INPUT BAR (mic, enter, button) ----
col1, col2 = st.columns([10,1])
with col1:
    q = st.text_input("Type your question...", key="askbox", label_visibility="collapsed", 
                      placeholder="Type here and press Enter...")
with col2:
    send = st.button("➤", key="send_btn")

# Optional: Browser mic input
st.markdown("""
<script>
let recognition;
function startRecording() {
    recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'en-US';
    recognition.start();
    recognition.onresult = function(e) {
        let res = '';
        for (let i = e.resultIndex; i < e.results.length; ++i) { res += e.results[i][0].transcript; }
        document.querySelector('input[data-testid="stTextInput"]').value = res;
        let ev = new Event('input', {bubbles:true});
        document.querySelector('input[data-testid="stTextInput"]').dispatchEvent(ev);
    }
}
window.addEventListener('DOMContentLoaded', function() {
    setTimeout(()=>{
        let input=document.querySelector('input[data-testid="stTextInput"]');
        if (input && !document.getElementById('mic-btn')) {
            let btn=document.createElement('button'); btn.id='mic-btn';
            btn.innerHTML = "🎤"; btn.onclick=startRecording;
            btn.style.marginLeft = "6px";
            btn.style.border = "none";
            btn.style.background = "none";
            btn.style.cursor = "pointer";
            btn.style.fontSize = "28px";
            input.parentElement.appendChild(btn);
        }
    },650);
});
</script>
""", unsafe_allow_html=True)

# ---- PROCESS NEW QUESTIONS ----
if (send or (q and st.session_state.get("askbox"))):
    src = st.session_state.data_sources[selected_src]
    context = get_context(src)
    answer = ask_vc_bot(q, context)
    st.session_state.history.append({"src": selected_src, "q": q, "a": answer})
    # Optionally: clear input box or support browser-based TTS output as before
    st.experimental_rerun()

