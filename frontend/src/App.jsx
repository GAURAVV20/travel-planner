import { useState } from "react";

const API_URL = "http://localhost:8000";

export default function App() {
  const [form, setForm] = useState({
    destination: "",
    from_location: "",
    budget: "",
    start_date: "",
    end_date: "",
    travel_style: "",
    currency: "USD",
  });
  const [itinerary, setItinerary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [agentStep, setAgentStep] = useState("");

  const AGENT_STEPS = [
    "Flight Agent: searching flights from your origin...",
    "Hotel Agent: finding accommodation...",
    "Activity Agent: planning daily activities...",
    "Budget Allocator: balancing your budget...",
    "Itinerary Compiler: assembling your trip...",
  ];

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setItinerary(null);

    const start = new Date(form.start_date);
    const end = new Date(form.end_date);
    const diffDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24));

    if (diffDays < 1) {
      setError("End date must be after start date.");
      return;
    }

    setLoading(true);

    let stepIdx = 0;
    setAgentStep(AGENT_STEPS[0]);
    const stepTimer = setInterval(() => {
      stepIdx++;
      if (stepIdx < AGENT_STEPS.length) {
        setAgentStep(AGENT_STEPS[stepIdx]);
      }
    }, 1500);

    try {
      const res = await fetch(`${API_URL}/generate-itinerary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          destination: form.destination,
          from_location: form.from_location,
          budget: parseFloat(form.budget),
          days: diffDays,
          start_date: form.start_date,
          end_date: form.end_date,
          travel_style: form.travel_style,
          currency: form.currency,
        }),
      });

      const data = await res.json();
      clearInterval(stepTimer);
      setAgentStep("");

      if (!res.ok) throw new Error(data.detail || "Something went wrong.");
      setItinerary(data.itinerary);
    } catch (err) {
      clearInterval(stepTimer);
      setAgentStep("");
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const CURRENCY_SYMBOL = { USD: "$", INR: "₹", EUR: "€" };
  const symbol = itinerary ? CURRENCY_SYMBOL[itinerary.currency] || "$" : "$";

  const breakdown = itinerary?.budgetBreakdown;
  const categories = breakdown
    ? [
        { label: "Flights", key: "flights", color: "#378ADD" },
        { label: "Hotel", key: "accommodation", color: "#1D9E75" },
        { label: "Food", key: "food", color: "#BA7517" },
        { label: "Activities", key: "activities", color: "#D4537E" },
        { label: "Misc", key: "misc", color: "#888780" },
      ]
    : [];

  const today = new Date().toISOString().split("T")[0];

  return (
    <div style={{ maxWidth: 680, margin: "0 auto", padding: "2rem 1rem", fontFamily: "sans-serif" }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Travel Itinerary Planner</h1>
      <p style={{ fontSize: 14, color: "#666", marginBottom: 24 }}>
        Enter your trip details and the AI agent will plan everything for you.
      </p>

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14, marginBottom: 24 }}>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div>
            <label style={labelStyle}>Travelling From</label>
            <input
              name="from_location"
              value={form.from_location}
              onChange={handleChange}
              placeholder="e.g. Mumbai, India"
              required
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Destination</label>
            <input
              name="destination"
              value={form.destination}
              onChange={handleChange}
              placeholder="e.g. Tokyo, Japan"
              required
              style={inputStyle}
            />
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div>
            <label style={labelStyle}>Budget ({form.currency})</label>
            <input
              name="budget"
              type="number"
              value={form.budget}
              onChange={handleChange}
              placeholder="e.g. 2000"
              required
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Currency</label>
            <select name="currency" value={form.currency} onChange={handleChange} style={inputStyle}>
              <option value="USD">USD — US Dollar</option>
              <option value="INR">INR — Indian Rupee</option>
              <option value="EUR">EUR — Euro</option>
            </select>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div>
            <label style={labelStyle}>Start Date</label>
            <input
              name="start_date"
              type="date"
              value={form.start_date}
              onChange={handleChange}
              min={today}
              required
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>End Date</label>
            <input
              name="end_date"
              type="date"
              value={form.end_date}
              onChange={handleChange}
              min={form.start_date || today}
              required
              style={inputStyle}
            />
          </div>
        </div>

        {form.start_date && form.end_date && new Date(form.end_date) > new Date(form.start_date) && (
          <p style={{ fontSize: 12, color: "#888", margin: "-6px 0 0" }}>
            📅 Trip duration: <strong>{Math.ceil((new Date(form.end_date) - new Date(form.start_date)) / (1000 * 60 * 60 * 24))} days</strong>
          </p>
        )}

        <div>
          <label style={labelStyle}>Travel style (optional)</label>
          <input
            name="travel_style"
            value={form.travel_style}
            onChange={handleChange}
            placeholder="e.g. budget backpacker, luxury, culture & food, adventure..."
            style={inputStyle}
          />
        </div>

        <button type="submit" disabled={loading} style={btnStyle}>
          {loading ? "Planning..." : "Generate Itinerary →"}
        </button>
      </form>

      {loading && agentStep && (
        <div style={agentBoxStyle}>
          <span style={{ fontSize: 13, color: "#555" }}>🤖 {agentStep}</span>
        </div>
      )}

      {error && (
        <div style={{ background: "#fff0f0", border: "1px solid #fcc", borderRadius: 8, padding: "12px 16px", color: "#c00", fontSize: 14, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {/* ---- Itinerary Output ---- */}
      {itinerary && (
        <div>
          <hr style={{ border: "none", borderTop: "1px solid #eee", marginBottom: 20 }} />

          <p style={{ fontSize: 13, color: "#666", marginBottom: 4 }}>
            ✈️ <strong style={{ color: "#222" }}>{form.from_location}</strong> → <strong style={{ color: "#222" }}>{itinerary.destination}</strong>
          </p>
          <p style={{ fontSize: 13, color: "#666", marginBottom: 16 }}>
            📅 {form.start_date} → {form.end_date} &nbsp;·&nbsp; <strong>{itinerary.days.length} days</strong>
          </p>

          <p style={{ fontSize: 13, color: "#666", marginBottom: 6 }}>
            Budget breakdown — {symbol}{itinerary.totalBudget.toLocaleString()} total
          </p>
          <div style={{ display: "flex", height: 10, borderRadius: 6, overflow: "hidden", gap: 2, marginBottom: 8 }}>
            {categories.map((cat) => {
              const pct = Math.round((breakdown[cat.key] / itinerary.totalBudget) * 100);
              return pct > 0 ? (
                <div key={cat.key} style={{ width: `${pct}%`, background: cat.color, minWidth: 4 }} title={`${cat.label}: ${symbol}${breakdown[cat.key]}`} />
              ) : null;
            })}
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 20 }}>
            {categories.map((cat) => (
              <span key={cat.key} style={{ fontSize: 12, color: "#666", display: "flex", alignItems: "center", gap: 4 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: cat.color, display: "inline-block" }} />
                {cat.label} {symbol}{breakdown[cat.key].toLocaleString()}
              </span>
            ))}
          </div>

          <p style={{ fontSize: 13, color: "#666", marginBottom: 20 }}>
            🏨 Staying at: <strong style={{ color: "#222" }}>{itinerary.accommodation}</strong>
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {itinerary.days.map((d) => (
              <div key={d.day} style={cardStyle}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
                  <strong style={{ fontSize: 14 }}>Day {d.day} — {d.title}</strong>
                  <span style={{ fontSize: 12, color: "#888" }}>~{symbol}{d.estimatedCost}</span>
                </div>
                {[["Morning", d.morning], ["Afternoon", d.afternoon], ["Evening", d.evening]].map(([label, text]) => (
                  <div key={label} style={{ display: "flex", gap: 10, marginBottom: 5 }}>
                    <span style={{ fontSize: 12, color: "#888", minWidth: 68 }}>{label}</span>
                    <span style={{ fontSize: 13 }}>{text}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>

          {itinerary.tips?.length > 0 && (
            <div style={{ marginTop: 16, background: "#f8f8f8", borderRadius: 8, padding: "12px 16px" }}>
              <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>💡 Travel tips</p>
              {itinerary.tips.map((tip, i) => (
                <p key={i} style={{ fontSize: 13, color: "#555", margin: "0 0 4px" }}>— {tip}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const labelStyle = { fontSize: 13, color: "#555", display: "block", marginBottom: 4 };
const inputStyle = { width: "100%", padding: "8px 10px", fontSize: 14, border: "1px solid #ddd", borderRadius: 6, boxSizing: "border-box" };
const btnStyle = { padding: "10px 16px", fontSize: 14, fontWeight: 600, background: "#111", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" };
const cardStyle = { background: "#fff", border: "1px solid #eee", borderRadius: 10, padding: "14px 16px" };
const agentBoxStyle = { background: "#f5f5f5", borderRadius: 8, padding: "10px 14px", marginBottom: 16 };
