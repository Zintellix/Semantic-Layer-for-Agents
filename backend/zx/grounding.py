"""L11 · Grounding Validator.

Three checks, mirroring the architecture's numeric check:
  · Numeric      — every figure in the response appears in the prefetch or is
                   derivable from it.
  · Entity       — every named entity carries an object ID present in the binding.
  · Action schema— the proposed action exists in the registry for that object type
                   and its parameters conform.

Failure behaviour: retry once, then downgrade — confidence 0.2, status PARTIAL. A
hand-forced answer naming "Shade 999" or citing an uncited number is caught here.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GroundingResult:
    numeric_ok: bool
    entity_ok: bool
    action_ok: bool
    status: str                       # OK | PARTIAL
    confidence: float
    notes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.numeric_ok and self.entity_ok and self.action_ok


class GroundingValidator:
    def __init__(self, registry):
        self.registry = registry

    def _allowed_numbers(self, plan, window, domain) -> set[float]:
        allowed: set[float] = set()

        def add(v):
            if isinstance(v, (int, float)):
                allowed.add(round(float(v), 1))

        if window:
            for k in ("starts_in_days", "duration_days", "expected_uplift_pct"):
                add(window.get(k))
            uplift = 1 + window["expected_uplift_pct"] / 100.0
            starts = window["starts_in_days"]
        else:
            uplift, starts = 1.0, 0

        # which keys are the level/rate/value depends on the domain (default: cosmetics)
        if domain is not None and not domain.is_cosmetics:
            level_k, rate_k = domain.metric.level, domain.metric.rate
            value_k = domain.metric.value
            if domain.metric.threshold is not None:
                add(domain.metric.threshold)
        else:
            level_k, rate_k, value_k = "on_hand", "avg_daily_units_7d", None

        agg_total = 0.0
        for bag in plan.prefetch.values():
            for v in bag.values():
                add(v)
            lvl, rate = bag.get(level_k), bag.get(rate_k)
            if isinstance(lvl, (int, float)) and isinstance(rate, (int, float)) and rate:
                burn = starts * rate
                remaining = lvl - burn
                peak = rate * uplift
                add(burn); add(remaining); add(peak); add(lvl / rate)
                if peak:
                    add(remaining / peak)
                    if window:
                        add(remaining / peak - window["duration_days"])
            if value_k and isinstance(bag.get(value_k), (int, float)):
                agg_total += bag[value_k]
        if value_k:
            add(agg_total)
            if domain.metric.threshold is not None:
                add(domain.metric.threshold - agg_total)   # gap (at_least)
                add(agg_total - domain.metric.threshold)   # over (at_most)
        return allowed

    def validate(self, response, plan, window, domain=None) -> GroundingResult:
        notes = []

        # numeric
        allowed = self._allowed_numbers(plan, window, domain)
        bad_numbers = [n for n in response.numbers
                       if round(float(n), 1) not in allowed
                       and not _close(n, allowed)]
        numeric_ok = not bad_numbers
        if bad_numbers:
            notes.append(f"ungrounded numbers: {bad_numbers}")

        # entity
        known = set(plan.prefetch.keys())
        for os_ in plan.object_sets:
            known.update(os_["members"])
        bad_entities = [e for e in response.entities if e not in known]
        entity_ok = not bad_entities
        if bad_entities:
            notes.append(f"ungrounded entities: {bad_entities}")

        # action schema
        action_ok = True
        if response.action:
            action_ok = self._validate_action(response.action, notes)

        if numeric_ok and entity_ok and action_ok:
            return GroundingResult(True, True, True, "OK", response.confidence, notes)
        # downgrade (after the single retry the orchestrator already attempted)
        return GroundingResult(numeric_ok, entity_ok, action_ok, "PARTIAL", 0.2, notes)

    def _validate_action(self, action, notes) -> bool:
        atype_name = action.get("action_type")
        oid = action.get("object_id", "")
        object_type = oid.split(":")[1] if oid.count(":") == 2 else ""
        allowed = {a.action_type: a for a in self.registry.actions_for(object_type)}
        atype = allowed.get(atype_name)
        if not atype:
            notes.append(f"action '{atype_name}' not in registry for {object_type}")
            return False
        for name, spec in atype.parameters.items():
            val = action.get("params", {}).get(name)
            if spec.type == "number" and val is not None:
                if spec.min is not None and val < spec.min:
                    notes.append(f"{name}={val} below min {spec.min}")
                    return False
                if spec.max is not None and val > spec.max:
                    notes.append(f"{name}={val} above max {spec.max}")
                    return False
        return True


def _close(n, allowed, tol=0.15) -> bool:
    return any(abs(float(n) - a) <= tol for a in allowed)
