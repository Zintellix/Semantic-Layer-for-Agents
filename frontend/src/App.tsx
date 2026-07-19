import { useEffect, useState } from "react";
import { api } from "./api";
import type { AskResult, DomainInfo, Health, ObjectsView, SignalResult } from "./types";
import { TraceView } from "./components/TraceView";
import { AnswerView } from "./components/AnswerView";
import { ActionCardView } from "./components/ActionCardView";
import { ObjectTable } from "./components/ObjectTable";
import { SignalPanel } from "./components/SignalPanel";

export function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [domain, setDomain] = useState<string>("cosmetics");
  const [tab, setTab] = useState<"ask" | "signal" | "data">("ask");

  const [question, setQuestion] = useState("");
  const [useLlm, setUseLlm] = useState(false);
  const [result, setResult] = useState<AskResult | null>(null);
  const [asking, setAsking] = useState(false);
  const [showCtx, setShowCtx] = useState(false);

  const [view, setView] = useState<ObjectsView | null>(null);
  const [signal, setSignal] = useState<SignalResult | null>(null);

  const current = domains.find((d) => d.name === domain);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
    api.domains().then((r) => setDomains(r.domains)).catch(() => {});
  }, []);

  // when the domain changes, reset to its flagship + reload its objects
  useEffect(() => {
    const d = domains.find((x) => x.name === domain);
    if (d) setQuestion(d.flagship);
    setResult(null);
    setSignal(null);
    api.objects(domain).then(setView).catch(() => setView(null));
  }, [domain, domains]);

  async function ask(q: string) {
    setAsking(true);
    setResult(null);
    try {
      setResult(await api.ask(q, domain, useLlm));
    } catch (e) {
      setResult({ question: q, domain, stages: [], status: "ERROR", error: String(e) });
    } finally {
      setAsking(false);
    }
  }

  async function fireSignal(key: string) {
    setTab("signal");
    setSignal(await api.signal(domain, key));
  }

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <span className="logo">◈</span>
          <div>
            <h1>ZINTELLIX</h1>
            <div className="sub">Agentic OS for Commerce · Semantic Layer POC</div>
          </div>
        </div>
        <div className="health">
          {health ? (
            <>
              <span className="pill">ontology v{health.ontology_version}</span>
              <span className={`pill ${health.llm_available ? "ok" : "muted"}`}>
                {health.llm_available ? `agent: ${health.provider}` : "offline reasoner"}
              </span>
            </>
          ) : (
            <span className="pill muted">backend offline</span>
          )}
        </div>
      </header>

      <div className="domain-bar">
        <span className="field-label" style={{ margin: 0 }}>
          Domain
        </span>
        <div className="domain-chips">
          {domains.map((d) => (
            <button
              key={d.name}
              className={`domain-chip ${d.name === domain ? "active" : ""}`}
              onClick={() => setDomain(d.name)}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      <nav className="tabs">
        <button className={tab === "ask" ? "active" : ""} onClick={() => setTab("ask")}>
          Ask
        </button>
        <button className={tab === "signal" ? "active" : ""} onClick={() => setTab("signal")}>
          Signal → Severity
        </button>
        <button className={tab === "data" ? "active" : ""} onClick={() => setTab("data")}>
          Seeded objects
        </button>
      </nav>

      {tab === "ask" && (
        <main className="two-col">
          <section className="panel">
            <label className="field-label">Ask the {current?.label ?? domain} semantic layer</label>
            <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={2} />
            <div className="controls">
              <button className="btn" disabled={asking} onClick={() => ask(question)}>
                {asking ? "Running pipeline…" : "Run"}
              </button>
              <label className="toggle" title={health?.llm_available ? "" : "no API key in .env"}>
                <input
                  type="checkbox"
                  checked={useLlm}
                  disabled={!health?.llm_available}
                  onChange={(e) => setUseLlm(e.target.checked)}
                />
                use {health?.provider ?? "LLM"} agent
              </label>
            </div>
            <div className="samples">
              {(current?.samples ?? []).map((s) => (
                <button key={s} className="chip" onClick={() => (setQuestion(s), ask(s))}>
                  {s.length > 46 ? s.slice(0, 46) + "…" : s}
                </button>
              ))}
            </div>

            {result && result.status === "CLARIFY" && result.clarification && (
              <div className="clarify">
                <b>Clarification needed</b> for “{result.clarification.surface}” (conf{" "}
                {result.clarification.confidence} &lt; 0.70). Principle O6 — no guess.
                <ul>
                  {result.clarification.candidates.map((c) => (
                    <li key={c.target_id}>
                      {c.label} <span className="muted">({c.confidence})</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {result && result.status === "SEMANTIC_GAP" && (
              <div className="clarify warn">Query rejected: {result.error}</div>
            )}
            {result && result.status === "ERROR" && (
              <div className="clarify warn">Error: {result.error}</div>
            )}

            {result && result.answer && (
              <>
                <div className="answer-head">
                  <span className={`conf conf-${result.status?.toLowerCase()}`}>
                    {result.status} · confidence {result.confidence}
                  </span>
                  {result.agent && (
                    <span className="muted small">
                      {result.agent.source} · {result.agent.model} · {result.agent.ctx_tokens} ctx
                      tokens
                    </span>
                  )}
                </div>
                <AnswerView answer={result.answer} />
                {result.action_card && <ActionCardView card={result.action_card} domain={domain} />}
                {result.context_block && (
                  <div className="ctx">
                    <button className="link" onClick={() => setShowCtx(!showCtx)}>
                      {showCtx ? "hide" : "show"} Ontology Context block →
                    </button>
                    {showCtx && <pre>{result.context_block}</pre>}
                  </div>
                )}
              </>
            )}
          </section>

          <section className="panel trace-panel">
            <label className="field-label">7-stage pipeline trace</label>
            {result ? (
              <TraceView stages={result.stages} />
            ) : (
              <p className="muted">Run a query to see the semantic-layer trace.</p>
            )}
          </section>
        </main>
      )}

      {tab === "signal" && (
        <main className="panel">
          <label className="field-label">Lift a raw signal → typed event → severity → action</label>
          <p className="muted small">
            A top object of the set → CRITICAL and an escalation card; a non-top object → HIGH,
            and the guard blocks the escalation and falls back to flag-for-review. Fire one from
            the “Seeded objects” tab.
          </p>
          {signal ? (
            <SignalPanel result={signal} />
          ) : (
            <p className="muted">No signal lifted yet — pick one from Seeded objects.</p>
          )}
        </main>
      )}

      {tab === "data" && (
        <main className="panel">
          <label className="field-label">
            {current?.label ?? domain} objects — read live through the binding layer (L4)
          </label>
          {view ? (
            <ObjectTable view={view} onSignal={fireSignal} />
          ) : (
            <p className="muted">Loading…</p>
          )}
        </main>
      )}

      <footer className="footer">
        One engine, many verticals · every number traces to seeded data through the binding layer;
        every entity to an object ID · 13 layers, built thin.
      </footer>
    </div>
  );
}
