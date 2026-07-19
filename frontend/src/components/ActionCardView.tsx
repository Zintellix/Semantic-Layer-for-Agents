import { useState } from "react";
import type { ActionCard } from "../types";
import { api } from "../api";

export function ActionCardView({ card, domain }: { card: ActionCard; domain: string }) {
  const [status, setStatus] = useState(card.status);
  const [reason, setReason] = useState(card.reason);
  const [busy, setBusy] = useState(false);

  const blocked = status === "BLOCKED" || status === "REJECTED";

  async function approve() {
    setBusy(true);
    try {
      const r = await api.approve(domain, card.action_id);
      setStatus(r.status);
      setReason(r.reason);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`action-card tier-${card.tier} ${blocked ? "blocked" : ""}`}>
      <div className="action-head">
        <span className="badge">Tier {card.tier}</span>
        <span className={`status status-${status.toLowerCase()}`}>{status}</span>
        {card.connector_write !== "none" && (
          <span className="badge muted">write: {card.connector_write}</span>
        )}
      </div>
      <div className="action-title">
        {card.action_type}
        <span className="action-args">
          (variant={card.target_title}
          {Object.entries(card.params).map(([k, v]) => `, ${k}=${v}`)})
        </span>
      </div>
      {card.guards_passed.length > 0 && (
        <div className="action-meta">✓ guards passed: {card.guards_passed.join(", ")}</div>
      )}
      {reason && <div className="action-meta warn">{reason}</div>}
      {card.fallback && (
        <div className="action-meta">↳ fallback: {card.fallback}</div>
      )}
      {card.tier === 2 && status === "PROPOSED" && (
        <button className="btn small" disabled={busy} onClick={approve}>
          {busy ? "…" : "Approve (Tier-2 gate)"}
        </button>
      )}
    </div>
  );
}
