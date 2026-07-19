import type { SignalResult } from "../types";
import { ActionCardView } from "./ActionCardView";

export function SignalPanel({ result }: { result: SignalResult }) {
  const sev = result.lifted.severity;
  return (
    <div className="signal-panel">
      <div className="signal-flow">
        <div className="flow-step">
          <span className="flow-label">signal</span>
          <code>
            {result.signal.type} · {result.signal.key}
          </code>
        </div>
        <div className="flow-arrow">→</div>
        <div className="flow-step">
          <span className="flow-label">lift</span>
          <code>{result.lifted.event_type}</code>
          <div className="muted small">
            {result.lifted.title} · {result.lifted.variant}
          </div>
        </div>
        <div className="flow-arrow">→</div>
        <div className="flow-step">
          <span className="flow-label">decide</span>
          <span className={`sev sev-${sev.toLowerCase()}`}>{sev}</span>
        </div>
      </div>

      <div className="sev-trace">
        {result.severity_trace.map((t, i) => (
          <div key={i} className="trace-line">
            {t}
          </div>
        ))}
        <div className="muted small">
          severity rule lives in the cosmetics pack — zero vertical code outside it
        </div>
      </div>

      <div className="cards-row">
        <ActionCardView card={result.proposal} domain={result.domain} />
        {result.fallback && (
          <>
            <div className="flow-arrow small">falls back to</div>
            <ActionCardView card={result.fallback} domain={result.domain} />
          </>
        )}
      </div>
    </div>
  );
}
