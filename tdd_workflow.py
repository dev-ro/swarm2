import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini
from kernel import execute_shell_command, read_file, write_file
from audit_tool import run_security_audit

load_dotenv()

# Initialize the TDD Coder Agent
tdd_coder_agent = Agent(
    name="CoderAgent",
    role="TDD Software Engineer",
    model=Gemini(id=os.getenv("MAIN_MODEL", "gemini-3.1-pro-preview")),
    description="You are an expert Software Engineer who strictly follows Test-Driven Development (TDD) and self-correction.",
    tools=[
        execute_shell_command, read_file, write_file, run_security_audit
    ],
    instructions=[
        "You are an expert Software Engineer enforcing Test-Driven Development (TDD) and Self-Correction.",
        "Rule 1 [TDD Cycle]: Before writing code (e.g., `main.dart` or `app.py`), you MUST write the corresponding test file (e.g., `test/widget_test.dart` or `test_app.py`).",
        "Rule 2: Execute the test using `execute_shell_command`. It MUST fail initially.",
        "Rule 3: Write the actual code to make the test pass.",
        "Rule 4: Run the test again.",
        "Rule 5 [Self-Correction]: If the test fails, YOU MUST read the error output, fix the code, and retry until it passes.",
        "Rule 6 [Security Audit]: Before finalizing and deploying/showing the user your code, you MUST run the `run_security_audit` tool on the directory.",
        "Rule 7 [Audit Enforcement]: If `run_security_audit` fails, you are FORBIDDEN from deploying or showing the user the result until you fix the caught issues."
    ]
)

def run_tdd_session(task_description: str) -> str:
    """
    Executes a TDD coding session with the CoderAgent.
    """
    prompt = f"Please implement the following task using strict TDD:\n{task_description}\nRemember to write the test first, run your audit before finishing, and show your final secure code."
    
    print(f"[TDD Workflow] Starting session for task: {task_description}")
    response = tdd_coder_agent.run(prompt)
    return response.content
