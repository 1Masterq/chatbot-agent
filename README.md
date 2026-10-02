# Chatbot Agent

A Python-first freshman help desk built with Streamlit. It answers from school-approved information, handles simple greetings without an API connection, and lets students save unanswered questions for staff follow-up.

## Run locally

1. Install Python 3.11 or newer.
2. Create a virtual environment: `py -m venv .venv`.
3. Activate it: `.\\.venv\\Scripts\\Activate.ps1`.
4. Install dependencies: `python -m pip install -r requirements.txt`.
5. Copy `.env.example` to `.env.local` and set `AI_API_KEY`.
6. Start the app: `streamlit run app.py`.
7. Open the local URL shown by Streamlit, usually `http://localhost:8501`.

Fill in `school_info.md` with facts verified by school staff. The assistant must not invent school-specific rules, course offerings, or HOD names; if a fact is missing, it will tell the student and offer a staff follow-up form.

The follow-up form saves requests to `data/handoff_requests.csv` and asks the student for consent before submitting. To email staff, configure `STAFF_EMAIL` and the `SMTP_*` values in local `.env.local` using sender settings approved by school IT. Without those settings, requests remain only on the machine running the app and staff are not notified. For deployment, configure these as the host's private secrets, not in GitHub, and add the school's privacy notice and retention policy.

The model connection currently uses OpenAI's API. API access requires available API billing/credits; a valid key by itself does not provide credits. Set `AI_BASE_URL` and `AI_MODEL` to use another compatible provider. The app reports common credit, permission, model, and service errors separately.
