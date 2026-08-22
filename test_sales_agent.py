import requests
import json

def test_sales_agent():
    print("Semantic Sales Agent Initialized\n")
    print("This agent communicates with the Zintellix Semantic Layer via the REST API.")
    print("It uses the 'sales' domain pack we just compiled.\n")

    question = "Which accounts have a Deal over 200,000?"
    print(f"User: {question}")
    print("Agent: Querying Semantic Layer...\n")

    # In a real environment, you'd start the server with `uvicorn api:app`
    # and hit `http://localhost:8000/api/ask`. 
    # For this demo script without running the server, we can just use the CLI underlying logic.
    
    # We will use the orchestrator directly since we are in the same environment.
    from zx.orchestrator import Orchestrator
    orch = Orchestrator(domain="sales")
    
    # Disable LLM so we just see the raw graph traversal resolution
    orch.agent.use_llm = False
    
    response = orch.ask(question)
    
    print("--- Semantic Layer Graph Resolution ---")
    print(f"Matched Object Types: {response.get('object_types', [])}")
    print("Data Extracted from Graph:")
    
    # Print out the data retrieved from the database via the semantic layer
    data = response.get("data", [])
    if data:
        print(json.dumps(data, indent=2))
    else:
        print("No data retrieved.")
    
    print("\n[SUCCESS] Agent successfully plugged into Semantic Layer!")

if __name__ == "__main__":
    test_sales_agent()
