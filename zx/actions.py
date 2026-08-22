"""L9 · Action Layer.

Actions are ENUMERATED from the ontology, never invented by the agent. The flow:
  enumerate -> instantiate (schema-validated) -> guard -> gate (by tier) -> execute+log.

  · An agent proposing prioritise_hero_shade_replenishment for shade 505 is BLOCKED
    by the guard fn.is_hero_shade.
  · An agent inventing action_type "email_supplier" is REJECTED — not in the registry.
"""
from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .objects import parse_object_id


@dataclass
class ActionProposal:
    action_id: str
    action_type: str
    object_id: str
    tier: int
    reversibility: str
    params: dict
    status: str                         # PROPOSED | BLOCKED | REJECTED | APPROVED | EXECUTED
    guards_passed: list[str] = field(default_factory=list)
    reason: Optional[str] = None
    connector_write: str = "none"
    rollback: Optional[str] = None
    fallback: Optional[str] = None


class ActionLayer:
    def __init__(self, conn, registry, objects, executor):
        self.conn = conn
        self.registry = registry
        self.objects = objects
        self.executor = executor

    def allowed_actions(self, object_type: str, max_tier: int = 2):
        return [a for a in self.registry.actions_for(object_type) if a.tier <= max_tier]

    def _validate_params(self, atype, params) -> Optional[str]:
        for name, spec in atype.parameters.items():
            if name not in params:
                return f"missing parameter '{name}'"
            val = params[name]
            if spec.type == "number":
                if not isinstance(val, (int, float)):
                    return f"parameter '{name}' must be a number"
                if spec.min is not None and val < spec.min:
                    return f"parameter '{name}'={val} below min {spec.min}"
                if spec.max is not None and val > spec.max:
                    return f"parameter '{name}'={val} above max {spec.max}"
        return None

    def propose(self, action_type: str, object_id: str, params: dict) -> ActionProposal:
        action_id = "act_" + secrets.token_hex(6)
        _, object_type, _ = parse_object_id(object_id)

        # enumerate — must exist in the registry for this object type
        atype = self.registry.action_type(action_type, object_type)
        if atype is None or atype.object_type != object_type:
            prop = ActionProposal(action_id, action_type, object_id, -1, "N/A", params,
                                  "REJECTED", reason=f"'{action_type}' is not an allowed "
                                  f"action for {object_type}")
            self._log(prop)
            return prop

        # instantiate — schema validation
        err = self._validate_params(atype, params)
        if err:
            prop = ActionProposal(action_id, action_type, object_id, atype.tier,
                                  atype.reversibility, params, "REJECTED", reason=err)
            self._log(prop)
            return prop

        # guard — every declared guard function must pass
        target = self.objects.get_object(object_id)
        for guard in atype.guards:
            if not self.executor.decision(guard, target):
                prop = ActionProposal(
                    action_id, action_type, object_id, atype.tier, atype.reversibility,
                    params, "BLOCKED", reason=f"guard {guard} failed",
                    fallback="flag_for_review")
                self._log(prop)
                return prop

        # gate — tier 0 auto-logs; tier 1 renders a card; tier 2 needs approval
        status = "EXECUTED" if atype.tier == 0 else "PROPOSED"
        prop = ActionProposal(action_id, action_type, object_id, atype.tier,
                              atype.reversibility, params, status,
                              guards_passed=list(atype.guards),
                              connector_write=atype.connector_write, rollback=atype.rollback)
        self._log(prop)
        return prop

    def approve(self, action_id: str) -> ActionProposal:
        row = self.conn.execute(
            "SELECT * FROM decision_log WHERE action_id=?", (action_id,)).fetchone()
        if not row:
            raise KeyError(f"No action {action_id}")
        target = json.loads(row["target_objects"])[0]
        _, otype, _ = parse_object_id(target)
        atype = self.registry.action_type(row["action_type"], otype)
        prop = ActionProposal(
            action_id, row["action_type"], target, row["tier"],
            atype.reversibility if atype else "N/A", json.loads(row["params"]),
            "EXECUTED", connector_write=atype.connector_write if atype else "none",
            rollback=row["rollback"])
        # mock connector write — the real system would call Shopify here (deferred).
        prop.reason = f"mock connector write via '{prop.connector_write}'"
        self._update_status(action_id, "EXECUTED")
        return prop

    # ---- decision_log -------------------------------------------------
    def _log(self, prop: ActionProposal):
        self.conn.execute(
            "INSERT OR REPLACE INTO decision_log "
            "(action_id, action_type, target_objects, tier, status, params, rollback, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (prop.action_id, prop.action_type, json.dumps([prop.object_id]), prop.tier,
             prop.status, json.dumps(prop.params), prop.rollback,
             datetime.now(timezone.utc).isoformat()))
        self.conn.commit()

    def _update_status(self, action_id: str, status: str):
        self.conn.execute("UPDATE decision_log SET status=? WHERE action_id=?",
                          (status, action_id))
        self.conn.commit()

    def log_entries(self, limit: int = 20):
        rows = self.conn.execute(
            "SELECT * FROM decision_log ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
