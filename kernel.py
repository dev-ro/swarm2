from agno.agent import Agent
from agno.models.google import Gemini
from agno.models.ollama import Ollama

from agno.knowledge.lancedb import LanceDbKnowledgeBase
from agno.vectordb.lancedb import LanceDb
from agno.embedder.openai import OpenAIEmbedder
import os
import uuid
import json
import subprocess
from dotenv import load_dotenv

load_dotenv()

# The "Body": A helper agent/sub-agent for summarizing text and filtering logs
summary_agent = Agent(
    name="SummaryAgent",
    role="Text summarizer and log filter",
    model=Gemini(id="gemini-3-flash-preview"),
    # model=Ollama(id="deepseek-r1:8b"),
    description="You are a helper agent responsible for summarizing text and filtering logs.",
    instructions=[
        "Provide concise, accurate summaries of the provided text.",
        "Filter logs to extract the most critical and relevant information.",
        "Respond only with the requested summary or filtered logs, minimizing extra dialogue."
    ],
)

# The Knowledge Base using LanceDB and OpenAI embeddings
knowledge_base = LanceDbKnowledgeBase(
    vector_db=LanceDb(
        table_name="soae_knowledge",
        uri="tmp/lancedb",
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
)


# IACT Master Tools
def spawn_worker(role: str, goal: str) -> str:
    """Spawns an independent worker process to perform a task.
    
    Args:
        role: The role or persona of the worker.
        goal: The specific task or goal for the worker to achieve.
        
    Returns:
        A message containing the worker ID and workspace directory.
    """
    worker_id = str(uuid.uuid4())
    workspace_dir = os.path.abspath(f"./workspaces/{worker_id}")
    os.makedirs(workspace_dir, exist_ok=True)
    
    # Launch worker in background without waiting
    cmd = [
        "uv", "run", "python", "agents/worker.py",
        "--role", role,
        "--goal", goal,
        "--workspace_dir", workspace_dir
    ]
    
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return f"Worker Started. ID: {worker_id}. Check status later with check_worker_status."

def check_worker_status(worker_id: str) -> str:
    """Checks the status of an independent worker process.
    
    Args:
        worker_id: The ID of the worker to check.
        
    Returns:
        The result of the worker's task, or a message indicating it's still running.
    """
    result_file = f"./workspaces/{worker_id}/result.json"
    if os.path.exists(result_file):
        try:
            with open(result_file, "r") as f:
                data = json.load(f)
            return f"Worker {worker_id} completed. Result:\n{json.dumps(data, indent=2)}"
        except Exception as e:
            return f"Error reading result for worker {worker_id}: {e}"
    else:
        return f"Worker {worker_id} is still running or failed. No result found yet."


class MasterAgent(Agent):
    """
    The "Brain": High-level planning and reasoning agent of the SOAE.
    """
    def __init__(self, **kwargs):
        from agno.db.sqlite import SqliteDb
        super().__init__(
            name="MasterAgent",
            role="Self-Organizing Autonomous Entity (SOAE) Kernel",
            model=Gemini(id="gemini-3.1-pro-preview"),
            description="You are the Master Agent (The Brain) of a Self-Organizing Autonomous Entity.",
            db=SqliteDb(session_table="master_agent_sessions", db_file="storage.db"),
            add_history_to_messages=True,
            team=[summary_agent],
            knowledge=knowledge_base,
            search_knowledge=True,
            read_chat_history=True,
            tools=[spawn_worker, check_worker_status],
            instructions=[
                "You are the high-level planner and orchestrator.",
                "Delegate any and all text summarization or log filtering tasks to your SummaryAgent to save costs and optimize processing.",
                "Remember user context across sessions to maintain continuity.",
                "Use your search_knowledge_base tool to find relevant information before answering questions.",
                "Use spawn_worker to delegate complex tasks asynchronously to independent Ollama workers.",
                "Use check_worker_status periodically to retrieve results of spawned workers."
            ],
            **kwargs
        )

# Example usage (can be removed or moved to main.py later):
# if __name__ == "__main__":
#     knowledge_base.load(recreate=False) # Load the knowledge base
#     master_kernel = MasterAgent()
#     master_kernel.print_response("Hello, what is your purpose?", stream=True)
