from docx import Document
from docx.shared import Pt
import os

def create_doc():
    doc = Document()
    doc.add_heading('Zintellix Semantic Layer: Architecture & Agent Integration Guide', 0)
    
    doc.add_heading('1. Executive Summary', level=1)
    doc.add_paragraph(
        "The Zintellix Semantic Layer is a domain-agnostic, generic framework designed to act as the "
        "brain for enterprise operations. Instead of hardcoding business rules, metrics, or relationships "
        "into the core engine, the framework relies on declarative 'Domain Packs' (YAML files) to define "
        "the ontology dynamically. This allows any external AI Agent to simply plug in on top of the "
        "framework, query the semantic layer via GraphQL or REST APIs, and reason about the business "
        "without needing to understand the underlying database schemas."
    )
    
    doc.add_heading('2. The Architecture', level=1)
    doc.add_paragraph("The framework is composed of four primary layers:")
    
    doc.add_heading('2.1 Ontology Packs (The Definitions)', level=2)
    doc.add_paragraph(
        "Domain specifics are defined in the `packs/` directory (e.g., `packs/sales`). A pack contains:\n"
        "- objects.yaml: Defines the entities (e.g., Deal, Account, Variant).\n"
        "- links.yaml: Defines how entities connect (e.g., Deal -> Account).\n"
        "- functions.yaml: Defines derived metrics and business rules (e.g., top_deals).\n"
        "- domain.yaml: Defines the domain's primary target metric and flagships."
    )
    
    doc.add_heading('2.2 The Compiler & Registry', level=2)
    doc.add_paragraph(
        "When `python build.py` is executed, the engine's Compiler reads the YAML packs, validates "
        "referential integrity, executes any defined tests, and compiles the ontology into the Semantic Registry "
        "(a relational database). The engine reads strictly from this registry at runtime."
    )
    
    doc.add_heading('2.3 Execution Engine (Planner & Resolver)', level=2)
    doc.add_paragraph(
        "The core logic resides in `zx/`. When a query is received, the Resolver uses vector similarity "
        "(via ChromaDB) to resolve ambiguous terms into exact Object IDs. The Planner then calculates the "
        "necessary graph traversal paths required to answer the query, fetching all required data."
    )
    
    doc.add_heading('2.4 API Surface (GraphQL & REST)', level=2)
    doc.add_paragraph(
        "The framework exposes two API layers via FastAPI:\n"
        "1. REST API: Standard POST endpoints like `/api/ask` to interact with the built-in orchestrator.\n"
        "2. GraphQL API: A dynamic GraphQL schema (via Strawberry) mounted at `/graphql/{domain}`. This allows "
        "external agents to query the semantic graph, traverse relationships (e.g., getting a Deal's associated Account), "
        "and read real-time properties without executing raw SQL."
    )
    
    doc.add_heading('3. Plugging and Playing Agents', level=1)
    doc.add_paragraph(
        "Because the Semantic Layer acts as an isolated translation layer between the raw database and the AI, "
        "plugging an agent on top is seamless. An external agent only needs to know the domain name and the API endpoint."
    )
    
    doc.add_heading('Integration via GraphQL', level=2)
    doc.add_paragraph(
        "Your custom LLM agents can treat the semantic layer as a standard tool. The agent can construct a "
        "GraphQL query to fetch exactly the data it needs to reason about the user's intent."
    )
    
    doc.add_heading('Integration via Built-In Orchestrator (REST API)', level=2)
    doc.add_paragraph(
        "Alternatively, if you want the engine to handle the reasoning, your front-end application can simply "
        "POST the user's natural language query to `/api/ask`. The built-in Orchestrator will resolve the entities, "
        "plan the data retrieval, execute the metrics, and pass the context to an LLM to generate the final response."
    )
    
    doc.add_heading('4. Example: Sales Domain', level=1)
    doc.add_paragraph(
        "To test a Sales Agent, we load a 'sales' domain pack. This pack defines 'Deals' and 'Accounts' with "
        "properties like 'deal_size' and 'stage'. Once loaded, you can point your Sales Agent at the "
        "`/graphql/sales` endpoint to traverse the sales pipeline, or use `zx ask --domain sales` to interact via CLI."
    )
    
    file_path = os.path.join(os.getcwd(), 'Semantic_Layer_Architecture.docx')
    doc.save(file_path)
    print(f"Document generated successfully at {file_path}")

if __name__ == '__main__':
    create_doc()
