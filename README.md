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

The follow-up form currently saves requests to `data/handoff_requests.csv` on the machine running the app. It does not email or otherwise notify staff. Before real student use or deployment, connect it to an approved, access-controlled school system and add the school's official support channel and privacy notice.

The model connection uses an OpenAI-compatible endpoint. Set `AI_BASE_URL` and `AI_MODEL` to use another compatible provider.
