"""L7 · Dynamic GraphQL Schema.

Exposes the semantic layer's graph (objects and links) as a GraphQL API.
Because the framework is domain-agnostic and loads ontology packs dynamically at 
runtime, the GraphQL schema is built as a universal Graph traversal engine.

You can query any object, read its properties as a JSON scalar, and traverse its 
links to other objects.
"""
import typing
import strawberry
from strawberry.scalars import JSON
from fastapi import Request

from .orchestrator import Orchestrator
from .cache import cached_query


@strawberry.type
class SemanticNode:
    object_id: str
    object_type: str

    @strawberry.field
    def properties(self, info: strawberry.Info) -> JSON:
        """Returns all scalar properties of this object as a JSON dictionary."""
        return self._raw_data  # type: ignore

    @strawberry.field
    def traverse(self, link: str, info: strawberry.Info) -> typing.List["SemanticNode"]:
        """Traverse a semantic link to find connected objects."""
        orch: Orchestrator = info.context["orchestrator"]
        cache_key = f"{orch.domain}:traverse:{self.object_id}:{link}"
        results = cached_query(cache_key, orch.objects.traverse, self.object_id, link)
        nodes = []
        for r in results:
            node = SemanticNode(object_id=r.object_id, object_type=r.object_type)
            node._raw_data = {k: v for k, v in r.items() if not k.startswith("_")} # type: ignore
            nodes.append(node)
        return nodes


@strawberry.type
class Query:
    @strawberry.field
    def object(self, object_id: str, info: strawberry.Info) -> typing.Optional[SemanticNode]:
        """Fetch a specific object by its ID."""
        orch: Orchestrator = info.context["orchestrator"]
        roles = info.context.get("roles", ["guest"])
        
        cache_key = f"{orch.domain}:get_object:{object_id}"
        obj = cached_query(cache_key, orch.objects.get_object, object_id)
        if not obj:
            return None
            
        # RBAC Check
        ot_def = orch.registry.object_type(obj.object_type)
        allowed_roles = ot_def.definition.get("roles_allowed", [])
        if allowed_roles and not any(r in allowed_roles for r in roles):
            return None
            
        node = SemanticNode(object_id=obj.object_id, object_type=obj.object_type)
        node._raw_data = {k: v for k, v in obj.items() if not k.startswith("_")} # type: ignore
        return node

    @strawberry.field
    def all_objects(self, object_type: str, info: strawberry.Info, limit: int = 50) -> typing.List[SemanticNode]:
        """Fetch all objects of a specific type (e.g. 'Variant', 'Product')."""
        orch: Orchestrator = info.context["orchestrator"]
        roles = info.context.get("roles", ["guest"])
        
        # RBAC Check
        ot_def = orch.registry.object_type(object_type)
        allowed_roles = ot_def.definition.get("roles_allowed", [])
        if allowed_roles and not any(r in allowed_roles for r in roles):
            return []
            
        cache_key = f"{orch.domain}:all_of:{object_type}"
        results = cached_query(cache_key, orch.objects.all_of, object_type)
        nodes = []
        for r in results[:limit]:
            node = SemanticNode(object_id=r.object_id, object_type=r.object_type)
            node._raw_data = {k: v for k, v in r.items() if not k.startswith("_")} # type: ignore
            nodes.append(node)
        return nodes

    @strawberry.field
    def schema_types(self, info: strawberry.Info) -> JSON:
        """Introspect the dynamic ontology types currently loaded in this domain."""
        orch: Orchestrator = info.context["orchestrator"]
        types = {}
        # Avoid circular import by fetching through db
        rows = orch.objects.conn.execute("SELECT object_type, definition FROM ontology_object_types").fetchall()
        import json
        for r in rows:
            types[r["object_type"]] = json.loads(r["definition"])
        return types


schema = strawberry.Schema(query=Query)

async def get_context(request: Request):
    # The orchestrator is attached to the request state by the FastAPI middleware/router
    return {
        "orchestrator": request.state.orchestrator
    }
