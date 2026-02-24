import os
from agno.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb
from agno.knowledge.embedder.openai import OpenAIEmbedder
from dotenv import load_dotenv

load_dotenv()
knowledge_base = Knowledge(
    vector_db=LanceDb(
        table_name="soae_knowledge",
        uri="tmp/lancedb",
        embedder=OpenAIEmbedder(id=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")),
    ),
)
try:
    knowledge_base.insert(text_content="test problem and solution", metadata={"type": "test"})
    print("inserted")
except Exception as e:
    print(f"error: {e}")
