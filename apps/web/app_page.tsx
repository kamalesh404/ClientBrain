"use client";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [workspace, setWorkspace] = useState("demo");
  const [apiKey, setApiKey] = useState("");
  const [message, setMessage] = useState("What are your timings?");
  const [answer, setAnswer] = useState("");
  const [stats, setStats] = useState<any>(null);
  const [plans, setPlans] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const headers = () => ({
    "Content-Type": "application/json",
    ...(apiKey ? { "X-API-Key": apiKey } : {}),
  });

  async function refresh() {
    const s = await fetch(`${API}/v1/stats?workspace=${workspace}`, { headers: headers() }).then((r) => r.json());
    setStats(s);
    const p = await fetch(`${API}/v1/billing/plans`).then((r) => r.json());
    setPlans(p.plans);
  }

  useEffect(() => { refresh(); }, []);

  async function send() {
    setLoading(true);
    const r = await fetch(`${API}/v1/chat`, {
      method: "POST", headers: headers(),
      body: JSON.stringify({ workspace, message }),
    });
    const j = await r.json();
    setAnswer(r.status === 402 ? `QUOTA HIT: ${j.detail} — upgrade below.` : j.answer || JSON.stringify(j));
    setLoading(false);
    refresh();
  }

  async function order(provider: "razorpay" | "stripe", plan: string) {
    const ep = provider === "razorpay" ? "razorpay/order" : "stripe/session";
    const j = await fetch(`${API}/v1/billing/${ep}`, {
      method: "POST", headers: headers(),
      body: JSON.stringify({ workspace, plan }),
    }).then((r) => r.json());
    alert(`${provider} order (${j.mock ? "MOCK — add keys for live" : "LIVE"}):\n` + JSON.stringify(j, null, 2));
  }

  return (
    <main style={{ maxWidth: 760, margin: "40px auto", fontFamily: "system-ui", padding: 16 }}>
      <h1>🧠 ClientBrain <small style={{ fontWeight: 400 }}>Phase 2 — billing + quotas</small></h1>
      <div style={{ display: "flex", gap: 8 }}>
        <input value={workspace} onChange={(e) => setWorkspace(e.target.value)} placeholder="workspace" />
        <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="X-API-Key (optional)" style={{ flex: 1 }} />
        <button onClick={refresh}>Stats</button>
      </div>
      <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3} style={{ width: "100%", marginTop: 8 }} />
      <button onClick={send} disabled={loading}>{loading ? "..." : "Ask"}</button>
      <pre style={{ whiteSpace: "pre-wrap", background: "#f5f5f5", padding: 16 }}>{answer}</pre>

      {stats && (
        <section style={{ border: "1px solid #ddd", padding: 12, borderRadius: 8 }}>
          <h3>Usage — {stats.workspace} ({stats.plan}) [{stats.backend}]</h3>
          <code>{JSON.stringify(stats.usage)} / quota {JSON.stringify(stats.quota)} → left {JSON.stringify(stats.remaining)}</code>
        </section>
      )}

      {plans && (
        <section style={{ marginTop: 16 }}>
          <h3>Pricing</h3>
          {Object.entries(plans).map(([name, p]: any) => (
            <div key={name} style={{ border: "1px solid #eee", padding: 8, marginBottom: 8 }}>
              <b>{name}</b> — {p.messages} msgs / {p.docs} docs — ₹{p.price_inr / 100} / ${p.price_usd / 100}
              <button style={{ marginLeft: 8 }} onClick={() => order("razorpay", name)}>Razorpay</button>
              <button style={{ marginLeft: 4 }} onClick={() => order("stripe", name)}>Stripe</button>
            </div>
          ))}
          <p><small>Without keys orders are MOCK — perfect for demos. Add keys in <code>.env</code> for live.</small></p>
        </section>
      )}
      <p>API docs: <a href={`${API}/docs`}>{API}/docs</a></p>
    </main>
  );
}
