import argparse
import os
import json
from agno.agent import Agent
from agno.models.google import Gemini
from agno.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb
from agno.knowledge.embedder.openai import OpenAIEmbedder
from dotenv import load_dotenv

load_dotenv()

def run_worker(role: str, goal: str, workspace_dir: str):
    """
    Runs an independent worker agent using Gemini
    and shared LanceDB knowledge.
    """
    print(f"Starting worker: Role='{role}', Goal='{goal}'")
    
    # Connect to shared LanceDB knowledge base
    knowledge_base = Knowledge(
        vector_db=LanceDb(
            table_name="soae_knowledge",
            uri="tmp/lancedb",
            embedder=OpenAIEmbedder(id=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")),
        ),
    )
    
    # Create the Gemini agent
    agent = Agent(
        name="LocalWorker",
        role=role,
        model=Gemini(id=os.getenv("LIGHT_MODEL", "gemini-2.5-flash")),
        knowledge=knowledge_base,
        search_knowledge=True, # Allow it to search the shared KB
        instructions=[
            f"Your role is: {role}",
            "Complete the goal independently and provide a comprehensive final answer.",
            "Make use of your knowledge base when necessary."
        ]
    )
    
    try:
        response = agent.run(goal)
        result = {
            "status": "success",
            "role": role,
            "goal": goal,
            "response": response.content
        }
    except Exception as e:
        result = {
            "status": "error",
            "role": role,
            "goal": goal,
            "error": str(e)
        }

    # Write result to IPC file (workspaces/{unique_id}/result.json)
    result_file = os.path.join(workspace_dir, "result.json")
    with open(result_file, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"Worker completed. Result written to {result_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IACT Independent Worker")
    parser.add_argument("--role", type=str, required=True, help="The role of the worker")
    parser.add_argument("--goal", type=str, required=True, help="The goal for the worker to achieve")
    parser.add_argument("--workspace_dir", type=str, required=True, help="Directory to store IPC files")
    
    args = parser.parse_args()
    run_worker(args.role, args.goal, args.workspace_dir)
