from typing import Optional
import os
import json
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini
from agno.knowledge.lancedb import LanceDbKnowledgeBase
from agno.document import Document
from agno.embedder.google import GeminiEmbedder

load_dotenv()

# Setup UI Learner Knowledge Base
ui_learner_kb = LanceDbKnowledgeBase(
    uri="./workspaces/db/lancedb",
    table_name="ui_lessons",
    embedder=GeminiEmbedder(id=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")),
    search_kwargs={"limit": 3}
)
# Ensure the KB loads or creates its internal structures
ui_learner_kb.load()

# Initialize the Visual Feedback Agent
qa_agent = Agent(
    name="QualityAssuranceAgent",
    role="Senior UI/UX Designer and QA Tester",
    model=Gemini(id=os.getenv("MAIN_MODEL", "gemini-3.1-pro-preview")),
    description="You are a Senior UI/UX Designer responsible for critiquing application layouts and aesthetics.",
    instructions=[
        "You are a Senior UI/UX Designer. Critique the screenshot for alignment, color theory, and usability."
    ]
)

def learn_ui_lesson(problem: str, solution: str, context: str = "Flutter"):
    """
    Saves a 'Lesson' to the LanceDB knowledge base for future UI generation/fixes.
    Structure: {'problem': ..., 'solution': ..., 'context': ...}
    """
    lesson_data = {
        "problem": problem,
        "solution": solution,
        "context": context
    }
    
    doc = Document(
        content=f"Problem: {problem}\nSolution: {solution}",
        meta_data={"context": context, "type": "ui_lesson"}
    )
    
    # Add to KB
    ui_learner_kb.load_documents([doc])
    print(f"[Learner] Saved UI lesson: {problem} -> {solution}")

def analyze_ui_screenshot(image_path: str, context: str = "Flutter") -> str:
    """
    Passes an image path to the QualityAssuranceAgent and returns its critique.
    It queries the Learner Knowledge Base beforehand to supply known pitfalls.
    """
    try:
        # 1. Query past lessons
        relevant_lessons = ui_learner_kb.search(f"{context} UI layout alignment color issues")
        
        lesson_context = ""
        if relevant_lessons:
            lesson_context = "\nHere are relevant previous lessons to keep in mind:\n"
            for lesson in relevant_lessons:
                lesson_context += f"- {lesson.content}\n"
                
        # 2. Build prompt
        prompt = (
            f"Please critique the following UI screenshot located at {image_path}. "
            f"Provide actionable bugs or improvements based on layout, color, and alignment."
            f"{lesson_context}"
        )
        
        response = qa_agent.run(prompt, images=[image_path])
        return response.content
    except Exception as e:
        return f"Failed to analyze screenshot: {str(e)}"
