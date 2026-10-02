import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import streamlit as st

ROOT = Path(__file__).resolve().parent
SCHOOL_INFO_PATH = ROOT / "school_info.md"
HANDOFF_PATH = ROOT / "data" / "handoff_requests.csv"
STAFF_EMAIL = "ohagwuijat@gmail.com"

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
        elif line.strip() and not re.search(r"\[[^]]*\]", line):
            clean_line = re.sub(r"^\s*[-*]\s*", "", line).strip()
            if clean_line and not clean_line.lower().startswith(("source documents", "last reviewed")):
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
        body = " ".join(lines)
        body_terms = search_terms(body)
        heading_terms = search_terms(heading)
        overlap = query_terms & (body_terms | heading_terms)
        if not overlap:
            continue
        score = 2 * len(query_terms & body_terms) + len(query_terms & heading_terms)
        answer = "\n".join(lines)
        if best_result is None or score > best_result[0]:
            best_result = (score, f"**{heading}**\n\n{answer}")

    return best_result[1] if best_result else None


def staff_email_link(email: str, question: str) -> str:
    body = f"Question: {question.strip()}\n\nReply email: {email.strip() or 'Not provided'}"
    query = urlencode({"subject": "Freshman help-desk question", "body": body})
    return f"mailto:{STAFF_EMAIL}?{query}"


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
    st.write("Send an unanswered question to staff using your own email app.")
    with st.form("staff_follow_up"):
        question = st.text_area(
            "Your question",
            value=st.session_state.get("pending_question", ""),
            placeholder="What would you like a staff member to answer?",
        )
        email = st.text_input("Email for a reply (optional)")
        consent = st.checkbox("I agree to include this question and my optional email in an email to staff.")
        submitted = st.form_submit_button("Prepare email", type="primary")
    if submitted:
        if not question.strip():
            st.error("Please enter your question first.")
        elif not consent:
            st.error("Please confirm before submitting your question to school staff.")
        else:
            save_handoff(email, question)
            st.session_state.pending_question = ""
            st.session_state.staff_mailto = staff_email_link(email, question)
            st.success("The question was saved locally. Select below to open a prefilled email, then press Send in your email app.")
    if st.session_state.get("staff_mailto"):
        st.link_button("Open prefilled email", st.session_state.staff_mailto, icon=":material/mail:")
    st.caption("Email opens in the student's email app and is not sent until they press Send. Requests are also saved locally on this computer.")

st.caption("Do not share passwords or other sensitive personal information in chat.")
