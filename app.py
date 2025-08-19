import streamlit as st
from openai import OpenAI
import requests
from bs4 import BeautifulSoup

client = OpenAI(api_key="sk-...")  # <--- paste your key here
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

st.title("VC Bot (Demo)")
st.write("Ask any VC/startup question—answers are based on this Notion doc.")

if "history" not in st.session_state:
    st.session_state.history = []

q = st.text_input("Your question:")
if st.button("Ask") and q:
    ans = ask_vc_bot(q)
    st.session_state.history.append((q, ans))

for _q, _a in reversed(st.session_state.history):
    st.markdown(f"**You:** {_q}")
    st.markdown(f"**VC Bot:** {_a}")

