# Chatbot Agent

A Python-first freshman help desk built with Streamlit. It searches school-approved information locally, handles simple greetings, and can email unanswered questions directly to staff. It uses no paid AI API.

## Run locally

1. Install Python 3.11 or newer.
2. Create a virtual environment: `py -m venv .venv`.
3. Activate it: `.\\.venv\\Scripts\\Activate.ps1`.
4. Install dependencies: `python -m pip install -r requirements.txt`.
5. Copy `.env.example` to `.env.local` and configure a staff inbox and an approved sender account's SMTP settings.
6. Start the app: `streamlit run app.py`.
7. Open the local URL shown by Streamlit, usually `http://localhost:8501`.

Fill in `school_info.md` with facts verified by school staff. The assistant must not invent school-specific rules, course offerings, or HOD names; if a fact is missing, it will tell the student and offer a staff follow-up form.

The follow-up form asks the student for consent, saves a local backup to `data/handoff_requests.csv`, and sends the question to `STAFF_EMAIL` using SMTP. The 48-hour review message is shown only after the SMTP server accepts the message. Students do not need mail-server credentials. Use a dedicated, school-approved sender account and its app password; never use a personal account password. For public deployment, move SMTP values into the host's secret manager and add the school's privacy notice and retention policy. Local delivery only reaches staff while the app machine has network access.

This version is an extractive local search assistant, not a generative large language model. It returns matching approved handbook text and directs unmatched questions to staff. A future free-tier model could write more conversational answers, but would still depend on provider availability, limits, and terms.
