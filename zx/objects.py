"""L4 · Object Data Binding.

Makes principle O4 real: objects are views, never copies. Property reads resolve
through the binding declared in the definition — never through a hardcoded SQL
string in application code. Reading `.days_of_stock` silently dispatches to the
function executor; reading `.shade` silently dispatches to SQL. The caller cannot
tell the difference.

object_id format:  {workspace}:{object_type}:{primary_key}
"""
from __future__ import annotations

from typing import Any, Optional

from . import WORKSPACE_ID
from .primitives import ObjectType
from .registry import Registry


def make_object_id(object_type: str, pk: str, workspace: str = WORKSPACE_ID) -> str:
    return f"{workspace}:{object_type}:{pk}"


def parse_object_id(object_id: str) -> tuple[str, str, str]:
    workspace, object_type, pk = object_id.split(":", 2)
    return workspace, object_type, pk


class ObjectInstance:
    def __init__(self, layer: "ObjectLayer", object_type: str, pk: str, row: dict):
        self._layer = layer
        self.object_type = object_type
        self.pk = pk
        self.object_id = make_object_id(object_type, pk)
        self._row = row  # raw source columns

    @property
    def title(self) -> str:
        ot = self._layer.registry.object_type(self.object_type)
        if ot.title_property:
            return str(self.get(ot.title_property))
        return self.pk

    def get(self, prop_name: str) -> Any:
        return self._layer.read_property(self.object_id, prop_name)

    def items(self):
        """Iterate over all property values for this object (dict-like interface)."""
        ot = self._layer.registry.object_type(self.object_type)
        result = {}
        for pname in ot.properties:
            try:
                result[pname] = self.get(pname)
            except Exception:  # noqa: BLE001
                result[pname] = None
        return result.items()

    def __repr__(self):
        return f"<{self.object_type} {self.pk}>"


class ObjectLayer:
    def __init__(self, conn, registry: Optional[Registry] = None):
        self.conn = conn
        self.registry = registry or Registry(conn)
        self.executor = None  # set by FunctionExecutor.__init__ (mutual wiring)

    def _table(self, ot: ObjectType) -> str:
        # datasource "sqlite.variants" -> "variants"
        return ot.datasource.split(".", 1)[1] if ot.datasource else ot.object_type.lower()

    def get_object(self, object_id: str) -> ObjectInstance:
        _, object_type, pk = parse_object_id(object_id)
        ot = self.registry.object_type(object_type)
        table = self._table(ot)
        row = self.conn.execute(
            f"SELECT * FROM {table} WHERE {ot.primary_key}=?", (pk,)
        ).fetchone()
        if not row:
            raise KeyError(f"No {object_type} with {ot.primary_key}={pk}")
        return ObjectInstance(self, object_type, pk, dict(row))

    def read_property(self, object_id: str, prop_name: str) -> Any:
        _, object_type, pk = parse_object_id(object_id)
        ot = self.registry.object_type(object_type)
        prop = ot.properties.get(prop_name)
        if prop is None:
            raise KeyError(f"{object_type} has no property '{prop_name}'")
        if prop.is_derived:
            # dispatch to the function executor — caller can't tell it's computed
            if self.executor is None:
                raise RuntimeError("Function executor not wired to object layer")
            return self.executor.evaluate(prop.function, self.get_object(object_id))
        # source binding -> read the seeded column
        table, _, col = prop.source.partition(".")
        row = self.conn.execute(
            f"SELECT {col} FROM {table} WHERE {ot.primary_key}=?", (pk,)
        ).fetchone()
        return row[col] if row else None

    def traverse(self, object_id: str, link_name: str) -> list[ObjectInstance]:
        _, object_type, pk = parse_object_id(object_id)
        link = self.registry.link(object_type, link_name)
        if link is None:
            raise KeyError(f"{object_type} has no link '{link_name}'")
        target = self.registry.object_type(link.to_type)
        table = self._table(target)
        join_col = link.join[0]
        rows = self.conn.execute(
            f"SELECT * FROM {table} WHERE {join_col}=?", (pk,)
        ).fetchall()
        return [ObjectInstance(self, link.to_type, str(r[target.primary_key]), dict(r))
                for r in rows]

    # convenience: all instances of a type (used by object-set functions)
    def all_of(self, object_type: str) -> list[ObjectInstance]:
        ot = self.registry.object_type(object_type)
        table = self._table(ot)
        rows = self.conn.execute(f"SELECT * FROM {table}").fetchall()
        return [ObjectInstance(self, object_type, str(r[ot.primary_key]), dict(r)) for r in rows]
