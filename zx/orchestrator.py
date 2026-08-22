"""L12 · Orchestrator & CLI (multi-domain).

Seven stages, driven by the selected domain's manifest:
  1. parse     keyword extraction -> entity_mentions
  2. resolve   L6 -> OntologyBinding | ClarificationNeeded
  3. plan      L7 -> validated traversal path (from the domain prefetch spec)
  4. prefetch  L7 -> object reads + function evaluations
  5. dispatch  L10 -> agent call with Ontology Context
  6. validate  L11 -> numeric + entity + action-schema
  7. respond   answer + citations + action card
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .actions import ActionLayer
from .agent import Agent
from .db import connect
from .domains import load_domains
from .events import EventLifter, Signal
from .functions import FunctionExecutor
from .grounding import GroundingValidator
from .objects import ObjectLayer
from .planner import Planner, SemanticGap
from .registry import Registry
from .resolver import ClarificationNeeded, Resolver


@dataclass
class Stage:
    n: int
    name: str
    lines: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)


class Orchestrator:
    def __init__(self, domain: str, conn=None, use_llm: Optional[bool] = None):
        self.conn = conn or connect()
        self.domains = load_domains()
        if domain not in self.domains:
            raise KeyError(f"Unknown domain '{domain}'. Known: {list(self.domains)}")
        self.domain = self.domains[domain]
        self.registry = Registry(self.conn)
        self.objects = ObjectLayer(self.conn, self.registry)
        self.executor = FunctionExecutor(self.registry, self.objects)
        self.resolver = Resolver(self.conn, self.registry, self.objects, self.domain)
        self.planner = Planner(self.registry, self.objects, self.executor)
        self.agent = Agent(use_llm=use_llm)
        self.grounding = GroundingValidator(self.registry)
        self.actions = ActionLayer(self.conn, self.registry, self.objects, self.executor)
        self.events = EventLifter(self.conn, self.registry, self.objects, self.executor)
        self.resolver.build_index()

    # ---- stage 1: parse ----------------------------------------------
    def _parse(self, question: str) -> list[str]:
        low = question.lower()
        phrases = set()
        for plist in self.domain.alias_object_sets.values():
            phrases.update(p.lower() for p in plist)
        for plist in self.domain.alias_windows.values():
            phrases.update(p.lower() for p in plist)
        found = [p for p in phrases if p in low]
        found += re.findall(r"\b[a-z]+\s+\d+\b", low)   # shade 22 / deal 99 / campaign 9
        found = [p for p in found if not any(p != q and p in q for q in found)]
        found = list(dict.fromkeys(found))
        found.sort(key=lambda p: low.find(p))
        return found

    def _event_type(self) -> Optional[str]:
        r = self.conn.execute(
            "SELECT event_type FROM ontology_event_types WHERE object_type=?",
            (self.domain.primary_type,)).fetchone()
        return r["event_type"] if r else None

    # ---- full pipeline ------------------------------------------------
    def ask(self, question: str) -> dict:
        stages: list[Stage] = []
        mentions = self._parse(question)
        stages.append(Stage(1, "parse", [f"entity_mentions: {mentions}"], {"mentions": mentions}))

        resolutions, clar, rlines = [], None, []
        for m in mentions:
            res = self.resolver.resolve(m)
            if isinstance(res, ClarificationNeeded):
                clar = res
                rlines.append(f"'{m}' -> CLARIFY (conf {res.confidence})")
                break
            resolutions.append(res)
            rlines.append(f"'{m}' -> {res.target_id}  conf {res.confidence}  ({res.method})")
        stages.append(Stage(2, "resolve", rlines,
                            {"resolutions": [r.__dict__ for r in resolutions]}))

        if clar is not None:
            return {"question": question, "domain": self.domain.name,
                    "stages": [s.__dict__ for s in stages],
                    "clarification": {"surface": clar.surface, "confidence": clar.confidence,
                                      "candidates": clar.candidates}, "status": "CLARIFY"}

        window = next((self.registry.window(r.target_id) for r in resolutions
                       if r.kind == "window"), None)

        try:
            plan = self.planner.build_plan(resolutions, self.domain.prefetch)
        except SemanticGap as e:
            stages.append(Stage(3, "plan", [f"REJECTED: {e}"], {"error": str(e)}))
            return {"question": question, "domain": self.domain.name,
                    "stages": [s.__dict__ for s in stages], "status": "SEMANTIC_GAP",
                    "error": str(e)}
        stages.append(Stage(3, "plan", [f"traversal validated: {t}" for t in plan.traversals]
                            or ["no traversal needed (members carry the metric)"],
                            {"traversals": [str(t) for t in plan.traversals]}))
        stages.append(Stage(4, "prefetch",
                            [f"{len(plan.prefetch)} objects; {len(plan.object_sets)} object sets; "
                             f"{plan.read_count} reads"],
                            {"prefetch": plan.prefetch, "object_sets": plan.object_sets}))

        response = self.agent.run(plan, resolutions, window, question,
                                  self.domain, self.registry)
        stages.append(Stage(5, "agent",
                            [f"{response.source} · {response.model} "
                             f"(ontology v{self.registry.version()}, {response.ctx_tokens} ctx tokens)"],
                            {"source": response.source, "model": response.model,
                             "ctx_tokens": response.ctx_tokens,
                             "context_block": response.context_block}))

        result = self.grounding.validate(response, plan, window, self.domain)
        if not result.passed and self.agent.use_llm:
            response = self.agent.run(plan, resolutions, window, question,
                                      self.domain, self.registry)   # retry once
            result = self.grounding.validate(response, plan, window, self.domain)
        stages.append(Stage(6, "validate",
                            [f"numeric {'OK' if result.numeric_ok else 'FAIL'}  "
                             f"entity {'OK' if result.entity_ok else 'FAIL'}  "
                             f"action-schema {'OK' if result.action_ok else 'FAIL'}  "
                             f"confidence {result.confidence}"] + result.notes,
                            {"status": result.status, "confidence": result.confidence,
                             "notes": result.notes}))

        action_card = None
        if response.action:
            prop = self.actions.propose(response.action["action_type"],
                                        response.action["object_id"], response.action["params"])
            action_card = _card(prop, self.objects)
        stages.append(Stage(7, "respond", ["answer assembled with object-ID citations"], {}))

        return {
            "question": question, "domain": self.domain.name,
            "stages": [s.__dict__ for s in stages], "answer": response.answer,
            "citations": response.entities, "action_card": action_card,
            "confidence": result.confidence, "status": result.status,
            "agent": {"source": response.source, "model": response.model,
                      "ctx_tokens": response.ctx_tokens},
            "context_block": response.context_block,
        }

    # ---- signal path (L8 -> L9) --------------------------------------
    def signal(self, key: str, signal_type: Optional[str] = None) -> dict:
        event_type = self._event_type()
        event = self.events.lift(Signal(signal_type or self.domain.signal_type, key), event_type)
        obj = self.objects.get_object(event.variant_ref)
        urgency = 1.0
        for w in self.registry.windows():
            if self.domain.metric.window == w.get("window"):
                urgency = float(w["starts_in_days"])
        prop = self.actions.propose(self.domain.action.action_type, event.variant_ref,
                                    {self.domain.action.param: urgency})
        fallback = None
        if prop.status == "BLOCKED":
            fallback = _card(self.actions.propose("flag_for_review", event.variant_ref,
                                                  {"reason": f"{self.domain.metric.event_noun} risk"}),
                             self.objects)
        return {
            "domain": self.domain.name,
            "signal": {"type": signal_type or self.domain.signal_type, "key": key},
            "lifted": {"event_type": event.event_type, "variant": event.variant_ref,
                       "title": obj.title, "position": event.position_ref,
                       "severity": event.severity},
            "severity_trace": event.trace,
            "proposal": _card(prop, self.objects), "fallback": fallback,
        }

    def objects_view(self) -> dict:
        """Generic table of the domain's objects, read live through the binding
        layer, with the object-set members flagged and ranked first."""
        spec = self.domain.prefetch
        members = set(self.executor.object_set_ids(self.domain.object_set))
        rank_by = self.registry.function(self.domain.object_set).params.get("rank_by")
        rows = []
        for v in self.objects.all_of(self.domain.primary_type):
            row = {"object_id": v.object_id, "key": v.pk, "title": v.title,
                   "top": v.pk in members}
            for p in spec.member_props:
                row[p] = _num(v.get(p))
            if spec.traverse:
                hits = self.objects.traverse(v.object_id, spec.traverse)
                if hits:
                    for p in spec.target_props:
                        row[p] = _num(hits[0].get(p))
            rows.append(row)
        rows.sort(key=lambda r: r.get(rank_by) or 0, reverse=True)
        cols = [c for c in spec.member_props if c not in ("display_title", "name")] \
            + list(spec.target_props)
        window = self.registry.window(self.domain.metric.window) if self.domain.metric.window else None
        return {"domain": self.domain.name, "label": self.domain.label, "columns": cols,
                "rows": rows, "window": window, "object_set": self.domain.object_set,
                "unit": self.domain.metric.unit, "flagship": self.domain.flagship,
                "samples": self.domain.samples}

    def approve(self, action_id: str) -> dict:
        return _card(self.actions.approve(action_id), self.objects)

    def explain(self, object_id: str) -> dict:
        obj = self.objects.get_object(object_id)
        ot = self.registry.object_type(obj.object_type)
        props = {}
        for name in ot.properties:
            try:
                props[name] = obj.get(name)
            except Exception as e:  # noqa: BLE001
                props[name] = f"<error: {e}>"
        links = {ln: [t.object_id for t in self.objects.traverse(object_id, ln)]
                 for ln in ot.links}
        return {"object_id": object_id, "object_type": obj.object_type, "title": obj.title,
                "properties": props, "links": links,
                "definition": {"pack": ot.pack, "primary_key": ot.primary_key,
                               "implements": ot.implements, "extends": ot.extends}}


def _num(v):
    return round(v, 3) if isinstance(v, float) else v


def _card(prop, objects) -> dict:
    try:
        title = objects.get_object(prop.object_id).title
    except Exception:  # noqa: BLE001
        title = prop.object_id
    return {"action_id": prop.action_id, "action_type": prop.action_type,
            "object_id": prop.object_id, "target_title": title, "tier": prop.tier,
            "status": prop.status, "params": prop.params, "guards_passed": prop.guards_passed,
            "reason": prop.reason, "fallback": prop.fallback, "rollback": prop.rollback,
            "connector_write": prop.connector_write}
