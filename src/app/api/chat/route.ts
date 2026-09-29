import { NextResponse } from "next/server";

type ChatMessage = { role: "user" | "assistant"; content: string };

export async function POST(request: Request) {
  const body = (await request.json()) as { messages?: ChatMessage[] };
  const messages = body.messages ?? [];
  const apiKey = process.env.AI_API_KEY;

  if (!messages.length) return NextResponse.json({ message: "Send a message to begin." }, { status: 400 });
  if (!apiKey || apiKey === "your_api_key_here") {
    return NextResponse.json({ message: "I’m ready to help. Add your AI_API_KEY to .env.local to connect Northstar to a model provider." });
  }

  const baseUrl = process.env.AI_BASE_URL ?? "https://api.openai.com/v1";
  const model = process.env.AI_MODEL ?? "gpt-4o-mini";
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({ model, messages: [{ role: "system", content: "You are Northstar, a thoughtful and concise AI thinking partner. Help users clarify ideas and take useful next steps." }, ...messages] }),
  });

  if (!response.ok) return NextResponse.json({ message: "The model provider returned an error. Check your AI settings and try again." }, { status: 502 });
  const result = (await response.json()) as { choices?: Array<{ message?: { content?: string } }> };
  return NextResponse.json({ message: result.choices?.[0]?.message?.content ?? "The agent returned no text." });
}
