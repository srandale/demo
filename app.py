import streamlit as st
from openai import OpenAI
import requests
from bs4 import BeautifulSoup

# For voice
import streamlit_webrtc as webrtc
import SpeechRecognition as sr

# For TTS (server-side; see browser-only alternative in comments)
import pyttsx3

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

# --- TTS function ---
def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

# --- Streamlit UI ---
st.title("Shiv's VC Bot (Demo)")
st.write("Ask any VC/startup question—answers are based on this Notion doc.")

if "history" not in st.session_state:
    st.session_state.history = []

if "voice_input" not in st.session_state:
    st.session_state.voice_input = False

st.markdown("**You can use your voice or type your question below:**")

use_voice = st.toggle("🎤 Use Voice Input", value=False)

question = ""

if use_voice:
    st.session_state.voice_input = True
    # Use streamlit_webrtc and speech_recognition to get voice input
    from streamlit_webrtc import webrtc_streamer, AudioProcessorBase

    class AudioProcessor(AudioProcessorBase):
        def __init__(self):
            self.recognizer = sr.Recognizer()
            self.mic = sr.Microphone()

        def recv(self, frame):
            with self.mic as source:
                audio_data = self.recognizer.listen(source, phrase_time_limit=5)
            try:
                question_text = self.recognizer.recognize_google(audio_data)
                st.session_state["audio_question"] = question_text
            except Exception as e:
                st.session_state["audio_question"] = "Sorry, could not recognize speech."

    webrtc_streamer(key="audio", audio_processor_factory=AudioProcessor)
    if st.session_state.get("audio_question"):
        question = st.session_state["audio_question"]
        st.text_input("Your question:", value=question, key="qtext_voice")
    else:
        st.text_input("Your question:", key="qtext_voice")
else:
    q = st.text_input("Your question:", key="qtext", on_change=lambda: st.session_state.update({'submitted': True}))
    question = q

# --- Submit either by hitting enter or ask button ---
submitted = st.session_state.get('submitted', False)
ask_clicked = st.button("Ask")

if (ask_clicked or submitted) and question:
    ans = ask_vc_bot(question)
    st.session_state.history.append((question, ans, st.session_state.voice_input))
    st.session_state["submitted"] = False

    # Read answer if voice input was used
    if st.session_state.voice_input:
        speak(ans)
        # Alternative for browser-based TTS:
        # st.markdown(f"<script>new SpeechSynthesisUtterance('{ans.replace(''','')}').speak()</script>", unsafe_allow_html=True)

for _q, _a, _voice in reversed(st.session_state.history):
    st.markdown(f"**You:** {_q}")
    st.markdown(f"**VC Bot:** {_a}")

st.session_state.voice_input = False  # Reset after use
