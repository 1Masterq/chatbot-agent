import json
import os
import urllib.error
import urllib.request

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Northstar Agent", page_icon="✦", layout="centered")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;600;700&family=Playfair+Display:ital,wght@0,500;1,500&display=swap');
    :root { --ink: #17211e; --muted: #71817b; --green: #2c765c; --coral: #df7158; }
    .stApp { background: #f7f9f5; color: var(--ink); }
    .block-container { max-width: 820px; padding-top: 3rem; }
    h1, h2, h3, p, div, button, textarea { font-family: Manrope, sans-serif; }
    h1 { font-size: 3.5rem !important; line-height: 1 !important; letter-spacing: -.04em; }
    .eyebrow { color: var(--muted); font-family: 'DM Mono', monospace; font-size: .7rem; letter-spacing: .12em; text-transform: uppercase; }
    .hero-mark { display: inline-grid; place-items: center; width: 54px; height: 54px; margin-bottom: 1.5rem; color: white; background: var(--coral); border-radius: 18px 18px 18px 4px; font-size: 1.6rem; transform: rotate(-6deg); }
    .subcopy { max-width: 470px; color: var(--muted); line-height: 1.7; }
    [data-testid='stChatMessage'] { border-radius: 8px; }
    [data-testid='stChatMessage'] p { line-height: 1.65; }
    .stButton button { border: 1px solid #dfe7e1; color: #4d6259; background: white; text-align: left; }
    .stButton button:hover { border-color: #80b397; color: var(--green); }
    </style>
    """,
    unsafe_allow_html=True,
)

SYSTEM_PROMPT = (
    "You are Northstar, a thoughtful and concise AI thinking partner. "
    "Help users clarify ideas, reason through decisions, and identify useful next steps."
)
STARTERS = [
    "Turn a messy idea into a clear plan",
    "Help me think through a difficult decision",
    "Draft a concise message for my team",
]


def ask_agent(messages: list[dict[str, str]]) -> str:
    api_key = os.getenv("AI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        return "I’m ready to help. Add your AI_API_KEY to .env to connect Northstar to a model provider."

    base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("AI_MODEL", "gpt-4o-mini")
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError):
        return "The model provider could not complete that request. Check your AI settings and try again."


st.markdown('<div class="hero-mark">✦</div>', unsafe_allow_html=True)
st.markdown('<p class="eyebrow">Personal studio</p>', unsafe_allow_html=True)
st.title("What are we\nmaking sense of?")
st.markdown('<p class="subcopy">Bring a question, a rough thought, or a blank page. Northstar helps you find the useful next step.</p>', unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    st.markdown('<p class="eyebrow">Try a starting point</p>', unsafe_allow_html=True)
    for starter in STARTERS:
        if st.button(starter, use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": starter})
            st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("Ask anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer = ask_agent(st.session_state.messages)
        st.write(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})

st.caption("Northstar can make mistakes. Check important details.")
