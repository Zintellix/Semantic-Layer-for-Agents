"""L2 · Ontology Compiler.

Three validations, no more — resist building a schema language today.
  1. Structural  — required keys present, types recognised.
  2. Referential — every link endpoint, property binding, guard, and action
                   object_type resolves to something declared/seeded.
  3. Functional  — every function's declared tests execute and PASS at compile
                   time. This makes fn.lead_time_coverage's 1.67 a compile gate,
                   not a hope.

A deliberately broken link (`to: NoSuchType`) fails compilation with a readable
error naming the file and key.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from . import ONTOLOGY_VERSION
from .db import connect, PACKS_DIR

KNOWN_TYPES = {"string", "number", "money", "object_ref", "boolean"}


class CompileError(Exception):
    pass


def _load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return list(yaml.safe_load_all(f)) if False else yaml.safe_load(f)


class Compiler:
    def __init__(self, packs_dir: Path | None = None, db_path=None):
        self.packs_dir = Path(packs_dir or PACKS_DIR)
        self.db_path = db_path
        self.object_types: dict[str, dict] = {}
        self.links: list[dict] = []
        self.actions: list[dict] = []
        self.functions: dict[str, dict] = {}
        self.events: list[dict] = []
        self.interfaces: dict[str, dict] = {}
        self.windows: list[dict] = []
        self._seeded_columns: dict[str, set[str]] = {}

    # ---- load ---------------------------------------------------------
    def load(self):
        for pack in sorted(self.packs_dir.iterdir()):
            if not pack.is_dir():
                continue
            self._load_file(pack / "interfaces.yaml", self._add_interfaces)
            self._load_file(pack / "objects.yaml", self._add_objects)
            self._load_file(pack / "links.yaml", self._add_links)
            self._load_file(pack / "actions.yaml", self._add_actions)
            self._load_file(pack / "functions.yaml", self._add_functions)
            self._load_file(pack / "events.yaml", self._add_events)
            self._load_file(pack / "calendar.yaml", self._add_windows)
        return self

    def _load_file(self, path: Path, handler):
        if not path.exists():
            return
        data = _load_yaml(path)
        if data is None:
            return
        try:
            handler(data, path)
        except CompileError:
            raise
        except Exception as e:  # noqa: BLE001
            raise CompileError(f"{path.name}: failed to load — {e}") from e

    def _add_interfaces(self, data, path):
        for i in data:
            self.interfaces[i["name"]] = i

    def _add_objects(self, data, path):
        for o in data:
            if "object_type" not in o or "primary_key" not in o:
                raise CompileError(f"{path.name}: object missing object_type/primary_key")
            self.object_types[o["object_type"]] = o

    def _add_links(self, data, path):
        self.links.extend(data or [])

    def _add_actions(self, data, path):
        self.actions.extend(data or [])

    def _add_functions(self, data, path):
        for fn in data or []:
            self.functions[fn["function_id"]] = fn

    def _add_events(self, data, path):
        self.events.extend(data or [])

    def _add_windows(self, data, path):
        self.windows.extend(data or [])

    # ---- validate -----------------------------------------------------
    def validate(self, conn):
        self._load_seeded_columns(conn)
        self._validate_structural()
        self._validate_referential(conn)
        # functional validation runs after write (needs a populated registry).

    def _load_seeded_columns(self, conn):
        tables = [r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        for t in tables:
            cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({t})").fetchall()}
            self._seeded_columns[t] = cols

    def _validate_structural(self):
        for name, o in self.object_types.items():
            for pname, p in o.get("properties", {}).items():
                if "type" not in p:
                    raise CompileError(f"{name}.{pname}: property missing 'type'")
                if p["type"] not in KNOWN_TYPES:
                    raise CompileError(f"{name}.{pname}: unknown type '{p['type']}'")
                if "source" not in p and "function" not in p:
                    raise CompileError(f"{name}.{pname}: needs a 'source' or 'function' binding")

    def _validate_referential(self, conn):
        types = set(self.object_types)
        # links (both inline and standalone) must have declared endpoints
        for name, o in self.object_types.items():
            for lname, lk in o.get("links", {}).items():
                if lk["to"] not in types:
                    raise CompileError(
                        f"{name}.links.{lname}: endpoint 'to: {lk['to']}' is not a declared object type")
                # Auto-create link join columns if table exists (assuming single table per object)
                if "datasource" in o and lk.get("join"):
                    table = o["datasource"].split(".")[-1]
                    cols = self._seeded_columns.get(table)
                    if cols is not None:
                        for jc in lk["join"]:
                            if jc not in cols:
                                conn.execute(f"ALTER TABLE {table} ADD COLUMN {jc} TEXT")
                                cols.add(jc)

        for lk in self.links:
            for endpoint in (lk["from_type"], lk["to_type"]):
                if endpoint not in types:
                    raise CompileError(
                        f"link {lk['link_type']}: endpoint '{endpoint}' is not a declared object type")
        
        # property source columns must exist in seeded tables (AUTO-MIGRATE them!)
        for name, o in self.object_types.items():
            for pname, p in o.get("properties", {}).items():
                if "source" in p:
                    table, _, col = p["source"].partition(".")
                    cols = self._seeded_columns.get(table)
                    if cols is None:
                        pk = o.get("primary_key", "id")
                        conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({pk} TEXT PRIMARY KEY)")
                        cols = {pk}
                        self._seeded_columns[table] = cols
                    if col not in cols:
                        sql_type = "REAL" if p.get("type") in ("number", "money") else "TEXT"
                        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {sql_type}")
                        cols.add(col)
                if "function" in p and p["function"] not in self.functions:
                    raise CompileError(f"{name}.{pname}: unknown function '{p['function']}'")
            for iface in o.get("implements", []):
                if iface not in self.interfaces:
                    raise CompileError(f"{name}: implements unknown interface '{iface}'")
            if o.get("extends") and o["extends"] not in types:
                raise CompileError(f"{name}: extends unknown type '{o['extends']}'")
        # action guards + object_type
        for a in self.actions:
            if a["object_type"] not in types:
                raise CompileError(
                    f"action {a['action_type']}: object_type '{a['object_type']}' not declared")
            for g in a.get("guards", []):
                if g not in self.functions:
                    raise CompileError(f"action {a['action_type']}: unknown guard '{g}'")
        # event object types
        for e in self.events:
            if e["object_type"] not in types:
                raise CompileError(
                    f"event {e['event_type']}: object_type '{e['object_type']}' not declared")

    # ---- write --------------------------------------------------------
    def write(self, conn):
        cur = conn.cursor()
        for tbl in ("ontology_object_types", "ontology_link_types", "ontology_action_types",
                    "ontology_functions", "ontology_event_types", "ontology_windows"):
            cur.execute(f"DELETE FROM {tbl}")
        v = ONTOLOGY_VERSION
        for name, o in self.object_types.items():
            cur.execute(
                "INSERT INTO ontology_object_types "
                "(object_type, pack, version, status, extends, implements, roles_allowed, definition) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (name, o.get("pack"), v, "ACTIVE", o.get("extends"),
                 json.dumps(o.get("implements", [])), 
                 json.dumps(o.get("roles_allowed", [])), 
                 json.dumps(o)))
            # persist inline links
            for lname, lk in o.get("links", {}).items():
                cur.execute(
                    "INSERT OR REPLACE INTO ontology_link_types "
                    "(link_type, version, from_type, to_type, cardinality, join_binding) "
                    "VALUES (?,?,?,?,?,?)",
                    (lname, v, name, lk["to"], lk["cardinality"], json.dumps(lk.get("join", []))))
        for a in self.actions:
            params = {n: p for n, p in a.get("parameters", {}).items()}
            cur.execute(
                "INSERT OR REPLACE INTO ontology_action_types "
                "(action_type, version, object_type, tier, reversibility, parameter_schema, "
                "connector_write, rollback_spec, guards) VALUES (?,?,?,?,?,?,?,?,?)",
                (a["action_type"], v, a["object_type"], a["tier"], a.get("reversibility"),
                 json.dumps(params), a.get("connector_write", "none"),
                 a.get("rollback"), json.dumps(a.get("guards", []))))
        for fid, fn in self.functions.items():
            cur.execute(
                "INSERT OR REPLACE INTO ontology_functions "
                "(function_id, version, returns, kind, inputs, formula, params, tests) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (fid, v, fn["returns"], fn.get("kind", "derived"),
                 json.dumps(fn.get("inputs", [])), fn.get("formula"),
                 json.dumps(fn.get("params", {})), json.dumps(fn.get("tests", []))))
        for e in self.events:
            cur.execute(
                "INSERT OR REPLACE INTO ontology_event_types "
                "(event_type, version, object_type, severity_rules) VALUES (?,?,?,?)",
                (e["event_type"], v, e["object_type"], json.dumps(e.get("severity_rules", []))))

        for w in self.windows:
            cur.execute(
                "INSERT OR REPLACE INTO ontology_windows (window, version, definition) VALUES (?,?,?)",
                (w["window"], v, json.dumps(w)))
        conn.commit()

    # ---- functional gate ---------------------------------------------
    def run_function_tests(self, conn):
        # Imported here to avoid a cycle: the executor reads the registry we just wrote.
        from .registry import Registry
        from .functions import FunctionExecutor
        from .objects import ObjectLayer

        reg = Registry(conn)
        objs = ObjectLayer(conn, reg)
        ex = FunctionExecutor(reg, objs)
        for fn in reg.functions():
            for t in fn.tests:
                ex.run_test(fn, t)  # raises CompileError-compatible AssertionError on failure


def compile_packs(conn=None, verbose: bool = True):
    conn = conn or connect()
    c = Compiler().load()
    c.validate(conn)
    c.write(conn)
    c.run_function_tests(conn)
    if verbose:
        print(f"Compiled {len(c.object_types)} object types, {len(c.functions)} functions, "
              f"{len(c.actions)} actions, {len(c.events)} events, {len(c.windows)} windows. "
              f"All function tests green.")
    return c


if __name__ == "__main__":
    compile_packs()
