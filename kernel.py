import os
import uuid
import json
import subprocess
import functools
import pathlib
import re
from typing import Dict, Any

from agno.agent import Agent
from agno.models.google import Gemini
from agno.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.knowledge.document.base import Document
from ddgs import DDGS
from security import requires_permission, get_credential
from dotenv import load_dotenv

load_dotenv()

# Universal Toolset & Self-Healing

def self_healing_tool(func):
    """
    Decorator that catches tool failures and asks a Gemini model to correct the arguments.
    It retries up to 3 times before giving up.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        attempts = 3
        current_kwargs = kwargs.copy()
        last_error = ""

        for attempt in range(attempts):
            try:
                return func(*args, **current_kwargs)
            except Exception as e:
                last_error = str(e)
                print(f"[Self-Healing] Tool '{func.__name__}' failed: {e}. Attempt {attempt + 1}/{attempts}. Healing...")
                
                # Healer agent
                healer = Agent(
                    model=Gemini(id=os.getenv("LIGHT_MODEL", "gemini-2.5-flash")),
                    instructions=[
                        f"The tool '{func.__name__}' failed with the following error: {last_error}",
                        f"The original arguments provided were: {current_kwargs}",
                        "Based on the error, fix the arguments to resolve the issue.",
                        "Return ONLY a valid JSON dictionary containing the corrected keyword arguments. Do NOT add markdown blocks or tags."
                    ]
                )
                
                try:
                    prompt = "Provide the corrected arguments as a raw JSON object string."
                    response = healer.run(prompt).content
                    
                    # Clean the response to ensure it's pure JSON
                    clean_resp = response.replace('```json', '').replace('```', '').strip()
                    clean_resp = re.sub(r'<think>.*?</think>', '', clean_resp, flags=re.DOTALL).strip()
                    
                    current_kwargs = json.loads(clean_resp)
                    print(f"[Self-Healing] Extracted corrected kwargs: {current_kwargs}")
                except Exception as parse_e:
                    print(f"[Self-Healing] Failed to parse healer response: {parse_e}")
                    # If we can't heal it properly, we just let the loop continue and try again or fail.
        
        return f"Tool '{func.__name__}' failed permanently after {attempts} attempts. Last error: {last_error}"
    return wrapper

def get_safe_path(file_path: str) -> pathlib.Path:
    """Returns the resolved file path."""
    return pathlib.Path(file_path).resolve()

@self_healing_tool
def read_file(file_path: str) -> str:
    """Reads the contents of a file within the workspaces directory."""
    safe_path = get_safe_path(file_path)
    if not safe_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(safe_path, "r", encoding="utf-8") as f:
        return f.read()

@self_healing_tool
def write_file(file_path: str, content: str) -> str:
    """Writes content to a file safely within the workspaces directory."""
    safe_path = get_safe_path(file_path)
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    with open(safe_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"File successfully written to {file_path}"

@self_healing_tool
def list_dir(dir_path: str) -> str:
    """Lists the contents of a directory safely within the workspaces directory."""
    safe_path = get_safe_path(dir_path)
    if not safe_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {dir_path}")
    return json.dumps(os.listdir(safe_path))

@self_healing_tool
def research_topic(query: str) -> str:
    """Searches the web for a given query, summarizes top results via Gemini, and saves to a file in workspaces/knowledge."""
    print(f"[Deep Research] Searching for: {query}")
    results = DDGS().text(query, max_results=3)
    if not results:
        return f"No results found for {query}"
    
    combined_text = "\n\n".join([f"Title: {r.get('title')}\nSnippet: {r.get('body')}\nLink: {r.get('href')}" for r in results])
    
    summarizer = Agent(
        model=Gemini(id=os.getenv("LIGHT_MODEL", "gemini-2.5-flash")),
        description="You are a research summarizer.",
        instructions=["Summarize the provided text comprehensively, extracting key facts. Do NOT include <think> tags."]
    )
    summary_resp = summarizer.run(combined_text).content
    summary_clean = re.sub(r'<think>.*?</think>', '', summary_resp, flags=re.DOTALL).strip()
    
    # Save the summary to workspaces/knowledge
    safe_dir = get_safe_path("workspaces/knowledge")
    safe_dir.mkdir(parents=True, exist_ok=True)
    
    # Make a safe filename
    safe_filename = "".join(x for x in query if x.isalnum() or x in " _-").strip() + ".txt"
    with open(safe_dir / safe_filename, "w", encoding="utf-8") as f:
        f.write(summary_clean)
        
    return f"Research on '{query}' complete. Summary saved to workspaces/knowledge/{safe_filename}."



# The "Body": A helper agent/sub-agent for summarizing text and filtering logs
summary_agent = Agent(
    name="SummaryAgent",
    role="Text summarizer and log filter",
    model=Gemini(id=os.getenv("LIGHT_MODEL", "gemini-2.5-flash")),
    description="You are a helper agent responsible for summarizing text and filtering logs.",
    instructions=[
        "Provide concise, accurate summaries of the provided text.",
        "Filter logs to extract the most critical and relevant information.",
        "Respond only with the requested summary or filtered logs, minimizing extra dialogue."
    ],
)

# The Knowledge Base using LanceDB and OpenAI embeddings
knowledge_base = Knowledge(
    vector_db=LanceDb(
        table_name="soae_knowledge",
        uri="tmp/lancedb",
        embedder=OpenAIEmbedder(id=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")),
    ),
)


# IACT Master Tools
from docker_tools import SandboxedExecutor
from screenshot_tool import capture_app_screenshot
from qa_agent import analyze_ui_screenshot

@requires_permission
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

sandbox = SandboxedExecutor()

@self_healing_tool
def execute_python_code(code: str, require_network: bool = False) -> str:
    """Executes python code strictly within an isolated Docker container context.
    Pass require_network=True if you need internet access (e.g. pip install),
    but this will ask the user for permission first.
    """
    return sandbox.execute_python(code, require_network)

@self_healing_tool
def execute_shell_command(cmd: str, require_network: bool = False) -> str:
    """Executes a shell command strictly within an isolated Docker container context.
    Pass require_network=True if you need internet access."""
    return sandbox.execute_shell(cmd, require_network)

@self_healing_tool
def save_ui_lesson(problem: str, solution: str, context: str = "Flutter") -> str:
    """
    Saves a learned UI/UX lesson to the Knowledge Base (LanceDB).
    Future agents will query this database before writing logic.
    """
    lesson_data = {
        "problem": problem,
        "solution": solution,
        "context": context
    }
    lesson_text = json.dumps(lesson_data)
    
    # Store as LanceDB knowledge
    knowledge_base.insert(text_content=lesson_text, metadata={"type": "ui_lesson", "context": context})
    
    return f"Lesson successfully saved to Knowledge Base: {lesson_text}"

@self_healing_tool
def query_ui_lessons(context: str = "Flutter") -> str:
    """
    Queries LanceDB for past UI/UX lessons. The agent MUST call this before writing new frontend code.
    """
    results = knowledge_base.search(f"{context} UI layout alignment color issues", num_documents=5)
    if not results:
        return f"No past UI lessons found for context: {context}."
    
    lessons = []
    for r in results:
        lessons.append(getattr(r, "content", getattr(r, "text", str(r))))
        
    return "Past UI lessons to keep in mind:\n" + "\n".join(lessons)

class MasterAgent(Agent):
    """
    The "Brain": High-level planning and reasoning agent of the SOAE.
    """
    def __init__(self, **kwargs):
        from agno.db.sqlite import SqliteDb
        super().__init__(
            name="MasterAgent",
            role="Self-Organizing Autonomous Entity (SOAE) Kernel",
            model=Gemini(id=os.getenv("MAIN_MODEL", "gemini-3.1-pro-preview")),
            description="You are the Master Agent (The Brain) of a Self-Organizing Autonomous Entity.",
            db=SqliteDb(session_table="master_agent_sessions", db_file="storage.db"),
            num_history_messages=10,
            knowledge=knowledge_base,
            search_knowledge=True,
            read_chat_history=True,
            tools=[
                spawn_worker, check_worker_status, list_dir, read_file, write_file, 
                research_topic, get_credential, execute_python_code, execute_shell_command,
                capture_app_screenshot, analyze_ui_screenshot, save_ui_lesson, query_ui_lessons
            ],
            instructions=[
                "You are the high-level planner and orchestrator.",
                "Delegate any and all text summarization or log filtering tasks to your SummaryAgent to save costs and optimize processing.",
                "Remember user context across sessions to maintain continuity.",
                "Before writing frontend or UI code, YOU MUST call the query_ui_lessons tool to query past UI lessons and avoid previous mistakes.",
                "Use spawn_worker to delegate complex tasks asynchronously to independent Gemini workers.",
                "Use check_worker_status periodically to retrieve results of spawned workers.",
                "Use the Universal Toolset (read_file, write_file, list_dir) to safely manipulate files in your sandboxed workspace directory.",
                "Use the research_topic tool to run Deep Research loops, summarizing findings from the web directly into your knowledge base.",
                "Use execute_python_code and execute_shell_command to safely run code or shell commands isolated in Docker.",
                "Use get_credential(service_name) prior to executing code requiring external auth to securely fetch user tokens securely without hardcoding them.",
                "The system enforces a Human-in-the-Loop policy. If you call write_file, spawn_worker, or request network access in the Sandbox, the user will be prompted to approve.",
                "Use capture_app_screenshot(url) to take a picture of a running web app.",
                "Use analyze_ui_screenshot(image_path) to pass images to your sibling QualityAssuranceAgent for UI critique.",
                "When you resolve a UI bug based on visual feedback, use save_ui_lesson to persist the {problem, solution, context} to LanceDB so you never make that mistake again."
            ],
            **kwargs
        )

# Example usage (can be removed or moved to main.py later):
# if __name__ == "__main__":
#     knowledge_base.load(recreate=False) # Load the knowledge base
#     master_kernel = MasterAgent()
#     master_kernel.print_response("Hello, what is your purpose?", stream=True)
