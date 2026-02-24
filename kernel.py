from agno.agent import Agent
from agno.models.google import Gemini
from agno.models.ollama import Ollama
from agno.storage.agent.sqlite import SqliteAgentStorage

# The "Body": A helper agent/sub-agent for summarizing text and filtering logs
summary_agent = Agent(
    name="SummaryAgent",
    role="Text summarizer and log filter",
    model=Ollama(id="deepseek-r1:8b"),
    description="You are a helper agent responsible for summarizing text and filtering logs.",
    instructions=[
        "Provide concise, accurate summaries of the provided text.",
        "Filter logs to extract the most critical and relevant information.",
        "Respond only with the requested summary or filtered logs, minimizing extra dialogue."
    ],
)

class MasterAgent(Agent):
    """
    The "Brain": High-level planning and reasoning agent of the SOAE.
    """
    def __init__(self, **kwargs):
        super().__init__(
            name="MasterAgent",
            role="Self-Organizing Autonomous Entity (SOAE) Kernel",
            model=Gemini(id="gemini-3.1-pro-preview"),
            description="You are the Master Agent (The Brain) of a Self-Organizing Autonomous Entity.",
            storage=SqliteAgentStorage(table_name="master_agent_sessions", db_file="storage.db"),
            add_history_to_messages=True,
            team=[summary_agent],
            instructions=[
                "You are the high-level planner and orchestrator.",
                "Delegate any and all text summarization or log filtering tasks to your SummaryAgent to save costs and optimize processing.",
                "Remember user context across sessions to maintain continuity."
            ],
            **kwargs
        )

# Example usage (can be removed or moved to main.py later):
# if __name__ == "__main__":
#     master_kernel = MasterAgent()
#     master_kernel.print_response("Hello, what is your purpose?", stream=True)
