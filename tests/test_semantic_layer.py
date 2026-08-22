"""The nine tests from §8. Each defends a specific architectural claim."""
import pytest

from zx.agent import reason_domain
from zx.compiler import CompileError, Compiler
from zx.db import connect
from zx.objects import make_object_id
from zx.planner import Planner, SemanticGap
from zx.resolver import ClarificationNeeded, Resolver


# 1. compiler_loads_core — ensure the base generic engine compiles empty
def test_compiler_loads_core(tmp_path):
    import shutil
    from zx.db import PACKS_DIR
    from zx.compiler import Compiler
    from zx.db import connect
    
    # Compile the core pack
    c = Compiler(packs_dir=PACKS_DIR).load()
    c.validate(connect())
    assert "ReplenishableUnit" in c.interfaces
    assert "SellableItem" in c.interfaces
    
# 2. graphql_schema_builds — ensure dynamic graphql schema compiles
def test_graphql_schema_builds():
    from zx.graphql import schema
    from strawberry.schema.schema import Schema
    assert isinstance(schema, Schema)
    # Ensure our base types are in the schema
    assert "SemanticNode" in schema.schema_converter.type_map
    


