"use client";

import { FormEvent, useState } from "react";

type Message = { role: "user" | "assistant"; content: string };

const starters = [
  "Turn a messy idea into a clear plan",
  "Help me think through a difficult decision",
  "Draft a concise message for my team",
];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);

  async function sendMessage(event?: FormEvent) {
    event?.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isThinking) return;

    const nextMessages = [...messages, { role: "user" as const, content: trimmed }];
    setMessages(nextMessages);
    setInput("");
    setIsThinking(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: nextMessages }),
      });
      const data = await response.json();
      setMessages([...nextMessages, { role: "assistant", content: data.message ?? "I could not complete that request." }]);
    } catch {
      setMessages([...nextMessages, { role: "assistant", content: "The agent is unreachable right now. Check the local server and try again." }]);
    } finally {
      setIsThinking(false);
    }
  }

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">N</span><span>northstar</span></div>
        <div className="side-section">
          <p className="eyebrow">Workspace</p>
          <button className="nav-item active"><span>✦</span> New conversation</button>
          <button className="nav-item"><span>◷</span> History</button>
        </div>
        <div className="side-section recent">
          <p className="eyebrow">Recent</p>
          <button className="recent-item">Untangling the product brief</button>
          <button className="recent-item">A sharper weekly rhythm</button>
          <button className="recent-item">Launch notes, first draft</button>
        </div>
        <div className="sidebar-footer"><span className="status-dot" /> Agent online <span className="version">v0.1</span></div>
      </aside>

      <section className="conversation">
        <header className="topbar"><div><p className="eyebrow">Personal studio</p><h1>New conversation</h1></div><button className="icon-button" aria-label="Open settings">•••</button></header>
        <div className="conversation-body">
          {messages.length === 0 ? (
            <div className="welcome">
              <div className="orb" aria-hidden="true"><span>✦</span></div>
              <p className="eyebrow">Your thinking partner</p>
              <h2>What are we<br /><em>making sense of?</em></h2>
              <p className="welcome-copy">Bring a question, a rough thought, or a blank page. Northstar helps you find the useful next step.</p>
              <div className="starter-grid">{starters.map((starter) => <button key={starter} onClick={() => setInput(starter)}>{starter}<span>↗</span></button>)}</div>
            </div>
          ) : (
            <div className="messages">{messages.map((message, index) => <div className={`message ${message.role}`} key={`${message.role}-${index}`}><div className="message-label">{message.role === "user" ? "You" : "Northstar"}</div><p>{message.content}</p></div>)}{isThinking && <div className="message assistant"><div className="message-label">Northstar</div><p className="thinking">Thinking<span>.</span><span>.</span><span>.</span></p></div>}</div>
          )}
        </div>
        <form className="composer" onSubmit={sendMessage}>
          <textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void sendMessage(); } }} placeholder="Ask anything..." rows={1} aria-label="Message Northstar" />
          <button className="send-button" type="submit" disabled={!input.trim() || isThinking} aria-label="Send message">↑</button>
          <div className="composer-hint">Northstar can make mistakes. Check important details.</div>
        </form>
      </section>
    </main>
  );
}
