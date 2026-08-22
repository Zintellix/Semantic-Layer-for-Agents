"""L8 · Event Lifting & Decision Rules.

A raw signal is lifted into a typed event bound to object instances, and the
decision rules attached to the EVENT TYPE — not to any agent — determine severity.

The same signal shape produces CRITICAL for a hero shade (220) and HIGH for a
non-hero shade (505), with ZERO cosmetics-specific code outside the pack. This is
the cleanest single demonstration of the architecture's value.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .objects import make_object_id


@dataclass
class Signal:
    type: str
    key: str          # primary key of the target object (cosmetics also accepts a SKU)


@dataclass
class Event:
    event_type: str
    variant_ref: str
    position_ref: Optional[str]
    severity: str
    trace: list[str] = field(default_factory=list)


class EventLifter:
    def __init__(self, conn, registry, objects, executor):
        self.conn = conn
        self.registry = registry
        self.objects = objects
        self.executor = executor

    def _resolve_pk(self, object_type: str, ref: str) -> str:
        """A signal names an object by its primary key. Cosmetics also accepts a
        SKU (SKU-220) for convenience — mapped back to the variant id."""
        try:
            self.objects.get_object(make_object_id(object_type, ref))
            return ref
        except Exception:  # noqa: BLE001
            row = self.conn.execute(
                "SELECT variant_id FROM variants WHERE sku=?", (ref,)).fetchone()
            if row:
                return row["variant_id"]
            raise KeyError(f"No {object_type} for ref {ref}")

    def lift(self, signal: Signal, event_type: str = "StockoutRiskDetected", object_type: Optional[str] = "CosmeticsVariant") -> Event:
        etype = self.registry.event_type(event_type, object_type)  # from the pack
        pk = self._resolve_pk(etype.object_type, signal.key)
        obj_oid = make_object_id(etype.object_type, pk)
        obj = self.objects.get_object(obj_oid)


        # traverse the first declared link for context, if any
        ot = self.registry.object_type(etype.object_type)
        position_ref = None
        for lname in ot.links:
            hits = self.objects.traverse(obj_oid, lname)
            if hits:
                position_ref = hits[0].object_id
                break

        severity, trace = self._evaluate_severity(etype, obj)
        return Event(event_type, obj_oid, position_ref, severity, trace)

    def _evaluate_severity(self, etype, obj):
        """Interpret the pack's severity_rules — 'fn.<set> contains $x' → membership.
        No vertical logic lives here; the object set is named by the pack."""
        trace = []
        for rule in etype.severity_rules:
            if rule.when is None:  # default rule
                trace.append(f"default -> {rule.severity}")
                return rule.severity, trace
            m = re.search(r"(fn\.\w+)\s+contains", rule.when)
            if m:
                fn_id = m.group(1)
                member = obj.pk in self.executor.object_set_ids(fn_id)
                trace.append(f"{fn_id} contains {obj.pk}? {'YES' if member else 'NO'}")
                if member:
                    trace.append(f"-> {rule.severity}")
                    return rule.severity, trace
        return "HIGH", trace + ["-> HIGH (fallthrough)"]
