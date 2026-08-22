"""L10 · Agent Runtime (multi-domain).

Everything the agent may know or do arrives as structure — the Ontology Context
block built from the L7 prefetch. Given only that block, the agent computes the
answer itself.

Provider: OpenAI when OPENAI_API_KEY is set (Anthropic if only ANTHROPIC_API_KEY
is), otherwise a deterministic reasoner runs offline so the demo works cold. The
reasoner is also the ground truth the grounding validator (L11) checks against.
Cosmetics keeps its exact §5.3 narrative; other domains use a generic reasoner
driven by the domain manifest's metric spec (timeline or aggregate).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from . import config


@dataclass
class AgentResponse:
    answer: str
    entities: list[str] = field(default_factory=list)
    numbers: list[float] = field(default_factory=list)
    action: Optional[dict] = None
    source: str = "fallback"
    model: str = "deterministic"
    ctx_tokens: int = 0
    confidence: float = 0.91
    context_block: str = ""


# ---------------------------------------------------------------------------
# Ontology Context block (generic across domains)
# ---------------------------------------------------------------------------
def build_context(plan, window, domain, registry) -> str:
    lines = ["--- ONTOLOGY CONTEXT ---", "Objects:"]
    for oid, bag in plan.prefetch.items():
        title = bag.get("display_title") or bag.get("name") or oid
        props = "  ".join(
            f"{k}={_fmt(v)}" for k, v in bag.items()
            if not k.startswith("_") and k not in ("display_title", "name"))
        lines.append(f'  [{oid}] "{title}"  {props}')
    for os_ in plan.object_sets:
        ids = [pid.split(":")[-1] for pid in os_["members"]]
        lines.append(f"Object set: {os_['function_id']} -> {ids}")
    if window:
        lines.append(f"Window: {window['window']} starts in {window['starts_in_days']} days, "
                     f"runs {window['duration_days']} days, +{window['expected_uplift_pct']}% demand")
    if plan.traversals:
        lines.append(f"Traversal used: {plan.traversals[0]}")
    lines.append("Allowed actions:")
    acts = []
    if domain and registry:
        for a in registry.actions_for(domain.primary_type):
            params = ", ".join(f"{n}: {p.type}" for n, p in a.parameters.items())
            acts.append(f"  {a.action_type}({params}) [Tier {a.tier}]")
    lines += acts or ["  (none)"]
    lines += [
        "",
        "GROUNDING RULES",
        "  Every entity you name must appear above with its object ID.",
        "  Every number you state must derive from the values above; show the arithmetic.",
        "  Every action you propose must be one of the allowed actions.",
        "  If you cannot ground a claim, say so. Do not estimate.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Cosmetics reasoner — exact §5.3 narrative (ground truth + offline fallback)
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Generic domain reasoner — driven by the manifest metric spec
# ---------------------------------------------------------------------------
def reason_domain(plan, window, domain) -> AgentResponse:
    m = domain.metric
    if m.mode == "timeline":
        return _reason_timeline(plan, window, domain)
    return _reason_aggregate(plan, domain)


def _reason_timeline(plan, window, domain) -> AgentResponse:
    m = domain.metric
    entities, numbers, parts = [], [], []
    if window is None:
        for oid, b in plan.prefetch.items():
            entities.append(oid)
            lvl, rate = b.get(m.level), b.get(m.rate)
            days = lvl / rate if rate else 0
            numbers.append(round(days, 1))
            parts.append(f"{_title(b, oid)} [{oid}] has {_fmt(round(days, 1))} days of runway.")
        return AgentResponse("\n".join(parts), entities, numbers, source="fallback",
                             model="deterministic", confidence=0.85)

    starts = window["starts_in_days"]; duration = window["duration_days"]
    uplift = 1 + window["expected_uplift_pct"] / 100.0
    alarms, nuances, comfortable = [], [], []
    for oid, b in plan.prefetch.items():
        entities.append(oid)
        lvl, rate = b.get(m.level), b.get(m.rate)
        remaining = lvl - starts * rate
        peak = rate * uplift
        rec = {"oid": oid, "title": _title(b, oid), "lvl": lvl, "rate": rate,
               "remaining": round(remaining, 1), "peak": round(peak, 2)}
        if remaining <= 0:
            rec["day"] = round(lvl / rate, 1); alarms.append(rec)
        else:
            d = remaining / peak
            rec["day"] = round(d, 1)
            (alarms if d < duration else nuances if d < duration + 3 else comfortable).append(rec)

    if alarms:
        a = alarms[0]
        parts.append(f"Yes — {a['title']} will hit {m.event_noun} first.\n")
        parts.append(
            f"{a['title']} [{a['oid']}] holds {_fmt(a['lvl'])} {m.unit} and burns "
            f"{_fmt(a['rate'])}/day. Over the {starts} days before {window['window']} it "
            f"spends {_fmt(round(starts * a['rate'], 1))}, leaving {_fmt(a['remaining'])}. "
            f"During the peak demand rises to {_fmt(a['peak'])}/day — {_fmt(a['remaining'])} / "
            f"{_fmt(a['peak'])} = {_fmt(a['day'])} days.\n"
            f"-> {m.event_noun.capitalize()} on day {_fmt(a['day'])} of the {window['window']}.")
        numbers += [a['lvl'], a['rate'], a['remaining'], a['peak'], a['day']]
        headline = a
    else:
        parts.append(f"No — all clear through {window['window']}."); headline = None
    for n in nuances:
        parts.append(f"\n{n['title']} [{n['oid']}] survives by ~"
                     f"{_fmt(round(n['day'] - duration, 1))} day "
                     f"({_fmt(n['day'])} days vs a {duration}-day peak) — watch it.")
        numbers += [n['day']]
    for c in comfortable:
        parts.append(f"\n{c['title']} [{c['oid']}] is comfortable.")

    action = _build_action(domain, headline["oid"], window) if headline else None
    return AgentResponse("\n".join(parts), entities, numbers, action=action,
                         source="fallback", model="deterministic", confidence=0.91)


def _reason_aggregate(plan, domain) -> AgentResponse:
    m = domain.metric
    entities, numbers, parts = [], [], []
    members = []
    total = 0.0
    for oid, b in plan.prefetch.items():
        entities.append(oid)
        v = b.get(m.value) or 0
        total += v
        members.append({"oid": oid, "title": _title(b, oid), "v": v})
        numbers.append(v)
    members.sort(key=lambda x: x["v"], reverse=True)
    total = round(total, 0)
    threshold = m.threshold
    numbers += [total, threshold]

    if m.direction == "at_least":
        gap = round(threshold - total, 0)
        if gap > 0:
            parts.append(f"Yes — short of {m.threshold_label}. The top {len(members)} commit "
                         f"{m.unit}{_money(total)} against {m.unit}{_money(threshold)} — "
                         f"short by {m.unit}{_money(gap)}.")
            numbers.append(gap)
        else:
            parts.append(f"No — {m.threshold_label} covered. {m.unit}{_money(total)} vs "
                         f"{m.unit}{_money(threshold)}.")
    else:  # at_most
        over = round(total - threshold, 0)
        if over > 0:
            parts.append(f"Yes — over the line. {m.event_noun.capitalize()} exposure across the "
                         f"top {len(members)} is {m.unit}{_money(total)} against a {m.unit}"
                         f"{_money(threshold)} {m.threshold_label} — {m.unit}{_money(over)} over.")
            numbers.append(over)
        else:
            parts.append(f"No — within budget. {m.unit}{_money(total)} vs "
                         f"{m.unit}{_money(threshold)} {m.threshold_label}.")

    parts.append("")
    for mem in members:
        parts.append(f"{mem['title']} [{mem['oid']}] contributes {m.unit}{_money(mem['v'])}.")

    action = _build_action(domain, members[0]["oid"], None) if members else None
    return AgentResponse("\n".join(parts), entities, numbers, action=action,
                         source="fallback", model="deterministic", confidence=0.9)


def _build_action(domain, object_id, window) -> dict:
    val = 1.0
    if domain.action.param_mode == "window_start" and window:
        val = float(window["starts_in_days"])
    return {"action_type": domain.action.action_type, "object_id": object_id,
            "params": {domain.action.param: val}}


# ---------------------------------------------------------------------------
# Provider selection + LLM calls
# ---------------------------------------------------------------------------
def _openai_available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _anthropic_available() -> bool:
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    from pathlib import Path
    return (Path.home() / ".config" / "anthropic" / "credentials").exists()


def _gemini_available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))

def pick_provider() -> Optional[str]:
    p = config.AGENT_PROVIDER
    if p == "off":
        return None
    if p == "gemini":
        return "gemini" if _gemini_available() else None
    if p == "openai":
        return "openai" if _openai_available() else None
    if p == "anthropic":
        return "anthropic" if _anthropic_available() else None
    if _gemini_available():
        return "gemini"
    if p == "openai":
        return "openai" if _openai_available() else None
    if p == "anthropic":
        return "anthropic" if _anthropic_available() else None
    if _openai_available():
        return "openai"
    if _anthropic_available():
        return "anthropic"
    return None


def _credentials_available() -> bool:      # kept for api.py
    return pick_provider() is not None


_SYSTEM = (
    "You are the Zintellix semantic-layer agent. You may only use the objects, "
    "numbers, and actions in the ONTOLOGY CONTEXT block. Compute arithmetic "
    "yourself; never invent a number or an entity. Respond ONLY with JSON matching: "
    '{"answer": str, "entities": [object_id...], "numbers": [number...], '
    '"action": {"action_type": str, "object_id": str, "params": {}} | null}.')


class Agent:
    def __init__(self, use_llm: Optional[bool] = None):
        self.provider = pick_provider()
        self.use_llm = (self.provider is not None) if use_llm is None else use_llm

    def run(self, plan, resolutions, window, question, domain=None, registry=None) -> AgentResponse:
        context = build_context(plan, window, domain, registry)
        ground = reason_domain(plan, window, domain)
        ground.context_block = context
        ground.ctx_tokens = len(context.split())

        if not self.use_llm or self.provider is None:
            return ground
        try:
            llm = self._call_llm(context, question)
            llm.context_block = context
            llm.ctx_tokens = ground.ctx_tokens
            if not llm.action:
                llm.action = ground.action
            return llm
        except Exception as e:  # noqa: BLE001 — any failure falls back to the reasoner
            ground.answer += f"\n\n(agent fell back to deterministic reasoner: {e})"
            return ground

    def _call_llm(self, context, question) -> AgentResponse:
        if self.provider == "gemini":
            return self._call_gemini(context, question)
        if self.provider == "openai":
            return self._call_openai(context, question)
        return self._call_anthropic(context, question)

    def _call_gemini(self, context, question) -> AgentResponse:
        from google import genai
        from google.genai import types
        
        client = genai.Client()
        prompt = f"{context}\n\nQUESTION: {question}"
        model = os.environ.get("ZX_AGENT_MODEL", "gemini-2.5-flash")
        
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM,
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        data = json.loads(response.text or "{}")
        return _from_json(data, source="llm", model=model)

    def _call_openai(self, context, question) -> AgentResponse:
        from openai import OpenAI
        client = OpenAI()
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL, temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": f"{context}\n\nQUESTION: {question}"}])
        data = json.loads(resp.choices[0].message.content or "{}")
        return _from_json(data, source="llm", model=config.OPENAI_MODEL)

    def _call_anthropic(self, context, question) -> AgentResponse:
        import anthropic
        client = anthropic.Anthropic()
        model = os.environ.get("ZX_AGENT_MODEL", "claude-opus-4-8")
        resp = client.messages.create(
            model=model, max_tokens=2000, thinking={"type": "adaptive"},
            output_config={"effort": "medium"}, system=_SYSTEM,
            messages=[{"role": "user", "content": f"{context}\n\nQUESTION: {question}"}])
        text = next((b.text for b in resp.content if b.type == "text"), "{}")
        return _from_json(json.loads(_extract_json(text)), source="llm", model=model)


def _from_json(data, source, model) -> AgentResponse:
    return AgentResponse(
        answer=data.get("answer", ""), entities=data.get("entities", []),
        numbers=[float(n) for n in data.get("numbers", []) if _isnum(n)],
        action=data.get("action"), source=source, model=model, confidence=0.91)


# ---- formatting helpers ----------------------------------------------
def _title(bag, oid):
    return bag.get("display_title") or bag.get("name") or oid


def _isnum(n):
    return isinstance(n, (int, float))


def _money(v):
    try:
        return f"{float(v):,.0f}"
    except Exception:  # noqa: BLE001
        return str(v)


def _extract_json(text: str) -> str:
    s, e = text.find("{"), text.rfind("}")
    return text[s:e + 1] if s >= 0 and e > s else "{}"


def _fmt(v):
    if v is None:
        return "?"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)
