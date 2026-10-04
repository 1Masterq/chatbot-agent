import csv
import os
import re
import smtplib
import ssl
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

STOP_WORDS = {
    "a", "about", "am", "an", "and", "are", "can", "do", "does", "for", "how", "i",
    "in", "is", "it", "me", "my", "of", "on", "or", "please", "school", "tell", "the",
    "there", "to", "we", "what", "when", "where", "which", "who", "why", "you",
}


def read_school_sections() -> list[tuple[str, list[str]]]:
    try:
        lines = SCHOOL_INFO_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    sections: list[tuple[str, list[str]]] = []
    title = "School information"
    content: list[str] = []
    for line in lines:
        heading = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if heading:
            if content:
                sections.append((title, content))
            title = heading.group(1)
            content = []
        elif line.strip():
            clean_line = re.sub(r"^\s*[-*]\s*", "", line).strip()
            if not clean_line or clean_line.lower().startswith(("source documents", "last reviewed")):
                continue

            field, separator, value = clean_line.partition(":")
            if separator and re.fullmatch(r"\[(?:add|add date)\]", value.strip(), flags=re.IGNORECASE):
                continue

            if separator and value.strip().startswith("[") and value.strip().endswith("]"):
                clean_line = f"{field.strip()}: {value.strip()[1:-1].strip()}"
            elif not separator and re.fullmatch(r"\[(?:add|add date)\]", clean_line, flags=re.IGNORECASE):
                continue

            content.append(clean_line)
    if content:
        sections.append((title, content))
    return sections


def search_terms(text: str) -> set[str]:
    return {
        word.rstrip("s")
        for word in re.findall(r"[a-z0-9]+", text.lower())
        if word not in STOP_WORDS and len(word) > 1
    }
def search_school_info(question: str) -> str | None:
    query_terms = search_terms(question)
    if not query_terms:
        return None

    best_result: tuple[int, str] | None = None
    for heading, lines in read_school_sections():
        heading_terms = search_terms(heading)
        for index, line in enumerate(lines):
            label, separator, value = line.partition(":")
            if not separator:
                label, value = heading, line

            # Handle FAQ questions/answers
            if label.strip().lower() == "question" and index + 1 < len(lines):
                answer_label, answer_separator, answer_value = lines[index + 1].partition(":")
                if answer_separator and answer_label.strip().lower() == "answer":
                    faq_terms = search_terms(value)
                    score = 6 * len(query_terms & faq_terms) + len(query_terms & heading_terms)
                    if score > 0 and (best_result is None or score > best_result[0]):
                        best_result = (score, answer_value.strip())
                    continue

            if label.strip().lower() == "answer" and index > 0:
                previous_label = lines[index - 1].partition(":")[0]
                if previous_label.strip().lower() == "question":
                    continue

            label_terms = search_terms(label)
            value_terms = search_terms(value)

            # Reduce the impact of generic labels like "name", "department"
            score = (
                2 * len(query_terms & label_terms)
                + 3 * len(query_terms & heading_terms)
                + 3 * len(query_terms & value_terms)
            )

            asks_for_name = bool(query_terms & {"name", "call", "called"})
            asks_for_department = bool(query_terms & {"department", "dept"})
            asks_for_hod = bool(query_terms & {"hod", "head"})

            if asks_for_name and asks_for_department and not asks_for_hod:
                if label.strip().lower() == "department":
                    score += 20
                elif "department" in label_terms:
                    score -= 4

            # Extra safeguard for vague "name" searches
            if asks_for_name and not asks_for_department and not asks_for_hod:
                if label.strip().lower() in {"official school name", "school identity"}:
                    score -= 5
                elif label.strip().lower() in {"head of department (hod)", "department contact/office"}:
                    score += 8

            if score > 0 and (best_result is None or score > best_result[0]):
                best_result = (score, value.strip())

    return f"**{best_result[1]}**" if best_result else None


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
    answer = search_school_info(latest_user_message)
    if answer:
        return answer
    return "I couldn't find a verified answer in the school information yet. I'll prepare this question for staff follow-up."


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
    message["Subject"] = "Freshman help-desk question"
    message["From"] = os.getenv("SMTP_FROM", "").strip() or smtp_username
    message["To"] = staff_email
    if email.strip():
        message["Reply-To"] = email.strip()
    message.set_content(
        "A freshman submitted a question for staff follow-up.\n\n"
        f"Question:\n{question.strip()}\n\n"
        f"Student reply email: {email.strip() or 'Not provided'}\n"
    )

    try:
        port = int(os.getenv("SMTP_PORT", "587"))
        with smtplib.SMTP(smtp_host, port, timeout=20) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(smtp_username, smtp_password)
            server.send_message(message)
    except (OSError, ValueError, smtplib.SMTPException):
        return "failed"
    return "sent"


st.title("Freshman help desk")
st.write("Welcome to campus. Search verified school information about rules, courses, departments, HODs, and settling in.")

with st.expander("What I can help with"):
    st.write("I search the school's approved information on this computer. I don't use a paid AI API or make up school facts. If I can't find an answer, you can email staff.")

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
        if answer.startswith("I couldn't find a verified answer"):
            st.session_state.pending_question = prompt
        st.write(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})

with st.sidebar:
    st.header("Ask a staff member")
    st.write("Send an unanswered question directly to the freshman support inbox.")
    with st.form("staff_follow_up"):
        question = st.text_area(
            "Your question",
            value=st.session_state.get("pending_question", ""),
            placeholder="What would you like a staff member to answer?",
        )
        email = st.text_input("Email for a reply (optional)")
        consent = st.checkbox("I agree to include this question and my optional email in an email to staff.")
        submitted = st.form_submit_button("Send to staff", type="primary")
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
                st.success("Your email was sent. We aim to review your question within 48 hours.")
            elif delivery == "failed":
                st.error("We couldn't send your email. Your question was saved on this computer; please contact the school directly.")
            else:
                st.warning("Email delivery isn't configured yet. Your question was saved on this computer, but staff have not received it.")
    st.caption("Your question and optional reply email are emailed to staff only after you agree and press Send to staff. Do not include passwords or sensitive personal information.")

st.caption("Do not share passwords or other sensitive personal information in chat.")
