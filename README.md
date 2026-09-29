# Chatbot Agent

A focused Next.js workspace for a conversational AI agent. The UI is ready for local development and the server route keeps model credentials off the client.

## Run locally

1. Install Node.js 20 or newer.
2. Run `npm install`.
3. Copy `.env.example` to `.env.local` and set `AI_API_KEY`.
4. Run `npm run dev`.
5. Open `http://localhost:3000`.

The agent uses an OpenAI-compatible chat completions endpoint. Set `AI_BASE_URL` and `AI_MODEL` to use another compatible provider.
