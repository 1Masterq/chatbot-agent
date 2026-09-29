# Chatbot Agent

A Python-first chatbot workspace built with Streamlit. The app keeps the conversation UI and agent logic in Python and uses an OpenAI-compatible chat completions endpoint.

## Run locally

1. Install Python 3.11 or newer.
2. Create a virtual environment: `py -m venv .venv`.
3. Activate it: `.\\.venv\\Scripts\\Activate.ps1`.
4. Install dependencies: `python -m pip install -r requirements.txt`.
5. Copy `.env.example` to `.env` and set `AI_API_KEY`.
6. Start the app: `streamlit run app.py`.
7. Open the local URL shown by Streamlit, usually `http://localhost:8501`.

The agent uses an OpenAI-compatible endpoint. Set `AI_BASE_URL` and `AI_MODEL` to use another compatible provider.
