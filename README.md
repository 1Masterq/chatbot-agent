# Chatbot Agent

A Python-first freshman help desk built with Streamlit. It searches school-approved information locally, handles simple greetings, and lets students prepare unanswered questions for staff by email. It uses no paid AI API and requires no SMTP credentials.

## Run locally

1. Install Python 3.11 or newer.
2. Create a virtual environment: `py -m venv .venv`.
3. Activate it: `.\\.venv\\Scripts\\Activate.ps1`.
4. Install dependencies: `python -m pip install -r requirements.txt`.
5. Start the app: `streamlit run app.py`.
6. Open the local URL shown by Streamlit, usually `http://localhost:8501`.

Fill in `school_info.md` with facts verified by school staff. The assistant must not invent school-specific rules, course offerings, or HOD names; if a fact is missing, it will tell the student and offer a staff follow-up form.

The follow-up form saves requests to `data/handoff_requests.csv` and asks the student for consent. It can then open a prefilled email to the configured staff address using the student's own mail app. The student must review and press Send; the app does not send email by itself. For deployment, add the school's privacy notice and retention policy.

This version is an extractive local search assistant, not a generative large language model. It returns matching approved handbook text and directs unmatched questions to staff. A future free-tier model could write more conversational answers, but would still depend on provider availability, limits, and terms.
