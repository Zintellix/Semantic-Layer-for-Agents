"""L7 · Semantic Query Planner.

Two deterministic jobs. This is the layer people skip, and the one that proves the
link graph is load-bearing rather than decorative.

  · Path validation  — find the traversal a task needs (CosmeticsVariant ->
                       stocked_at -> InventoryPosition). No path => reject the plan
                       with a logged semantic gap, never an incoherent task.
  · Prefetch         — from the resolved binding, emit the EXACT object reads and
                       function evaluations the agent will need. The agent never
                       queries; it receives.

Deleting the stocked_at link from the pack makes validate_path raise SemanticGap.
That single behaviour is the proof the graph matters.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


class SemanticGap(Exception):
    pass


@dataclass
class LinkPath:
    from_type: str
    link: str
    to_type: str

    def __str__(self):
        return f"{self.from_type} -> {self.link} -> {self.to_type}"


@dataclass
class Plan:
    object_refs: list[str] = field(default_factory=list)          # resolved object ids
    object_sets: list[dict] = field(default_factory=list)         # {function_id, members}
    traversals: list[LinkPath] = field(default_factory=list)
    windows: list[dict] = field(default_factory=list)
    prefetch: dict[str, dict] = field(default_factory=dict)       # {object_id: {prop: value}}
    read_count: int = 0





class Planner:
    def __init__(self, registry, objects, executor):
        self.registry = registry
        self.objects = objects
        self.executor = executor

    # ---- path validation ---------------------------------------------
    def validate_path(self, from_type: str, to_type: str) -> LinkPath:
        for link in self.registry.links_from(from_type):
            if link.to_type == to_type:
                return LinkPath(from_type, link.link_type, to_type)
        raise SemanticGap(f"no traversal path {from_type} -> {to_type}")

    # ---- plan + prefetch ---------------------------------------------
    def build_plan(self, resolutions: list, spec) -> Plan:
        plan = Plan()
        member_variants = []

        for res in resolutions:
            if res.kind == "object_set":
                members = self.executor.object_set(res.target_id)
                member_variants.extend(members)
                plan.object_sets.append({
                    "function_id": res.target_id,
                    "members": [m.object_id for m in members],
                })
            elif res.kind == "object":
                obj = self.objects.get_object(
                    res.target_id if res.target_id.count(":") == 2
                    else f"ws1:{res.target_type}:{res.target_id}")
                member_variants.append(obj)
            elif res.kind == "window":
                plan.windows.append(self.registry.window(res.target_id))

        # dedupe variants by object id
        seen = {}
        for v in member_variants:
            seen[v.object_id] = v
        variants = list(seen.values())
        plan.object_refs = list(seen.keys())

        if variants:
            link = None
            if spec.traverse:
                # Path validation is load-bearing: raises SemanticGap if the pack has
                # no <member> -> <target> link.
                path = self.validate_path(variants[0].object_type, spec.target_type)
                plan.traversals.append(path)
                link = path.link

            for v in variants:
                bag = {p: _round(v.get(p)) for p in spec.member_props}
                if link:
                    hits = self.objects.traverse(v.object_id, link)
                    if hits:
                        pos = hits[0]
                        for p in spec.target_props:
                            bag[p] = _round(pos.get(p))
                        bag["_position_id"] = pos.object_id
                plan.prefetch[v.object_id] = bag
                plan.read_count += len(bag)

        return plan


def _round(v):
    return round(v, 3) if isinstance(v, float) else v
