"use client";
import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [workspace, setWorkspace] = useState("demo");
  const [message, setMessage] = useState("What are your timings?");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  async function send() {
    setLoading(true);
    const r = await fetch(`${API}/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace, message }),
    });
    const j = await r.json();
    setAnswer(j.answer || JSON.stringify(j));
    setLoading(false);
  }

  return (
    <main style={{ maxWidth: 720, margin: "40px auto", fontFamily: "system-ui" }}>
      <h1>🧠 ClientBrain</h1>
      <p>Sellable RAG chatbot — ingest your site, embed the widget, charge monthly.</p>
      <input value={workspace} onChange={(e) => setWorkspace(e.target.value)} placeholder="workspace" />
      <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3} style={{ width: "100%" }} />
      <button onClick={send} disabled={loading}>{loading ? "..." : "Ask"}</button>
      <pre style={{ whiteSpace: "pre-wrap", background: "#f5f5f5", padding: 16 }}>{answer}</pre>
      <p>API docs: <a href={`${API}/docs`}>{API}/docs</a></p>
    </main>
  );
}
