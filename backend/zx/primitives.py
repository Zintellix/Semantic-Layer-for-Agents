"""L1 · Primitives.

The six ontology primitives plus interfaces, authored as dataclasses. Even the
ones that stay thin in this POC (ActionType, EventType) are fully present so the
primitive set is visibly complete and composes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class Property:
    name: str
    type: str                       # string | number | money | ...
    source: Optional[str] = None    # "table.column" binding, OR
    function: Optional[str] = None   # "fn.xxx" derived value

    @property
    def is_derived(self) -> bool:
        return self.function is not None


@dataclass(frozen=True)
class LinkType:
    link_type: str
    from_type: str
    to_type: str
    cardinality: str                # "1:N", "1:1", ...
    join: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Interface:
    name: str
    properties: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ObjectType:
    object_type: str
    pack: str
    primary_key: str
    properties: dict[str, Property] = field(default_factory=dict)
    links: dict[str, LinkType] = field(default_factory=dict)
    extends: Optional[str] = None
    implements: list[str] = field(default_factory=list)
    title_property: Optional[str] = None
    datasource: Optional[str] = None
    verticals: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FunctionDef:
    function_id: str
    returns: str                    # number | object_set | classification
    inputs: list[str] = field(default_factory=list)
    formula: Optional[str] = None    # restricted-eval expression (derived props)
    kind: str = "derived"           # derived | object_set | decision
    params: dict[str, Any] = field(default_factory=dict)
    tests: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class SeverityRule:
    when: Optional[str]             # None => default rule
    severity: str


@dataclass(frozen=True)
class EventType:
    event_type: str
    object_type: str
    severity_rules: list[SeverityRule] = field(default_factory=list)


@dataclass(frozen=True)
class ActionParam:
    name: str
    type: str
    min: Optional[float] = None
    max: Optional[float] = None


@dataclass(frozen=True)
class ActionType:
    action_type: str
    object_type: str
    tier: int                       # 0 auto-log · 1 recommendation · 2 gated write
    reversibility: str
    parameters: dict[str, ActionParam] = field(default_factory=dict)
    guards: list[str] = field(default_factory=list)     # function ids
    connector_write: str = "none"
    rollback: Optional[str] = None


# --- Stubs that the arch pulls in later; declared so the set is complete. ---
class NotImplementedPrimitive:
    def __init__(self, *_a, **_k):
        raise NotImplementedError(
            "This primitive facet is declared for completeness but out of POC scope."
        )
