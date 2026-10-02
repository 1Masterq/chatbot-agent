import csv
import smtplib
import json
import os
import re
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
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


def provider_error_message(error: urllib.error.HTTPError) -> str:
    try:
        details = json.loads(error.read().decode("utf-8")).get("error", {})
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError):
        details = {}

    code = details.get("code")
    if code in {"credit_balance_exhausted", "insufficient_quota"}:
        return "The AI account has no API credits available. The account owner needs to add API billing or credits."
    if error.code == 429:
        return "The AI account has reached its usage limit. Check the provider's billing and rate limits."
    if error.code in {401, 403}:
        return "The AI provider rejected this key or its permissions. Check the provider account and API key."
    if error.code == 404:
        return "The configured AI model or API endpoint was not found. Check AI_MODEL and AI_BASE_URL."
    if error.code == 400:
        return "The AI provider rejected the request settings. Check AI_MODEL and the provider configuration."
    if error.code >= 500:
        return "The AI provider is having a temporary service problem. Please try again later."
    return "The AI provider could not complete this request. Please check its account and configuration."


def ask_agent(messages: list[dict[str, str]]) -> str:
    latest_user_message = next((message["content"] for message in reversed(messages) if message["role"] == "user"), "")
    local_greeting = greeting_reply(latest_user_message)
    if local_greeting:
        return local_greeting

    api_key = os.getenv("AI_API_KEY")
    if not api_key or api_key.strip() in {"your_real_api_key", "your_api_key_here"}:
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
        return provider_error_message(error)
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


def email_staff(email: str, question: str) -> str:
    staff_email = os.getenv("STAFF_EMAIL", "").strip()
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_username = os.getenv("SMTP_USERNAME", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    if not all((staff_email, smtp_host, smtp_username, smtp_password)):
        return "not_configured"

    message = EmailMessage()
    message["Subject"] = "Freshman help-desk follow-up"
    message["From"] = os.getenv("SMTP_FROM", "").strip() or smtp_username
    message["To"] = staff_email
    message.set_content(
        f"A freshman submitted a question for staff follow-up.\n\n"
        f"Question:\n{question.strip()}\n\n"
        f"Reply email: {email.strip() or 'Not provided'}\n"
    )

    try:
        with smtplib.SMTP(smtp_host, int(os.getenv("SMTP_PORT", "587")), timeout=20) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(smtp_username, smtp_password)
            server.send_message(message)
    except (OSError, ValueError, smtplib.SMTPException):
        return "failed"
    return "sent"


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
    st.caption("This saves the request locally. It emails staff only after the school's approved sender settings are configured.")
    with st.form("staff_follow_up"):
        question = st.text_area(
            "Your question",
            value=st.session_state.get("pending_question", ""),
            placeholder="What would you like a staff member to answer?",
        )
        email = st.text_input("Email for a reply (optional)")
        consent = st.checkbox("I agree to send this question and my optional email to school staff.")
        submitted = st.form_submit_button("Submit question", type="primary")
    if submitted:
        if not question.strip():
            st.error("Please enter your question first.")
        elif not consent:
            st.error("Please confirm before submitting your question to school staff.")
        else:
            save_handoff(email, question)
            st.session_state.pending_question = ""
            delivery = email_staff(email, question)
            if delivery == "sent":
                st.success("Your request was saved and emailed to school staff.")
            elif delivery == "failed":
                st.error("Your request was saved on this computer, but the staff email could not be sent. Please contact the school directly.")
            else:
                st.warning("Your request was saved on this computer only. Staff email delivery is not configured yet.")
    st.caption("Only submit information you are comfortable sharing with school staff. Requests are saved locally; email is sent only when the school configures an approved sender.")

st.caption("Do not share passwords or other sensitive personal information in chat.")
