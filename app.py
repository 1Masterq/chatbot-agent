import csv
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
SCHOOL_INFO_PATH = ROOT / "school_info.md"
HANDOFF_PATH = ROOT / "data" / "handoff_requests.csv"

load_dotenv(ROOT / ".env.local")
load_dotenv(ROOT / ".env", override=False)

st.set_page_config(page_title="Freshman help desk", page_icon=":material/school:", layout="centered")

SYSTEM_PROMPT = """You are the school's friendly freshman help-desk assistant.
Answer questions about school rules, courses, departments, HODs, offices, and student life using only the verified school information below.
Do not invent or infer school-specific facts. If the information does not answer the question, reply with exactly [STAFF_FOLLOW_UP] followed by one brief sentence saying the information is not available and the student can ask a staff member.
For greetings and ordinary conversation, respond naturally and briefly. Be respectful, welcoming, and easy for a new student to understand.
Do not claim a staff request was sent unless the student submits the staff follow-up form.

Verified school information:
{school_info}
"""


def read_school_info() -> str:
    try:
        return SCHOOL_INFO_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return "No verified school information has been added yet."


def greeting_reply(message: str) -> str | None:
    normalized = re.sub(r"[^a-z ]", "", message.lower()).strip()
    if normalized in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}:
        return "Hey! Welcome. I can help with school rules, courses, departments, HODs, and other freshman questions. What would you like to know?"
    return None


def ask_agent(messages: list[dict[str, str]]) -> str:
    latest_user_message = next((message["content"] for message in reversed(messages) if message["role"] == "user"), "")
    local_greeting = greeting_reply(latest_user_message)
    if local_greeting:
        return local_greeting

    api_key = os.getenv("AI_API_KEY")
    if not api_key or api_key == "your_real_api_key":
        return "I can greet you, but the AI connection is not configured yet. Add AI_API_KEY to .env.local to ask school questions."

    base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("AI_MODEL", "gpt-4o-mini")
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.format(school_info=read_school_info())},
            *messages,
        ],
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
    except urllib.error.HTTPError as error:
        if error.code in {401, 403}:
            return "The AI provider rejected the API key. Check AI_API_KEY in .env.local."
        return "The AI provider is temporarily unavailable. Please try again or submit a staff follow-up request."
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError):
        return "I couldn't reach the AI provider. Please try again or submit a staff follow-up request."


def save_handoff(email: str, question: str) -> None:
    HANDOFF_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_exists = HANDOFF_PATH.exists()
    with HANDOFF_PATH.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["created_at_utc", "email", "question"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "email": email.strip(),
            "question": question.strip(),
        })


st.title("Freshman help desk")
st.write("Welcome to campus. Ask about school rules, courses, departments, HODs, or settling in.")

with st.expander("What I can help with"):
    st.write("I answer from the school's approved information. If I can't verify an answer, I will say so and you can leave a question for a staff member.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

prompt = st.chat_input("Ask a school or freshman question")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Checking..." if greeting_reply(prompt) is None else ""):
            answer = ask_agent(st.session_state.messages)
        if answer.startswith("[STAFF_FOLLOW_UP]"):
            answer = answer.removeprefix("[STAFF_FOLLOW_UP]").strip()
            st.session_state.pending_question = prompt
        st.write(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})

with st.sidebar:
    st.header("Ask a staff member")
    st.write("Use this when you need a person to follow up, or when the assistant does not know the answer.")
    with st.form("staff_follow_up"):
        question = st.text_area(
            "Your question",
            value=st.session_state.get("pending_question", ""),
            placeholder="What would you like a staff member to answer?",
        )
        email = st.text_input("Email for a reply (optional)")
        submitted = st.form_submit_button("Save follow-up request", type="primary")
    if submitted:
        if not question.strip():
            st.error("Please enter your question first.")
        else:
            save_handoff(email, question)
            st.session_state.pending_question = ""
            st.success("Your request was saved for staff follow-up.")
    st.caption("Prototype notice: requests are saved on this computer only. They are not emailed or sent to school staff yet.")

st.caption("Do not share passwords or other sensitive personal information in chat.")
