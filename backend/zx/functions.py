"""L5 · Function Executor.

Deterministic. No LLM inside a function. Three kinds:
  · derived property : fn.days_of_stock, fn.lead_time_coverage
  · object set        : fn.hero_shades (top-3 by revenue_28d)
  · decision function : fn.is_hero_shade, fn.stockout_severity (consumed by L8/L9)

SECURITY NOTE (arch §14): the POC evaluates formulas with a restricted eval over a
whitelisted namespace. The real system REQUIRES a sandboxed runner. This comment
exists so the shortcut never becomes the design by accident.
"""
from __future__ import annotations

import math
from typing import Any

from .objects import ObjectInstance
from .primitives import FunctionDef

# Whitelisted names available to formula evaluation. No builtins, no imports.
_SAFE_NS = {"__builtins__": {}, "min": min, "max": max, "abs": abs, "round": round,
            "math": math}


def safe_eval(formula: str, variables: dict[str, Any]) -> Any:
    ns = dict(_SAFE_NS)
    ns.update(variables)
    return eval(formula, {"__builtins__": {}}, ns)  # noqa: S307 — restricted; see module note


class FunctionExecutor:
    def __init__(self, registry, objects):
        self.registry = registry
        self.objects = objects
        objects.executor = self  # mutual wiring (L4 <-> L5)

    # ---- derived properties ------------------------------------------
    def evaluate(self, function_id: str, obj: ObjectInstance) -> Any:
        fn = self.registry.function(function_id)
        if fn.kind != "derived":
            raise ValueError(f"{function_id} is not a derived function")
        variables = self._gather_inputs(obj, fn.inputs)
        variables.update(fn.params)
        return safe_eval(fn.formula, variables)

    def _gather_inputs(self, obj: ObjectInstance, inputs: list[str]) -> dict[str, Any]:
        """Resolve each formula input from the object or a linked object.

        on_hand / avg_daily_units_7d live on the linked InventoryPosition, so we
        traverse the object's links to find them. Deterministic: one position per
        variant in the seed.
        """
        ot = self.registry.object_type(obj.object_type)
        out: dict[str, Any] = {}
        for name in inputs:
            if name in ot.properties:
                out[name] = obj.get(name)
                continue
            found = False
            for link_name in ot.links:
                for target in self.objects.traverse(obj.object_id, link_name):
                    tot = self.registry.object_type(target.object_type)
                    if name in tot.properties:
                        out[name] = target.get(name)
                        found = True
                        break
                if found:
                    break
            if not found:
                raise KeyError(f"Cannot resolve input '{name}' for {obj.object_type}")
        return out

    # ---- object sets --------------------------------------------------
    def object_set(self, function_id: str) -> list[ObjectInstance]:
        fn = self.registry.function(function_id)
        if fn.kind != "object_set":
            raise ValueError(f"{function_id} is not an object-set function")
        rank_by = fn.params.get("rank_by", "revenue_28d")
        top_n = int(fn.params.get("top_n", 3))
        object_type = fn.params.get("object_type", "CosmeticsVariant")
        candidates = self.objects.all_of(object_type)
        candidates.sort(key=lambda o: o.get(rank_by) or 0, reverse=True)
        return candidates[:top_n]

    def object_set_ids(self, function_id: str) -> list[str]:
        return [o.pk for o in self.object_set(function_id)]

    # ---- decision functions ------------------------------------------
    def is_hero_shade(self, obj: ObjectInstance) -> bool:
        return obj.pk in self.object_set_ids("fn.hero_shades")

    def stockout_severity(self, obj: ObjectInstance) -> str:
        # Delegates to hero membership — the rule itself lives in the pack (L8).
        return "CRITICAL" if self.is_hero_shade(obj) else "HIGH"

    def decision(self, function_id: str, obj: ObjectInstance) -> Any:
        """Data-driven: a decision fn with params.membership_of returns whether the
        object belongs to that object set. Works for any domain's guards."""
        fn = self.registry.function(function_id)
        membership = fn.params.get("membership_of")
        if membership:
            return obj.pk in self.object_set_ids(membership)
        # legacy named fallbacks (cosmetics)
        if function_id == "fn.is_hero_shade":
            return self.is_hero_shade(obj)
        if function_id == "fn.stockout_severity":
            return self.stockout_severity(obj)
        raise KeyError(f"Unknown decision function {function_id}")

    # ---- compile-time gate -------------------------------------------
    def run_test(self, fn: FunctionDef, test: dict) -> None:
        if fn.kind == "derived":
            variables = dict(test["inputs"])
            variables.update(fn.params)
            got = safe_eval(fn.formula, variables)
            tol = test.get("tol", 1e-9)
            if abs(got - test["expect"]) > tol:
                raise AssertionError(
                    f"{fn.function_id}: expected {test['expect']}±{tol}, got {got}")
        elif fn.kind == "object_set":
            got = self.object_set_ids(fn.function_id)
            want = test["expect_ids"]
            if got != want:
                raise AssertionError(f"{fn.function_id}: expected {want}, got {got}")
        # decision functions declare no compile tests
