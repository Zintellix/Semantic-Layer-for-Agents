"""L3 · Ontology Registry.

Compiled definitions live in the registry tables and are read back through this
single accessor. No module outside registry.py reads a YAML file at runtime — if
one did, we'd have built a config loader, not an ontology.

An in-process dict cache stands in for the real design's 60s-TTL cache; the
accessor signatures are identical so the TTL is an additive change later.
"""
from __future__ import annotations

import json
from typing import Optional

from . import ONTOLOGY_VERSION
from .db import connect
from .primitives import (
    ActionParam, ActionType, EventType, FunctionDef, Interface,
    LinkType, ObjectType, Property, SeverityRule,
)


class Registry:
    def __init__(self, conn=None):
        self.conn = conn or connect()
        self._cache: dict[str, object] = {}

    # ---- object types -------------------------------------------------
    def object_type(self, name: str) -> ObjectType:
        key = f"ot:{name}"
        if key in self._cache:
            return self._cache[key]  # type: ignore[return-value]
        row = self.conn.execute(
            "SELECT definition FROM ontology_object_types WHERE object_type=?", (name,)
        ).fetchone()
        if not row:
            raise KeyError(f"Unknown object type: {name}")
        ot = _object_type_from_json(json.loads(row["definition"]))
        self._cache[key] = ot
        return ot

    def object_types(self) -> list[ObjectType]:
        rows = self.conn.execute("SELECT object_type FROM ontology_object_types").fetchall()
        return [self.object_type(r["object_type"]) for r in rows]

    # ---- links --------------------------------------------------------
    def links_from(self, object_type: str) -> list[LinkType]:
        rows = self.conn.execute(
            "SELECT link_type, from_type, to_type, cardinality, join_binding "
            "FROM ontology_link_types WHERE from_type=?", (object_type,)
        ).fetchall()
        return [
            LinkType(r["link_type"], r["from_type"], r["to_type"], r["cardinality"],
                     json.loads(r["join_binding"]))
            for r in rows
        ]

    def link(self, from_type: str, link_name: str) -> Optional[LinkType]:
        for lk in self.links_from(from_type):
            if lk.link_type == link_name:
                return lk
        return None

    # ---- actions ------------------------------------------------------
    def actions_for(self, object_type: str) -> list[ActionType]:
        rows = self.conn.execute(
            "SELECT * FROM ontology_action_types WHERE object_type=?", (object_type,)
        ).fetchall()
        return [_action_from_row(r) for r in rows]

    def action_type(self, action_type: str, object_type: Optional[str] = None) -> Optional[ActionType]:
        if object_type:
            r = self.conn.execute(
                "SELECT * FROM ontology_action_types WHERE action_type=? AND object_type=?",
                (action_type, object_type)).fetchone()
        else:
            r = self.conn.execute(
                "SELECT * FROM ontology_action_types WHERE action_type=?", (action_type,)
            ).fetchone()
        return _action_from_row(r) if r else None

    # ---- functions ----------------------------------------------------
    def function(self, function_id: str) -> FunctionDef:
        r = self.conn.execute(
            "SELECT * FROM ontology_functions WHERE function_id=?", (function_id,)
        ).fetchone()
        if not r:
            raise KeyError(f"Unknown function: {function_id}")
        return FunctionDef(
            function_id=r["function_id"], returns=r["returns"], kind=r["kind"],
            inputs=json.loads(r["inputs"]), formula=r["formula"],
            params=json.loads(r["params"]), tests=json.loads(r["tests"]),
        )

    def functions(self) -> list[FunctionDef]:
        rows = self.conn.execute("SELECT function_id FROM ontology_functions").fetchall()
        return [self.function(r["function_id"]) for r in rows]

    # ---- events -------------------------------------------------------
    def event_type(self, event_type: str) -> EventType:
        r = self.conn.execute(
            "SELECT * FROM ontology_event_types WHERE event_type=?", (event_type,)
        ).fetchone()
        if not r:
            raise KeyError(f"Unknown event type: {event_type}")
        rules = [SeverityRule(x.get("when"), x["severity"]) for x in json.loads(r["severity_rules"])]
        return EventType(r["event_type"], r["object_type"], rules)

    # ---- windows ------------------------------------------------------
    def window(self, name: str) -> dict:
        r = self.conn.execute(
            "SELECT definition FROM ontology_windows WHERE window=?", (name,)
        ).fetchone()
        if not r:
            raise KeyError(f"Unknown window: {name}")
        return json.loads(r["definition"])

    def windows(self) -> list[dict]:
        rows = self.conn.execute("SELECT definition FROM ontology_windows").fetchall()
        return [json.loads(r["definition"]) for r in rows]

    def version(self) -> str:
        return ONTOLOGY_VERSION


# ---- (de)serialization helpers ---------------------------------------
def _object_type_from_json(d: dict) -> ObjectType:
    props = {
        n: Property(name=n, type=p["type"], source=p.get("source"), function=p.get("function"))
        for n, p in d.get("properties", {}).items()
    }
    links = {
        n: LinkType(n, d["object_type"], lk["to"], lk["cardinality"], lk.get("join", []))
        for n, lk in d.get("links", {}).items()
    }
    return ObjectType(
        object_type=d["object_type"], pack=d["pack"], primary_key=d["primary_key"],
        properties=props, links=links, extends=d.get("extends"),
        implements=d.get("implements", []), title_property=d.get("title_property"),
        datasource=d.get("datasource"), verticals=d.get("verticals", []),
    )


def _action_from_row(r) -> ActionType:
    params = {
        n: ActionParam(n, p["type"], p.get("min"), p.get("max"))
        for n, p in json.loads(r["parameter_schema"]).items()
    }
    return ActionType(
        action_type=r["action_type"], object_type=r["object_type"], tier=r["tier"],
        reversibility=r["reversibility"], parameters=params,
        guards=json.loads(r["guards"]), connector_write=r["connector_write"],
        rollback=r["rollback_spec"],
    )
